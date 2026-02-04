"""
测试所有 30 种约束类型的生成

目标：
1. 验证所有 30 种约束类型都在白名单中
2. 测试每种约束的生成成功率
3. 识别值生成器的问题
4. 统计哪些约束可以正常工作
"""

import logging
from collections import Counter, defaultdict

from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_all_constraint_types():
    """测试所有 30 种约束类型"""
    logger.info("="*80)
    logger.info("测试所有 30 种约束类型")
    logger.info("="*80)
    
    kg_loader = KnowledgeGraphLoader()
    constraint_gen = ConstraintGenerator(kg_loader=kg_loader)
    
    # 检查白名单
    enabled_types = constraint_gen.valid_constraint_types
    logger.info(f"\n白名单中的约束类型数: {len(enabled_types)}")
    
    if len(enabled_types) != 30:
        logger.warning(f"⚠️ 白名单中只有 {len(enabled_types)} 种约束，应该有 30 种")
    else:
        logger.info("✓ 白名单已包含所有 30 种约束类型")
    
    # 按 Phase 分组显示
    phases = {
        "Phase 1": ["temporal", "author_count", "citation", "title_format"],
        "Phase 2": ["person_name", "author_order", "institution_affiliation"],
        "Phase 3": ["coauthor", "cited_by_author", "publication_venue"],
        "Phase 4": ["institution_founding", "paper_structure", "position_title", 
                    "birth_info", "location", "editorial_role", "publication_details", "department"],
        "Phase 5": ["education_degree", "award_honor", "research_topic", "method_technique",
                    "data_sample", "acknowledgment", "funding", "conference_event", "technical_entity"],
        "Phase 6": ["publication_history", "measurement_value", "company", "advisor"]
    }
    
    logger.info("\n按 Phase 分组:")
    for phase, types in phases.items():
        enabled_count = sum(1 for t in types if t in enabled_types)
        logger.info(f"  {phase}: {enabled_count}/{len(types)} 种")
        for t in types:
            status = "✓" if t in enabled_types else "✗"
            logger.info(f"    {status} {t}")
    
    return enabled_types


def test_constraint_generation_rates():
    """测试每种约束的生成成功率"""
    logger.info("\n" + "="*80)
    logger.info("测试约束生成成功率")
    logger.info("="*80)
    
    kg_loader = KnowledgeGraphLoader()
    constraint_gen = ConstraintGenerator(kg_loader=kg_loader)
    
    # 统计数据
    stats = defaultdict(lambda: {"attempts": 0, "success": 0, "examples": []})
    
    # 尝试生成每种约束
    templates = ["A", "B", "C", "D", "E", "F", "G"]
    attempts_per_type = 50  # 每种约束尝试生成 50 次
    
    logger.info(f"\n尝试生成每种约束 {attempts_per_type} 次...\n")
    
    total_attempts = 0
    for _ in range(attempts_per_type * 10):  # 多尝试一些次数
        if total_attempts >= attempts_per_type * 30:
            break
            
        for template_id in templates:
            try:
                constraint_set = constraint_gen.generate(
                    template_id=template_id,
                    min_constraints=1,
                    max_constraints=2
                )
                
                for constraint in constraint_set.constraints:
                    ctype = constraint.constraint_type
                    stats[ctype]["attempts"] += 1
                    
                    # 检查是否生成成功（没有 unknown 值）
                    if constraint.filter_condition and constraint.filter_condition != "unknown":
                        stats[ctype]["success"] += 1
                        
                        # 保存示例
                        if len(stats[ctype]["examples"]) < 2:
                            stats[ctype]["examples"].append({
                                "description": constraint.description,
                                "condition": str(constraint.filter_condition)[:50]
                            })
                
                total_attempts += 1
                
            except Exception as e:
                continue
    
    # 输出结果
    logger.info("\n约束生成统计（按成功率排序）:\n")
    logger.info(f"{'约束类型':<25} {'尝试':<8} {'成功':<8} {'成功率':<10} 示例")
    logger.info("-" * 100)
    
    # 按成功率排序
    sorted_stats = sorted(stats.items(), 
                         key=lambda x: x[1]["success"] / max(x[1]["attempts"], 1) if x[1]["attempts"] > 0 else 0,
                         reverse=True)
    
    success_groups = {"high": [], "medium": [], "low": [], "failed": []}
    
    for ctype, data in sorted_stats:
        attempts = data["attempts"]
        success = data["success"]
        rate = success / attempts * 100 if attempts > 0 else 0
        
        example = data["examples"][0]["description"] if data["examples"] else "N/A"
        
        # 分类
        if rate >= 80:
            group = "high"
            emoji = "✓"
        elif rate >= 40:
            group = "medium"
            emoji = "○"
        elif rate > 0:
            group = "low"
            emoji = "△"
        else:
            group = "failed"
            emoji = "✗"
        
        success_groups[group].append(ctype)
        
        logger.info(f"{emoji} {ctype:<24} {attempts:<8} {success:<8} {rate:>6.1f}%   {example[:40]}")
    
    # 统计缺失的约束类型
    all_30_types = set()
    phases = {
        "Phase 1": ["temporal", "author_count", "citation", "title_format"],
        "Phase 2": ["person_name", "author_order", "institution_affiliation"],
        "Phase 3": ["coauthor", "cited_by_author", "publication_venue"],
        "Phase 4": ["institution_founding", "paper_structure", "position_title", 
                    "birth_info", "location", "editorial_role", "publication_details", "department"],
        "Phase 5": ["education_degree", "award_honor", "research_topic", "method_technique",
                    "data_sample", "acknowledgment", "funding", "conference_event", "technical_entity"],
        "Phase 6": ["publication_history", "measurement_value", "company", "advisor"]
    }
    
    for types in phases.values():
        all_30_types.update(types)
    
    not_generated = all_30_types - set(stats.keys())
    
    if not_generated:
        logger.info(f"\n⚠️ 未生成的约束类型 ({len(not_generated)} 种):")
        for ctype in sorted(not_generated):
            logger.info(f"  ✗ {ctype}")
    
    # 总结
    logger.info("\n" + "="*80)
    logger.info("生成成功率总结")
    logger.info("="*80)
    logger.info(f"✓ 高成功率 (≥80%): {len(success_groups['high'])} 种")
    for t in success_groups['high'][:10]:
        logger.info(f"    - {t}")
    if len(success_groups['high']) > 10:
        logger.info(f"    ... 还有 {len(success_groups['high']) - 10} 种")
    
    logger.info(f"\n○ 中等成功率 (40-79%): {len(success_groups['medium'])} 种")
    for t in success_groups['medium']:
        logger.info(f"    - {t}")
    
    logger.info(f"\n△ 低成功率 (1-39%): {len(success_groups['low'])} 种")
    for t in success_groups['low']:
        logger.info(f"    - {t}")
    
    logger.info(f"\n✗ 完全失败 (0%): {len(success_groups['failed'])} 种")
    for t in success_groups['failed']:
        logger.info(f"    - {t}")
    
    logger.info(f"\n未出现: {len(not_generated)} 种")
    
    # 计算总体统计
    total_attempts_all = sum(s["attempts"] for s in stats.values())
    total_success_all = sum(s["success"] for s in stats.values())
    overall_rate = total_success_all / total_attempts_all * 100 if total_attempts_all > 0 else 0
    
    logger.info(f"\n总体统计:")
    logger.info(f"  总尝试: {total_attempts_all}")
    logger.info(f"  总成功: {total_success_all}")
    logger.info(f"  总成功率: {overall_rate:.1f}%")
    logger.info(f"  已生成约束类型数: {len(stats)}/30")
    
    return stats, success_groups, not_generated


def test_small_question_generation():
    """测试小规模问题生成（50 questions）"""
    logger.info("\n" + "="*80)
    logger.info("小规模问题生成测试 (50 questions)")
    logger.info("="*80)
    
    from browsecomp_v3.generator.question_generator import QuestionGenerator
    
    kg_loader = KnowledgeGraphLoader()
    qg = QuestionGenerator(kg_loader=kg_loader)
    
    # 生成 50 个问题
    try:
        questions = qg.generate(count=50, diversity_check=True)
    except TypeError:
        # 如果不支持参数，尝试其他方式
        try:
            questions = qg.generate(50)
        except Exception as e:
            logger.warning(f"⚠️ 无法调用 generate: {e}")
            logger.info("尝试手动生成...")
            questions = []
            return questions, Counter()
    
    constraint_usage = Counter()
    
    if questions:
        for question in questions:
            for c in question.constraints:
                constraint_usage[c.constraint_type] += 1
    
    logger.info(f"\n生成结果:")
    logger.info(f"  成功生成: {len(questions)} 个问题")
    
    if not questions:
        logger.warning("⚠️ 未能生成任何问题")
        return questions, constraint_usage
    
    logger.info(f"\n约束类型使用统计 (Top 15):")
    for ctype, count in constraint_usage.most_common(15):
        percentage = count / len(questions) * 100
        logger.info(f"  {ctype:<25} {count:>3} 次 ({percentage:>5.1f}%)")
    
    logger.info(f"\n使用的约束类型总数: {len(constraint_usage)}/30")
    
    # 未使用的约束
    all_30 = set()
    phases = {
        "Phase 1": ["temporal", "author_count", "citation", "title_format"],
        "Phase 2": ["person_name", "author_order", "institution_affiliation"],
        "Phase 3": ["coauthor", "cited_by_author", "publication_venue"],
        "Phase 4": ["institution_founding", "paper_structure", "position_title", 
                    "birth_info", "location", "editorial_role", "publication_details", "department"],
        "Phase 5": ["education_degree", "award_honor", "research_topic", "method_technique",
                    "data_sample", "acknowledgment", "funding", "conference_event", "technical_entity"],
        "Phase 6": ["publication_history", "measurement_value", "company", "advisor"]
    }
    for types in phases.values():
        all_30.update(types)
    
    unused = all_30 - set(constraint_usage.keys())
    if unused:
        logger.info(f"\n未使用的约束类型 ({len(unused)} 种):")
        for t in sorted(unused):
            logger.info(f"  - {t}")
    
    return questions, constraint_usage


def main():
    """运行所有测试"""
    logger.info("="*80)
    logger.info("30 种约束类型全面测试")
    logger.info("="*80)
    
    # Test 1: 检查白名单
    enabled_types = test_all_constraint_types()
    
    # Test 2: 测试生成成功率
    stats, success_groups, not_generated = test_constraint_generation_rates()
    
    # Test 3: 小规模问题生成（需要确保 QuestionGenerator 可用）
    try:
        questions, constraint_usage = test_small_question_generation()
    except Exception as e:
        logger.warning(f"\n⚠️ 小规模问题生成测试跳过: {e}")
        questions = []
        constraint_usage = Counter()
    
    # 最终总结
    logger.info("\n" + "="*80)
    logger.info("最终总结")
    logger.info("="*80)
    logger.info(f"✓ 白名单约束类型: {len(enabled_types)}/30")
    logger.info(f"✓ 高成功率约束: {len(success_groups['high'])} 种")
    logger.info(f"○ 中等成功率约束: {len(success_groups['medium'])} 种")
    logger.info(f"△ 低成功率约束: {len(success_groups['low'])} 种")
    logger.info(f"✗ 完全失败约束: {len(success_groups['failed'])} 种")
    logger.info(f"⚠️ 未生成约束: {len(not_generated)} 种")
    
    if questions:
        logger.info(f"\n问题生成测试:")
        logger.info(f"  生成问题数: {len(questions)}")
        logger.info(f"  使用约束类型数: {len(constraint_usage)}/30")
    
    logger.info("\n" + "="*80)
    logger.info("测试完成！")
    logger.info("="*80)


if __name__ == "__main__":
    main()
