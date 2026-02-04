#!/usr/bin/env python3
"""
大规模测试多跳约束

测试不同规模下多跳约束的性能和质量
"""

import json
import time
from pathlib import Path
from collections import Counter
from datetime import datetime

from browsecomp_v3.core.config import get_config
from browsecomp_v3.core.models import ActionType
from browsecomp_v3.templates.template_selector import TemplateSelector
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.query_executor import QueryExecutor
from browsecomp_v3.generator.question_generator import QuestionGenerator
from browsecomp_v3.generator.answer_extractor import AnswerExtractor
from browsecomp_v3.validator.question_validator import QuestionValidator
from browsecomp_v3.validator.diversity_checker import DiversityChecker
from browsecomp_v3.utils.logging import setup_logging


def test_scale(count, min_constraints, max_constraints, test_name):
    """
    测试指定规模的问题生成
    
    Args:
        count: 生成数量
        min_constraints: 最小约束数
        max_constraints: 最大约束数
        test_name: 测试名称
    """
    print(f"\n{'='*80}")
    print(f"测试: {test_name}")
    print(f"配置: count={count}, constraints={min_constraints}-{max_constraints}")
    print(f"{'='*80}\n")
    
    # 初始化组件
    config = get_config()
    template_selector = TemplateSelector()
    kg_loader = KnowledgeGraphLoader()
    constraint_generator = ConstraintGenerator(kg_loader)
    query_executor = QueryExecutor(kg_loader)
    question_generator = QuestionGenerator(kg_loader)
    answer_extractor = AnswerExtractor()
    question_validator = QuestionValidator()
    diversity_checker = DiversityChecker()
    
    # 加载知识图谱
    print("加载知识图谱...")
    kg_loader.load()
    print(f"✓ 知识图谱已加载: {kg_loader.node_count} 节点, {kg_loader.edge_count} 边\n")
    
    # 统计变量
    generated_questions = []
    total_attempts = 0
    max_attempts = count * config.max_generation_retries
    
    # 详细统计
    failure_reasons = Counter()
    constraint_counts = Counter()
    constraint_types_used = Counter()
    multi_hop_count = 0
    templates_used = Counter()
    hop_counts = Counter()
    
    start_time = time.time()
    
    print(f"开始生成 {count} 个问题...\n")
    
    while len(generated_questions) < count and total_attempts < max_attempts:
        total_attempts += 1
        
        # 1. 选择模板
        try:
            tid = template_selector.select(mode="random")
            templates_used[tid] += 1
        except Exception as e:
            failure_reasons["template_selection"] += 1
            continue
        
        # 2. 生成约束
        try:
            constraint_set = constraint_generator.generate(
                template_id=tid,
                min_constraints=min_constraints,
                max_constraints=max_constraints
            )
            
            num_constraints = len(constraint_set.constraints)
            constraint_counts[num_constraints] += 1
            
            # 统计约束类型和多跳约束
            has_multi_hop = False
            for constraint in constraint_set.constraints:
                constraint_types_used[constraint.constraint_type] += 1
                if constraint.action == ActionType.MULTI_HOP_TRAVERSE:
                    has_multi_hop = True
            
            if has_multi_hop:
                multi_hop_count += 1
        
        except Exception as e:
            failure_reasons["constraint_generation"] += 1
            continue
        
        # 3. 执行查询
        try:
            query_result = query_executor.execute(constraint_set)
            
            if len(query_result.candidates) == 0:
                failure_reasons["no_candidates"] += 1
                continue
            
            # 统计推理跳数
            hop_counts[query_result.reasoning_chain.total_hops] += 1
            
            # 随机选择一个候选
            import random
            candidate_id = random.choice(query_result.candidates)
        
        except Exception as e:
            failure_reasons["query_execution"] += 1
            continue
        
        # 4. 提取答案
        try:
            candidate_data = kg_loader.get_node(candidate_id)
            answer = answer_extractor.extract(candidate_id, candidate_data, kg_loader)
        
        except Exception as e:
            failure_reasons["answer_extraction"] += 1
            continue
        
        # 5. 生成问题
        try:
            question = question_generator.generate(
                constraint_set=constraint_set,
                reasoning_chain=query_result.reasoning_chain,
                answer_entity_id=candidate_id,
                answer_text=answer.text
            )
        
        except Exception as e:
            failure_reasons["question_generation"] += 1
            continue
        
        # 6. 验证
        if question_validator.validate(question, query_result.candidates):
            generated_questions.append(question)
            
            # 进度显示
            if len(generated_questions) % 10 == 0 or len(generated_questions) == count:
                print(f"✓ 已生成: {len(generated_questions)}/{count} ({len(generated_questions)/count*100:.1f}%)")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 多样性分析
    diversity_stats = diversity_checker.check_diversity(generated_questions)
    
    # 难度分布
    difficulty_dist = Counter(q.difficulty for q in generated_questions)
    
    # 统计结果
    results = {
        "test_name": test_name,
        "config": {
            "count": count,
            "min_constraints": min_constraints,
            "max_constraints": max_constraints,
        },
        "generation": {
            "successful": len(generated_questions),
            "total_attempts": total_attempts,
            "success_rate": len(generated_questions) / total_attempts if total_attempts > 0 else 0,
            "elapsed_time": elapsed,
            "questions_per_second": len(generated_questions) / elapsed if elapsed > 0 else 0,
        },
        "multi_hop": {
            "total_with_multi_hop": multi_hop_count,
            "percentage": multi_hop_count / total_attempts * 100 if total_attempts > 0 else 0,
        },
        "diversity": diversity_stats,
        "constraint_counts": dict(constraint_counts),
        "constraint_types_used": dict(constraint_types_used),
        "templates_used": dict(templates_used),
        "hop_counts": dict(hop_counts),
        "difficulty_distribution": dict(difficulty_dist),
        "failure_reasons": dict(failure_reasons),
    }
    
    print_results(results)
    
    return results, generated_questions


def print_results(results):
    """打印测试结果"""
    print(f"\n{'='*80}")
    print("测试结果")
    print(f"{'='*80}\n")
    
    config = results["config"]
    gen = results["generation"]
    mh = results["multi_hop"]
    div = results["diversity"]
    
    print(f"生成统计:")
    print(f"  - 目标数量: {config['count']}")
    print(f"  - 成功生成: {gen['successful']} 个")
    print(f"  - 总尝试次数: {gen['total_attempts']} 次")
    print(f"  - 成功率: {gen['success_rate']:.2%}")
    print(f"  - 耗时: {gen['elapsed_time']:.2f} 秒")
    print(f"  - 速度: {gen['questions_per_second']:.2f} 问题/秒")
    
    print(f"\n多跳约束统计:")
    print(f"  - 包含多跳约束的尝试: {mh['total_with_multi_hop']} 次")
    print(f"  - 多跳约束占比: {mh['percentage']:.1f}%")
    
    print(f"\n多样性统计:")
    print(f"  - 唯一问题: {div['unique']}")
    print(f"  - 多样性率: {div['diversity_rate']:.2%}")
    print(f"  - 模板分布: {div['template_distribution']}")
    
    print(f"\n约束数量分布:")
    total = sum(results["constraint_counts"].values())
    for count, freq in sorted(results["constraint_counts"].items()):
        print(f"  - {count} 个约束: {freq} 次 ({freq/total*100:.1f}%)")
    
    print(f"\n约束类型使用统计:")
    for ctype, freq in sorted(results["constraint_types_used"].items(), key=lambda x: x[1], reverse=True):
        marker = " [多跳]" if ctype in ["person_name", "author_order", "institution_affiliation"] else ""
        print(f"  - {ctype}: {freq} 次{marker}")
    
    print(f"\n推理跳数分布:")
    for hops, freq in sorted(results["hop_counts"].items()):
        print(f"  - {hops} 跳: {freq} 个问题 ({freq/gen['successful']*100:.1f}%)")
    
    print(f"\n难度分布:")
    for diff, count in sorted(results["difficulty_distribution"].items()):
        print(f"  - {diff}: {count} 个问题 ({count/gen['successful']*100:.1f}%)")
    
    print(f"\n失败原因统计:")
    for reason, freq in sorted(results["failure_reasons"].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {reason}: {freq} 次 ({freq/gen['total_attempts']*100:.1f}%)")


def main():
    """主函数"""
    # 设置日志
    config = get_config()
    config.verbose = False
    setup_logging(log_level="WARNING", log_file=None, log_dir=None, verbose=False)
    
    print("\n" + "#"*80)
    print("# 多跳约束大规模测试")
    print("#"*80)
    
    # 测试配置
    test_configs = [
        (100, 2, 3, "100问题 (2-3约束)"),
        (200, 2, 3, "200问题 (2-3约束)"),
        (500, 2, 4, "500问题 (2-4约束)"),
    ]
    
    all_results = []
    
    for count, min_c, max_c, test_name in test_configs:
        results, questions = test_scale(count, min_c, max_c, test_name)
        all_results.append(results)
        
        # 短暂休息
        time.sleep(2)
    
    # 保存完整结果
    output_dir = Path("output/multi_hop_scale_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"scale_test_results_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n{'='*80}")
    print(f"完整测试结果已保存到: {output_file}")
    print(f"{'='*80}\n")
    
    # 生成对比表格
    print("\n" + "="*80)
    print("对比表格")
    print("="*80 + "\n")
    
    print(f"{'测试':<20} {'成功数':<10} {'成功率':<10} {'耗时(秒)':<12} {'速度(问/秒)':<15} {'多跳占比':<12} {'多样性率':<10}")
    print("-" * 120)
    
    for r in all_results:
        config = r["config"]
        gen = r["generation"]
        mh = r["multi_hop"]
        div = r["diversity"]
        
        test_str = f"{config['count']}问题"
        
        print(f"{test_str:<20} {gen['successful']:<10} {gen['success_rate']:<10.2%} "
              f"{gen['elapsed_time']:<12.2f} {gen['questions_per_second']:<15.2f} "
              f"{mh['percentage']:<12.1f}% {div['diversity_rate']:<10.2%}")
    
    # 关键洞察
    print("\n" + "="*80)
    print("关键洞察")
    print("="*80 + "\n")
    
    for r in all_results:
        print(f"✓ {r['test_name']}:")
        print(f"  - 多跳约束占比: {r['multi_hop']['percentage']:.1f}%")
        print(f"  - 多样性率: {r['diversity']['diversity_rate']:.1f}%")
        print(f"  - 平均速度: {r['generation']['questions_per_second']:.1f} 问题/秒")
        
        # 分析推理跳数
        hop_dist = r["hop_counts"]
        total_questions = r["generation"]["successful"]
        multi_hop_questions = sum(count for hops, count in hop_dist.items() if hops > 1)
        print(f"  - 多跳问题 (>1跳): {multi_hop_questions}/{total_questions} ({multi_hop_questions/total_questions*100:.1f}%)")
        
        # 分析难度
        diff_dist = r["difficulty_distribution"]
        medium_hard = diff_dist.get("medium", 0) + diff_dist.get("hard", 0)
        print(f"  - 中高难度问题: {medium_hard}/{total_questions} ({medium_hard/total_questions*100:.1f}%)")
        print()


if __name__ == "__main__":
    main()
