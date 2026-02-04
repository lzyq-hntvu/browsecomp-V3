#!/usr/bin/env python3
"""
测试多跳遍历功能

验证多跳约束是否正常工作
"""

import json
from pathlib import Path

from browsecomp_v3.core.config import get_config
from browsecomp_v3.core.models import NodeType, EdgeType, ActionType
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.traversal import GraphTraversal
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator
from browsecomp_v3.templates.template_selector import TemplateSelector
from browsecomp_v3.graph.query_executor import QueryExecutor
from browsecomp_v3.generator.answer_extractor import AnswerExtractor
from browsecomp_v3.generator.question_generator import QuestionGenerator


def test_basic_multi_hop_traversal():
    """测试基本的多跳遍历功能"""
    print("\n" + "="*80)
    print("测试 1: 基本多跳遍历功能")
    print("="*80 + "\n")
    
    # 加载知识图谱
    kg_loader = KnowledgeGraphLoader()
    graph = kg_loader.load()
    traversal = GraphTraversal(graph)
    
    print(f"知识图谱已加载: {kg_loader.node_count} 节点, {kg_loader.edge_count} 边\n")
    
    # 测试 1.1: traverse_with_filter
    print("测试 1.1: traverse_with_filter (Paper → HAS_AUTHOR → Author)")
    papers = kg_loader.get_nodes_by_type(NodeType.PAPER)
    sample_papers = papers[:10]
    
    authors = traversal.traverse_with_filter(
        nodes=sample_papers,
        edge_type=EdgeType.HAS_AUTHOR,
        target_node_type=NodeType.AUTHOR
    )
    
    print(f"  起始节点: {len(sample_papers)} 篇论文")
    print(f"  遍历结果: {len(authors)} 个作者")
    print(f"  示例作者ID: {authors[:3]}\n")
    
    # 测试 1.2: traverse_reverse
    print("测试 1.2: traverse_reverse (Author → HAS_AUTHOR(reverse) → Paper)")
    sample_authors = authors[:5]
    
    papers_reverse = traversal.traverse_reverse(
        nodes=sample_authors,
        edge_type=EdgeType.HAS_AUTHOR,
        target_node_type=NodeType.PAPER
    )
    
    print(f"  起始节点: {len(sample_authors)} 个作者")
    print(f"  反向遍历结果: {len(papers_reverse)} 篇论文")
    print(f"  示例论文ID: {papers_reverse[:3]}\n")
    
    # 测试 1.3: chain_traverse (2-hop)
    print("测试 1.3: chain_traverse (Paper → HAS_AUTHOR → Author)")
    chain = [
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Author",
            "direction": "forward"
        }
    ]
    
    result = traversal._chain_traverse(sample_papers, chain)
    print(f"  起始节点: {len(sample_papers)} 篇论文")
    print(f"  链式遍历结果: {len(result)} 个作者")
    print(f"  示例作者ID: {result[:3]}\n")
    
    # 测试 1.4: chain_traverse (3-hop)
    print("测试 1.4: chain_traverse (Paper → HAS_AUTHOR → Author → AFFILIATED_WITH → Institution)")
    chain_3hop = [
        {
            "edge_type": "HAS_AUTHOR",
            "target_node": "Author",
            "direction": "forward"
        },
        {
            "edge_type": "AFFILIATED_WITH",
            "target_node": "Institution",
            "direction": "forward"
        }
    ]
    
    institutions = traversal._chain_traverse(sample_papers, chain_3hop)
    print(f"  起始节点: {len(sample_papers)} 篇论文")
    print(f"  3跳遍历结果: {len(institutions)} 个机构")
    if institutions:
        print(f"  示例机构ID: {institutions[:3]}")
        # 获取机构名称
        for inst_id in institutions[:3]:
            inst_data = kg_loader.get_node(inst_id)
            print(f"    - {inst_data.get('name', 'Unknown')}")
    print()
    
    return True


def test_multi_hop_with_filter():
    """测试带过滤条件的多跳遍历"""
    print("\n" + "="*80)
    print("测试 2: 带过滤条件的多跳遍历")
    print("="*80 + "\n")
    
    # 加载知识图谱
    kg_loader = KnowledgeGraphLoader()
    graph = kg_loader.load()
    traversal = GraphTraversal(graph)
    
    # 获取所有作者
    authors = kg_loader.get_nodes_by_type(NodeType.AUTHOR)
    print(f"知识图谱中共有 {len(authors)} 个作者\n")
    
    # 选择一个有名字的作者
    test_author_name = None
    for author_id in authors[:100]:
        author_data = kg_loader.get_node(author_id)
        name = author_data.get("name")
        if name and len(name) > 3:
            test_author_name = name
            break
    
    if not test_author_name:
        print("⚠️ 未找到有名字的作者，跳过此测试\n")
        return False
    
    print(f"测试作者名称: {test_author_name}")
    
    # 测试: Paper → HAS_AUTHOR → Author[name=X]
    papers = kg_loader.get_nodes_by_type(NodeType.PAPER)
    sample_papers = papers[:100]
    
    filtered_authors = traversal.traverse_with_filter(
        nodes=sample_papers,
        edge_type=EdgeType.HAS_AUTHOR,
        target_node_type=NodeType.AUTHOR,
        node_filter={"name": {"=": test_author_name}}
    )
    
    print(f"  起始节点: {len(sample_papers)} 篇论文")
    print(f"  过滤条件: name = {test_author_name}")
    print(f"  遍历结果: {len(filtered_authors)} 个匹配的作者\n")
    
    return True


def test_multi_hop_constraint_generation():
    """测试多跳约束生成"""
    print("\n" + "="*80)
    print("测试 3: 多跳约束生成")
    print("="*80 + "\n")
    
    # 初始化组件
    kg_loader = KnowledgeGraphLoader()
    kg_loader.load()
    constraint_generator = ConstraintGenerator(kg_loader)
    
    print("测试约束类型:")
    print("  - person_name (2跳)")
    print("  - author_order (2跳)")
    print("  - institution_affiliation (3跳)\n")
    
    # 尝试生成多跳约束
    template_selector = TemplateSelector()
    template_id = "A"  # Paper-Author-Institution模板
    
    success_count = 0
    multi_hop_count = 0
    
    for i in range(10):
        try:
            constraint_set = constraint_generator.generate(
                template_id=template_id,
                min_constraints=2,
                max_constraints=3
            )
            
            success_count += 1
            
            # 检查是否包含多跳约束
            for constraint in constraint_set.constraints:
                if constraint.action == ActionType.MULTI_HOP_TRAVERSE:
                    multi_hop_count += 1
                    print(f"  ✓ 生成多跳约束: {constraint.constraint_type}")
                    print(f"    - 描述: {constraint.description}")
                    print(f"    - 遍历链长度: {len(constraint.traversal_chain or [])}")
                    print(f"    - 需要回溯: {constraint.requires_backtrack}")
                    break
        
        except Exception as e:
            print(f"  ✗ 约束生成失败: {e}")
            continue
    
    print(f"\n生成统计:")
    print(f"  - 成功生成: {success_count}/10")
    print(f"  - 多跳约束: {multi_hop_count}\n")
    
    return success_count > 0


def test_end_to_end_multi_hop():
    """端到端测试：生成包含多跳约束的问题"""
    print("\n" + "="*80)
    print("测试 4: 端到端多跳约束问题生成")
    print("="*80 + "\n")
    
    # 初始化所有组件
    config = get_config()
    kg_loader = KnowledgeGraphLoader()
    kg_loader.load()
    
    template_selector = TemplateSelector()
    constraint_generator = ConstraintGenerator(kg_loader)
    query_executor = QueryExecutor(kg_loader)
    question_generator = QuestionGenerator(kg_loader)
    answer_extractor = AnswerExtractor()
    
    print(f"知识图谱已加载: {kg_loader.node_count} 节点, {kg_loader.edge_count} 边\n")
    
    # 尝试生成10个问题
    generated_questions = []
    attempts = 0
    max_attempts = 50
    
    while len(generated_questions) < 5 and attempts < max_attempts:
        attempts += 1
        
        try:
            # 1. 选择模板
            template_id = template_selector.select(mode="random")
            
            # 2. 生成约束
            constraint_set = constraint_generator.generate(
                template_id=template_id,
                min_constraints=2,
                max_constraints=3
            )
            
            # 检查是否包含多跳约束
            has_multi_hop = any(
                c.action == ActionType.MULTI_HOP_TRAVERSE 
                for c in constraint_set.constraints
            )
            
            if not has_multi_hop:
                continue  # 只关注包含多跳约束的问题
            
            # 3. 执行查询
            query_result = query_executor.execute(constraint_set)
            
            if len(query_result.candidates) == 0:
                continue
            
            # 选择候选
            import random
            candidate_id = random.choice(query_result.candidates)
            
            # 4. 提取答案
            candidate_data = kg_loader.get_node(candidate_id)
            answer = answer_extractor.extract(candidate_id, candidate_data, kg_loader)
            
            # 5. 生成问题
            question = question_generator.generate(
                constraint_set=constraint_set,
                reasoning_chain=query_result.reasoning_chain,
                answer_entity_id=candidate_id,
                answer_text=answer.text
            )
            
            generated_questions.append({
                "question_id": question.question_id,
                "template_id": question.template_id,
                "question_text": question.question_text,
                "answer": answer.text,
                "constraints": [
                    {
                        "type": c.constraint_type,
                        "action": c.action.value,
                        "description": c.description,
                        "is_multi_hop": c.action == ActionType.MULTI_HOP_TRAVERSE
                    }
                    for c in constraint_set.constraints
                ],
                "reasoning_hops": query_result.reasoning_chain.total_hops,
                "candidates_count": len(query_result.candidates)
            })
            
            print(f"✓ 成功生成问题 {len(generated_questions)}/5")
            
        except Exception as e:
            continue
    
    print(f"\n生成完成:")
    print(f"  - 尝试次数: {attempts}")
    print(f"  - 成功生成: {len(generated_questions)} 个包含多跳约束的问题\n")
    
    # 显示问题示例
    for i, q in enumerate(generated_questions, 1):
        print(f"示例 {i}:")
        print(f"  问题ID: {q['question_id']}")
        print(f"  模板: {q['template_id']}")
        print(f"  问题: {q['question_text']}")
        print(f"  答案: {q['answer'][:100]}...")
        print(f"  推理跳数: {q['reasoning_hops']}")
        print(f"  候选数: {q['candidates_count']}")
        print(f"  约束:")
        for c in q['constraints']:
            hop_marker = " [多跳]" if c['is_multi_hop'] else ""
            print(f"    - {c['type']}: {c['description']}{hop_marker}")
        print()
    
    # 保存结果
    output_dir = Path("output/multi_hop_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "multi_hop_questions.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(generated_questions, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 测试结果已保存到: {output_file}\n")
    
    return len(generated_questions) > 0


def main():
    """主函数"""
    print("\n" + "#"*80)
    print("# 多跳遍历功能测试")
    print("#"*80)
    
    results = []
    
    # 测试1: 基本多跳遍历
    try:
        result = test_basic_multi_hop_traversal()
        results.append(("基本多跳遍历", result))
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        results.append(("基本多跳遍历", False))
    
    # 测试2: 带过滤条件的多跳遍历
    try:
        result = test_multi_hop_with_filter()
        results.append(("带过滤条件的多跳遍历", result))
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        results.append(("带过滤条件的多跳遍历", False))
    
    # 测试3: 多跳约束生成
    try:
        result = test_multi_hop_constraint_generation()
        results.append(("多跳约束生成", result))
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        results.append(("多跳约束生成", False))
    
    # 测试4: 端到端多跳问题生成
    try:
        result = test_end_to_end_multi_hop()
        results.append(("端到端多跳问题生成", result))
    except Exception as e:
        print(f"✗ 测试失败: {e}\n")
        results.append(("端到端多跳问题生成", False))
    
    # 输出总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80 + "\n")
    
    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 测试通过\n")


if __name__ == "__main__":
    main()
