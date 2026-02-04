#!/usr/bin/env python3
"""
测试多约束配置并分析结果
"""

import json
import time
from pathlib import Path
from collections import Counter
from datetime import datetime

from browsecomp_v3.core.config import get_config
from browsecomp_v3.templates.template_selector import TemplateSelector
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.query_executor import QueryExecutor
from browsecomp_v3.generator.question_generator import QuestionGenerator
from browsecomp_v3.generator.answer_extractor import AnswerExtractor
from browsecomp_v3.validator.question_validator import QuestionValidator
from browsecomp_v3.validator.diversity_checker import DiversityChecker
from browsecomp_v3.utils.logging import setup_logging


def test_constraint_config(min_constraints, max_constraints, count=100, verbose=False):
    """
    测试特定的约束配置
    
    Args:
        min_constraints: 最小约束数
        max_constraints: 最大约束数
        count: 生成问题数量
        verbose: 详细输出
    
    Returns:
        dict: 测试结果统计
    """
    print(f"\n{'='*80}")
    print(f"测试配置: min={min_constraints}, max={max_constraints}, count={count}")
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
    
    # 失败原因统计
    failure_reasons = Counter()
    constraint_counts = Counter()
    constraint_types_used = Counter()
    templates_used = Counter()
    
    start_time = time.time()
    
    while len(generated_questions) < count and total_attempts < max_attempts:
        total_attempts += 1
        
        # 1. 选择模板
        try:
            tid = template_selector.select(mode="random")
            templates_used[tid] += 1
        except Exception as e:
            failure_reasons["template_selection"] += 1
            if verbose:
                print(f"  模板选择失败: {e}")
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
            
            # 统计约束类型
            for constraint in constraint_set.constraints:
                constraint_types_used[constraint.constraint_type] += 1
            
            if verbose:
                print(f"  尝试 {total_attempts}: 模板={tid}, 约束数={num_constraints}")
                for c in constraint_set.constraints:
                    print(f"    - {c.constraint_type}: {c.filter_condition}")
        
        except Exception as e:
            failure_reasons["constraint_generation"] += 1
            if verbose:
                print(f"  约束生成失败: {e}")
            continue
        
        # 3. 执行查询
        try:
            query_result = query_executor.execute(constraint_set)
            
            if verbose:
                print(f"    → 查询结果: {len(query_result.candidates)} 候选")
            
            if len(query_result.candidates) == 0:
                failure_reasons["no_candidates"] += 1
                continue
            
            # 随机选择一个候选
            import random
            candidate_id = random.choice(query_result.candidates) if len(query_result.candidates) > 1 else query_result.candidates[0]
        
        except Exception as e:
            failure_reasons["query_execution"] += 1
            if verbose:
                print(f"    → 查询失败: {e}")
            continue
        
        # 4. 提取答案
        try:
            candidate_data = kg_loader.get_node(candidate_id)
            answer = answer_extractor.extract(candidate_id, candidate_data, kg_loader)
            
            if verbose:
                print(f"    → 答案: {answer.text[:50]}...")
        
        except Exception as e:
            failure_reasons["answer_extraction"] += 1
            if verbose:
                print(f"    → 答案提取失败: {e}")
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
            if verbose:
                print(f"    → 问题生成失败: {e}")
            continue
        
        # 6. 验证
        if question_validator.validate(question, query_result.candidates):
            generated_questions.append(question)
            if not verbose:
                print(f"✓ 生成问题 {len(generated_questions)}/{count}: {question.question_id} (约束数: {num_constraints})")
            else:
                print(f"    → ✓ 生成成功: {question.question_id}")
        else:
            failure_reasons["validation_failed"] += 1
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 多样性分析
    diversity_stats = diversity_checker.check_diversity(generated_questions)
    
    # 统计结果
    results = {
        "config": {
            "min_constraints": min_constraints,
            "max_constraints": max_constraints,
            "target_count": count,
        },
        "generation": {
            "successful": len(generated_questions),
            "total_attempts": total_attempts,
            "success_rate": len(generated_questions) / total_attempts if total_attempts > 0 else 0,
            "elapsed_time": elapsed,
            "questions_per_second": len(generated_questions) / elapsed if elapsed > 0 else 0,
        },
        "diversity": diversity_stats,
        "constraint_counts": dict(constraint_counts),
        "constraint_types_used": dict(constraint_types_used),
        "templates_used": dict(templates_used),
        "failure_reasons": dict(failure_reasons),
        "questions": [
            {
                "question_id": q.question_id,
                "template_id": q.template_id,
                "constraint_count": len(q.constraint_set.constraints),
                "difficulty": q.difficulty,
                "question_text": q.question_text,
                "answer": q.answer.text,
                "constraints": [
                    {
                        "type": c.constraint_type,
                        "condition": c.filter_condition
                    }
                    for c in q.constraint_set.constraints
                ]
            }
            for q in generated_questions[:10]  # 只保存前10个问题的详细信息
        ]
    }
    
    return results


def print_results(results):
    """打印测试结果"""
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}\n")
    
    config = results["config"]
    gen = results["generation"]
    div = results["diversity"]
    
    print(f"配置: min={config['min_constraints']}, max={config['max_constraints']}")
    print(f"\n生成统计:")
    print(f"  - 目标数量: {config['target_count']}")
    print(f"  - 成功生成: {gen['successful']} 个")
    print(f"  - 总尝试次数: {gen['total_attempts']} 次")
    print(f"  - 成功率: {gen['success_rate']:.2%}")
    print(f"  - 耗时: {gen['elapsed_time']:.2f} 秒")
    print(f"  - 速度: {gen['questions_per_second']:.2f} 问题/秒")
    
    print(f"\n多样性统计:")
    print(f"  - 唯一问题: {div['unique']}")
    print(f"  - 多样性率: {div['diversity_rate']:.2%}")
    print(f"  - 模板分布: {div['template_distribution']}")
    
    print(f"\n约束数量分布:")
    for count, freq in sorted(results["constraint_counts"].items()):
        print(f"  - {count} 个约束: {freq} 次 ({freq/gen['total_attempts']*100:.1f}%)")
    
    print(f"\n约束类型使用统计:")
    for ctype, freq in sorted(results["constraint_types_used"].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {ctype}: {freq} 次")
    
    print(f"\n模板使用统计:")
    for template, freq in sorted(results["templates_used"].items()):
        print(f"  - 模板 {template}: {freq} 次")
    
    print(f"\n失败原因统计:")
    for reason, freq in sorted(results["failure_reasons"].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {reason}: {freq} 次 ({freq/gen['total_attempts']*100:.1f}%)")
    
    print(f"\n前3个问题示例:")
    for i, q in enumerate(results["questions"][:3], 1):
        print(f"\n  示例 {i}:")
        print(f"    问题ID: {q['question_id']}")
        print(f"    模板: {q['template_id']}")
        print(f"    难度: {q['difficulty']}")
        print(f"    约束数: {q['constraint_count']}")
        print(f"    问题: {q['question_text']}")
        print(f"    答案: {q['answer'][:100]}...")
        print(f"    约束:")
        for c in q["constraints"]:
            print(f"      - {c['type']}: {c['condition']}")


def main():
    """主函数"""
    # 设置日志
    config = get_config()
    config.verbose = False
    setup_logging(log_level="WARNING", log_file=None, log_dir=None, verbose=False)
    
    # 测试配置列表
    test_configs = [
        # (min_constraints, max_constraints, count, description)
        (1, 1, 100, "基线测试 (单约束)"),
        (2, 2, 100, "双约束测试"),
        (3, 3, 100, "三约束测试"),
        (2, 4, 100, "混合约束测试 (2-4个)"),
        (3, 5, 100, "高约束测试 (3-5个)"),
    ]
    
    all_results = []
    
    for min_c, max_c, count, description in test_configs:
        print(f"\n\n{'#'*80}")
        print(f"# {description}")
        print(f"{'#'*80}")
        
        results = test_constraint_config(min_c, max_c, count, verbose=False)
        print_results(results)
        
        all_results.append({
            "description": description,
            "results": results
        })
        
        # 短暂暂停
        time.sleep(1)
    
    # 保存完整结果
    output_dir = Path("output/multi_constraint_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_results_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n{'='*80}")
    print(f"完整测试结果已保存到: {output_file}")
    print(f"{'='*80}\n")
    
    # 生成对比表格
    print("\n" + "="*80)
    print("对比表格")
    print("="*80 + "\n")
    
    print(f"{'配置':<20} {'成功数':<10} {'成功率':<10} {'耗时(秒)':<12} {'速度(问/秒)':<15} {'唯一问题':<10} {'多样性率':<10}")
    print("-" * 100)
    
    for item in all_results:
        desc = item["description"]
        r = item["results"]
        config = r["config"]
        gen = r["generation"]
        div = r["diversity"]
        
        config_str = f"{config['min_constraints']}-{config['max_constraints']}约束"
        
        print(f"{config_str:<20} {gen['successful']:<10} {gen['success_rate']:<10.2%} "
              f"{gen['elapsed_time']:<12.2f} {gen['questions_per_second']:<15.2f} "
              f"{div['unique']:<10} {div['diversity_rate']:<10.2%}")


if __name__ == "__main__":
    main()
