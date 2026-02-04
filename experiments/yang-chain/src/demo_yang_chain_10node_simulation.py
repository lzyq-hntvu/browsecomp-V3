#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 10节点链模拟演示

由于API限流，使用模拟数据演示10节点链的构建和问题生成
展示如果数据充足，系统如何工作
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class SimulatedPaper:
    """模拟论文数据"""
    paper_id: str
    title: str
    year: int
    authors: List[str]
    citation_count: int


def generate_simulated_kg(num_papers: int = 50, avg_citations: int = 5) -> Dict:
    """
    生成模拟知识图谱
    模拟真实引用网络：幂律分布（少数论文被大量引用）
    """
    print(f"生成模拟KG: {num_papers}篇论文，平均{avg_citations}引用...")

    # 生成论文
    topics = [
        "metal-organic frameworks", "catalysis", "nanomaterials",
        "perovskites", "thermoelectric", "battery", "solar cells",
        "quantum dots", "graphene", "superconductors"
    ]

    methods = [
        "synthesis", "characterization", "simulation", "optimization",
        "fabrication", "analysis", "design", "modification"
    ]

    papers = {}
    for i in range(num_papers):
        topic = random.choice(topics)
        method = random.choice(methods)
        year = random.randint(2010, 2023)

        papers[f"paper_{i}"] = SimulatedPaper(
            paper_id=f"paper_{i}",
            title=f"{method.capitalize()} of {topic} for energy applications (Study {i})",
            year=year,
            authors=[f"Author_{i*3}", f"Author_{i*3+1}"],
            citation_count=random.randint(0, 100)
        )

    # 生成引用图（确保有足够的长链）
    citation_graph = {}

    # 策略：创建链式结构 + 随机引用
    for i in range(num_papers - 1):
        paper_id = f"paper_{i}"
        citations = []

        # 链式引用：每篇论文引用后面的几篇（形成链）
        chain_refs = min(3, num_papers - i - 1)
        for j in range(1, chain_refs + 1):
            if random.random() < 0.7:  # 70%概率形成链
                citations.append(f"paper_{i+j}")

        # 随机引用
        random_refs = random.randint(0, avg_citations - len(citations))
        for _ in range(random_refs):
            target = f"paper_{random.randint(0, num_papers-1)}"
            if target != paper_id and target not in citations:
                citations.append(target)

        if citations:
            citation_graph[paper_id] = citations

    return {
        "papers": papers,
        "citation_graph": citation_graph
    }


def build_chain_with_backtrack(
    graph: Dict[str, List[str]],
    start: str,
    target_length: int = 10
) -> List[str]:
    """
    使用回溯算法构建链
    """
    print(f"\n构建{target_length}节点链，起点: {start}")

    longest = []
    visited = set()

    def dfs(current: str, path: List[str]):
        nonlocal longest

        if len(path) > len(longest):
            longest = path.copy()
            if len(longest) % 2 == 0 or len(longest) == target_length:  # 每2个节点打印一次
                print(f"  当前最长: {len(longest)}节点")

            if len(longest) >= target_length:
                return True

        # 获取可用引用
        candidates = graph.get(current, [])
        # 按引用数排序（优先选择引用多的，更可能形成长链）
        candidates = sorted(candidates, key=lambda x: len(graph.get(x, [])), reverse=True)

        for next_paper in candidates:
            if next_paper not in visited:
                visited.add(next_paper)
                path.append(next_paper)

                if dfs(next_paper, path):
                    return True

                path.pop()
                visited.remove(next_paper)

        return False

    visited.add(start)
    dfs(start, [start])

    return longest


def generate_10node_questions(chain: List[str], papers: Dict[str, SimulatedPaper]) -> List[Dict]:
    """
    为10节点链生成复杂问题
    """
    if len(chain) < 5:
        return []

    questions = []

    # 1. 完整链描述问题
    paper_start = papers[chain[0]]
    paper_mid = papers[chain[len(chain)//2]]
    paper_end = papers[chain[-1]]

    q1 = {
        "type": "expert_full_chain",
        "difficulty": "expert",
        "question": f"从{paper_start.year}年的研究《{paper_start.title[:40]}...》出发，"
                   f"经过一系列引用，最终到达关于{paper_end.title.split()[-4:]}的研究。"
                   f"这条引用链的中间论文使用了什么方法？",
        "answer": paper_mid.title,
        "chain": " -> ".join(chain),
        "chain_length": len(chain)
    }
    questions.append(q1)

    # 2. 跳跃推理（起点+终点，问中间）
    if len(chain) >= 6:
        paper_3 = papers[chain[2]]
        paper_7 = papers[chain[6]]

        q2 = {
            "type": "expert_hop",
            "difficulty": "expert",
            "question": f"一篇关于{paper_start.title[:30]}...的研究（{paper_start.year}年）"
                       f"引用了论文A，A引用了B，B引用了C，C引用了论文D。"
                       f"D是一篇关于{paper_end.title[:30]}...的研究（{paper_end.year}年）。"
                       f"论文B的标题是什么？",
            "answer": paper_mid.title,
            "chain": " -> ".join(chain[:7]),
            "chain_length": 7
        }
        questions.append(q2)

    # 3. 多约束筛选
        paper_4 = papers[chain[3]]
        paper_5 = papers[chain[4]]

        q3 = {
            "type": "hard_multi_constraint",
            "difficulty": "hard",
            "question": f"在{paper_start.year}年发表的一篇关于{paper_start.title[:20]}...的研究中，"
                       f"哪篇被引用的论文同时满足：(1)发表于{paper_4.year}年后，"
                       f"(2)标题包含'{paper_5.title.split()[0]}'，"
                       f"(3)在引用链中距离起点至少4跳？",
            "answer": paper_5.title,
            "chain": " -> ".join(chain[:6]),
            "chain_length": 6
        }
        questions.append(q3)

    # 4. 反向推理（从中间推导起点）
    if len(chain) >= 8:
        paper_6 = papers[chain[5]]

        q4 = {
            "type": "hard_reverse",
            "difficulty": "hard",
            "question": f"一篇关于{paper_mid.title[:30]}...的研究（{paper_mid.year}年）"
                       f"被某篇更早的论文引用。该早期论文又引用了一篇关于"
                       f"{paper_6.title[:20]}...的研究。"
                       f"这条引用链的起始论文发表年份是？",
            "answer": str(paper_start.year),
            "chain": " -> ".join(chain[:7]),
            "chain_length": 7
        }
        questions.append(q4)

    # 5. 计数问题
    year_counts = {}
    for pid in chain:
        year = papers[pid].year
        year_counts[year] = year_counts.get(year, 0) + 1

    if year_counts:
        most_common_year = max(year_counts.items(), key=lambda x: x[1])

        q5 = {
            "type": "medium_count",
            "difficulty": "medium",
            "question": f"在从《{paper_start.title[:30]}...》到"
                       f"《{paper_end.title[:30]}...》的引用链中，"
                       f"共有多少篇论文发表于{most_common_year[0]}年？",
            "answer": str(most_common_year[1]),
            "chain": " -> ".join(chain),
            "chain_length": len(chain)
        }
        questions.append(q5)

    return questions


def print_chain_details(chain: List[str], papers: Dict[str, SimulatedPaper]):
    """打印链详情"""
    print(f"\n{'='*70}")
    print(f"链详情 ({len(chain)}节点)")
    print(f"{'='*70}")

    for i, pid in enumerate(chain):
        paper = papers[pid]
        print(f"\n[{i+1:2d}] {pid}")
        print(f"     年份: {paper.year}")
        print(f"     标题: {paper.title}")
        print(f"     作者: {', '.join(paper.authors)}")
        print(f"     引用数: {paper.citation_count}")

        if i < len(chain) - 1:
            print(f"            ↓ CITES")


def main():
    print("=" * 70)
    print("杨逸飞推理链 - 10节点链模拟演示")
    print("=" * 70)
    print()
    print("说明：由于API限流，使用模拟数据展示10节点链的问题生成")
    print()

    # 生成模拟KG
    kg = generate_simulated_kg(num_papers=50, avg_citations=6)
    papers = kg["papers"]
    graph = kg["citation_graph"]

    print(f"\nKG统计:")
    print(f"  论文数: {len(papers)}")
    print(f"  引用关系数: {sum(len(c) for c in graph.values())}")
    print(f"  平均出度: {sum(len(c) for c in graph.values()) / len(graph):.1f}")

    # 找最大连通分量（用于构建长链）
    max_out_paper = max(graph.keys(), key=lambda x: len(graph.get(x, [])))
    print(f"  最高出度论文: {max_out_paper} ({len(graph[max_out_paper])}个引用)")

    # 测试不同链长度
    targets = [10, 8, 5]

    for target in targets:
        print(f"\n{'='*70}")
        print(f"尝试构建{target}节点链")
        print(f"{'='*70}")

        chain = build_chain_with_backtrack(graph, max_out_paper, target)

        if len(chain) >= target:
            print(f"\n✓ 成功构建{len(chain)}节点链!")
            print_chain_details(chain, papers)

            # 生成问题
            print(f"\n{'='*70}")
            print(f"生成复杂问题")
            print(f"{'='*70}")

            questions = generate_10node_questions(chain, papers)

            for i, q in enumerate(questions, 1):
                print(f"\n问题 {i} [{q['difficulty'].upper()}]")
                print(f"  类型: {q['type']}")
                print(f"  问题: {q['question']}")
                print(f"  答案: {q['answer']}")
                print(f"  涉及链长: {q['chain_length']}节点")

            break
        else:
            print(f"\n✗ 仅构建{len(chain)}节点链")

    # 实际部署建议
    print(f"\n{'='*70}")
    print("实际部署方案（绕过API限流）")
    print(f"{'='*70}")
    print("""
方案A: 批量下载公开数据集
- 使用 DBLP、arXiv 或 Microsoft Academic Graph (MAG)
- 预构建完整的引用网络
- 避免实时API调用

方案B: 缓存API结果
- 将API返回数据保存到本地
- 建立 SS ID -> 本地数据的映射
- 重复使用已获取的数据

方案C: 与原始KG结合
- 使用原始52篇论文作为种子
- 扩展获取它们引用的论文
- 构建200+论文的中型KG

推荐: 方案B + 方案C
1. 先预取一批论文的API数据
2. 保存到本地 cache/api_cache.json
3. 构建扩展KG时优先查缓存
""")


if __name__ == "__main__":
    main()
