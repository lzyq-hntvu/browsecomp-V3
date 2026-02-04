"""
测试 Coauthor 约束（5-hop 遍历）

Coauthor 约束的遍历路径：
Paper A → HAS_AUTHOR → Author X → HAS_AUTHOR(reverse) → Paper B → HAS_AUTHOR → Author Y[name=Z]

这是最复杂的多跳约束，需要验证：
1. 基础遍历功能是否正常
2. 约束生成器能否正确生成 coauthor 约束
3. 端到端问题生成是否能正确使用 coauthor 约束
"""

import logging
from typing import List, Dict, Any

from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.traversal import GraphTraversal
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator
from browsecomp_v3.core.models import EdgeType, NodeType
from browsecomp_v3.question_generator import QuestionGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_basic_5hop_traversal():
    """测试基础 5-hop 遍历：找到某作者的合作者的论文"""
    logger.info("\n" + "="*80)
    logger.info("Test 1: 基础 5-hop 遍历")
    logger.info("="*80)
    
    kg_loader = KnowledgeGraphLoader()
    graph = kg_loader.load()
    traversal = GraphTraversal(graph)
    
    # 找到几篇论文作为起点
    papers = [node for node, data in graph.nodes(data=True) 
              if data.get("type") == "Paper"][:5]
    
    logger.info(f"起始论文数: {len(papers)}")
    
    # 找一个真实存在的作者名字
    test_authors = []
    for paper_id in papers:
        authors = traversal.traverse_with_filter(
            [paper_id],
            EdgeType.HAS_AUTHOR,
            NodeType.AUTHOR
        )
        for author_id in authors[:1]:  # 只取第一个作者
            author_data = graph.nodes.get(author_id, {})
            author_name = author_data.get("name")
            if author_name:
                test_authors.append(author_name)
                break
        if test_authors:
            break
    
    if not test_authors:
        logger.warning("无法找到测试作者")
        return False
    
    test_author_name = test_authors[0]
    logger.info(f"测试作者: {test_author_name}")
    
    # 执行 5-hop 遍历
    traversal_chain = [
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Author",
        },
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Paper",
            "direction": "reverse",
        },
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Author",
            "node_filter": {"name": {"=": test_author_name}},
        },
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Paper",
            "direction": "reverse",
        },
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Author",
        }
    ]
    
    result = traversal._chain_traverse(papers, traversal_chain)
    
    logger.info(f"遍历结果: {len(result)} 个作者节点")
    
    if result:
        # 验证结果
        for author_id in result[:3]:
            author_data = graph.nodes.get(author_id, {})
            logger.info(f"  - 作者: {author_data.get('name', 'N/A')}")
        logger.info("✓ 5-hop 遍历成功")
        return True
    else:
        logger.warning("✗ 5-hop 遍历返回空结果")
        return False


def test_coauthor_constraint_generation():
    """测试 coauthor 约束生成"""
    logger.info("\n" + "="*80)
    logger.info("Test 2: Coauthor 约束生成")
    logger.info("="*80)
    
    kg_loader = KnowledgeGraphLoader()
    constraint_gen = ConstraintGenerator(kg_loader=kg_loader)
    
    # 检查 coauthor 是否在有效约束类型中
    if "coauthor" not in constraint_gen.valid_constraint_types:
        logger.error("✗ coauthor 不在 valid_constraint_types 中")
        return False
    
    logger.info("✓ coauthor 已添加到有效约束类型")
    
    # 尝试生成包含 coauthor 约束的约束集
    attempts = 0
    success = False
    
    for template_id in ["template_A", "template_B", "template_C"]:
        for _ in range(10):  # 尝试 10 次
            attempts += 1
            try:
                constraint_set = constraint_gen.generate(
                    template_id=template_id,
                    min_constraints=1,
                    max_constraints=3
                )
                
                # 检查是否有 coauthor 约束
                for constraint in constraint_set.constraints:
                    if constraint.constraint_type == "coauthor":
                        logger.info(f"✓ 成功生成 coauthor 约束 (尝试 {attempts} 次)")
                        logger.info(f"  - 描述: {constraint.description}")
                        logger.info(f"  - 遍历链长度: {len(constraint.traversal_chain)}")
                        logger.info(f"  - 需要回溯: {constraint.requires_backtrack}")
                        success = True
                        break
                
                if success:
                    break
                    
            except Exception as e:
                logger.debug(f"生成约束失败: {e}")
                continue
        
        if success:
            break
    
    if not success:
        logger.warning(f"✗ 在 {attempts} 次尝试后未能生成 coauthor 约束")
        return False
    
    return True


def test_coauthor_end_to_end():
    """测试端到端问题生成（包含 coauthor 约束）"""
    logger.info("\n" + "="*80)
    logger.info("Test 3: 端到端问题生成 (含 coauthor 约束)")
    logger.info("="*80)
    
    kg_loader = KnowledgeGraphLoader()
    qg = QuestionGenerator(kg_loader=kg_loader)
    
    # 强制使用 coauthor 约束
    original_types = qg.constraint_generator.valid_constraint_types.copy()
    
    # 测试 1: 仅使用 coauthor
    logger.info("\n测试 3a: 仅使用 coauthor 约束")
    qg.constraint_generator.valid_constraint_types = {"coauthor"}
    
    generated = 0
    for _ in range(20):
        try:
            question = qg.generate_one()
            if question:
                generated += 1
                logger.info(f"\n✓ 生成问题 {generated}")
                logger.info(f"  问题: {question.question[:100]}...")
                logger.info(f"  约束数量: {len(question.constraints)}")
                for c in question.constraints:
                    logger.info(f"    - {c.constraint_type}: {c.description}")
                logger.info(f"  候选集大小: {len(question.candidate_nodes)}")
                logger.info(f"  答案数量: {len(question.answers)}")
                
                if generated >= 3:
                    break
        except Exception as e:
            logger.debug(f"生成失败: {e}")
            continue
    
    if generated == 0:
        logger.warning("✗ 无法生成包含 coauthor 约束的问题")
        qg.constraint_generator.valid_constraint_types = original_types
        return False
    
    logger.info(f"\n✓ 成功生成 {generated} 个包含 coauthor 约束的问题")
    
    # 测试 2: 混合约束（包含 coauthor）
    logger.info("\n测试 3b: 混合约束（包含 coauthor）")
    qg.constraint_generator.valid_constraint_types = {
        "temporal", "author_count", "citation",
        "person_name", "institution_affiliation",
        "coauthor"
    }
    
    coauthor_count = 0
    total_generated = 0
    
    for _ in range(50):
        try:
            question = qg.generate_one()
            if question:
                total_generated += 1
                has_coauthor = any(c.constraint_type == "coauthor" for c in question.constraints)
                if has_coauthor:
                    coauthor_count += 1
                    logger.info(f"\n✓ 生成包含 coauthor 的混合约束问题 ({coauthor_count}/{total_generated})")
                    for c in question.constraints:
                        logger.info(f"    - {c.constraint_type}: {c.description}")
        except Exception as e:
            logger.debug(f"生成失败: {e}")
            continue
    
    # 恢复原始约束类型
    qg.constraint_generator.valid_constraint_types = original_types
    
    logger.info(f"\n混合约束测试结果:")
    logger.info(f"  总生成: {total_generated}")
    logger.info(f"  包含 coauthor: {coauthor_count} ({coauthor_count/total_generated*100:.1f}%)")
    
    return coauthor_count > 0


def test_coauthor_scale():
    """大规模测试 coauthor 约束"""
    logger.info("\n" + "="*80)
    logger.info("Test 4: 大规模测试 (100 questions)")
    logger.info("="*80)
    
    kg_loader = KnowledgeGraphLoader()
    qg = QuestionGenerator(kg_loader=kg_loader)
    
    # 使用所有约束类型（包括 coauthor）
    qg.constraint_generator.valid_constraint_types = {
        "temporal", "author_count", "citation", "title_format",
        "person_name", "author_order", "institution_affiliation",
        "coauthor"
    }
    
    questions = []
    stats = {
        "total": 0,
        "with_coauthor": 0,
        "coauthor_only": 0,
        "constraint_counts": {},
        "success_rate": 0.0
    }
    
    attempts = 0
    max_attempts = 200
    
    while len(questions) < 100 and attempts < max_attempts:
        attempts += 1
        try:
            question = qg.generate_one()
            if question:
                questions.append(question)
                stats["total"] += 1
                
                # 统计约束
                has_coauthor = False
                constraint_types = []
                for c in question.constraints:
                    constraint_types.append(c.constraint_type)
                    if c.constraint_type == "coauthor":
                        has_coauthor = True
                
                if has_coauthor:
                    stats["with_coauthor"] += 1
                    if len(constraint_types) == 1:
                        stats["coauthor_only"] += 1
                
                # 约束数量统计
                num_constraints = len(question.constraints)
                stats["constraint_counts"][num_constraints] = stats["constraint_counts"].get(num_constraints, 0) + 1
                
                if stats["total"] % 10 == 0:
                    logger.info(f"进度: {stats['total']}/100 (尝试 {attempts} 次)")
        
        except Exception as e:
            logger.debug(f"生成失败: {e}")
            continue
    
    stats["success_rate"] = stats["total"] / attempts * 100 if attempts > 0 else 0
    
    # 输出统计结果
    logger.info("\n" + "="*80)
    logger.info("大规模测试统计结果")
    logger.info("="*80)
    logger.info(f"总生成问题数: {stats['total']}")
    logger.info(f"总尝试次数: {attempts}")
    logger.info(f"成功率: {stats['success_rate']:.1f}%")
    logger.info(f"\nCoauthor 约束统计:")
    logger.info(f"  包含 coauthor 约束: {stats['with_coauthor']} ({stats['with_coauthor']/stats['total']*100:.1f}%)")
    logger.info(f"  仅 coauthor 约束: {stats['coauthor_only']} ({stats['coauthor_only']/stats['total']*100:.1f}%)")
    logger.info(f"\n约束数量分布:")
    for num, count in sorted(stats['constraint_counts'].items()):
        logger.info(f"  {num} 个约束: {count} ({count/stats['total']*100:.1f}%)")
    
    # 示例问题
    logger.info("\n示例问题（包含 coauthor）:")
    coauthor_examples = [q for q in questions if any(c.constraint_type == "coauthor" for c in q.constraints)][:3]
    for i, q in enumerate(coauthor_examples, 1):
        logger.info(f"\n示例 {i}:")
        logger.info(f"  问题: {q.question[:150]}...")
        logger.info(f"  约束:")
        for c in q.constraints:
            logger.info(f"    - {c.constraint_type}: {c.description}")
        logger.info(f"  候选集: {len(q.candidate_nodes)} 篇论文")
        logger.info(f"  答案数: {len(q.answers)}")
    
    return stats['with_coauthor'] > 0


def main():
    """运行所有测试"""
    logger.info("开始测试 Coauthor 约束（Phase 3）")
    logger.info("="*80)
    
    results = {}
    
    # Test 1: 基础遍历
    results['basic_traversal'] = test_basic_5hop_traversal()
    
    # Test 2: 约束生成
    results['constraint_generation'] = test_coauthor_constraint_generation()
    
    # Test 3: 端到端测试
    results['end_to_end'] = test_coauthor_end_to_end()
    
    # Test 4: 大规模测试
    results['scale_test'] = test_coauthor_scale()
    
    # 总结
    logger.info("\n" + "="*80)
    logger.info("测试总结")
    logger.info("="*80)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("✓ 所有测试通过！Coauthor 约束实现成功")
    else:
        logger.info("✗ 部分测试失败，需要调试")
    logger.info("="*80)
    
    return all_passed


if __name__ == "__main__":
    main()
