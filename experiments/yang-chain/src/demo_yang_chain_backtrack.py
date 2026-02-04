#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 回溯回退机制

核心思想:
- 当当前路径走不通时，回退到上一个节点选择其他分支
- 使用DFS（深度优先搜索）+ 回溯
- 记录访问过的节点避免循环

类比：走迷宫时遇到死路，回到上一个路口选其他方向
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BacktrackNode:
    """回溯节点记录"""
    paper_id: str
    available_choices: List[str]  # 可选择的下一个节点
    chosen_index: int  # 当前选择的索引


class BacktrackChainBuilder:
    """
    回溯式链构建器

    算法：
    1. 从起始节点开始
    2. 记录当前节点的所有可选分支
    3. 选择一个分支继续前进
    4. 如果走到死路（无可用分支），回退到上一个节点选择其他分支
    5. 重复直到达到目标长度或所有可能都尝试完毕
    """

    def __init__(self, kg_path: str = "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"):
        self.kg_path = Path(kg_path)
        self.kg = None
        self.papers = {}
        self.citation_graph = {}  # paper -> [cited_papers]
        self._load_kg()

        # 统计
        self.backtrack_count = 0
        self.max_depth_reached = 0

    def _load_kg(self):
        """加载知识图谱"""
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            self.kg = json.load(f)

        for node in self.kg['nodes']:
            if node['type'] == 'paper':
                self.papers[node['id']] = node

        for edge in self.kg['edges']:
            if edge['relation_type'] == 'CITES':
                src = edge['source_id']
                tgt = edge['target_id']
                if src not in self.citation_graph:
                    self.citation_graph[src] = []
                if tgt not in self.citation_graph[src]:
                    self.citation_graph[src].append(tgt)

    def build_chain_with_backtrack(
        self,
        start_paper: Optional[str] = None,
        target_length: int = 10,
        max_backtracks: int = 100
    ) -> Tuple[List[str], int, str]:
        """
        使用回溯算法构建链

        Args:
            start_paper: 起始论文，None则随机选择
            target_length: 目标链长度
            max_backtracks: 最大回退次数（防止无限循环）

        Returns:
            (链, 回退次数, 状态说明)
        """
        if start_paper is None:
            # 选择引用较多的论文作为起点
            papers_with_citations = [
                p for p in self.papers
                if p in self.citation_graph and len(self.citation_graph[p]) >= 2
            ]
            if papers_with_citations:
                start_paper = random.choice(papers_with_citations)
            else:
                start_paper = random.choice(list(self.papers.keys()))

        print(f"   起始: {start_paper}")
        print(f"   目标链长: {target_length}")

        # 回溯栈：记录每个节点的选择状态
        stack: List[BacktrackNode] = []
        visited: Set[str] = {start_paper}
        current_chain = [start_paper]
        backtrack_count = 0

        while len(current_chain) < target_length:
            current_paper = current_chain[-1]

            # 获取当前论文的可引用论文
            candidates = self.citation_graph.get(current_paper, [])
            # 过滤已访问的
            available = [p for p in candidates
                        if p not in visited and p in self.papers]

            if not available:
                # 死路！需要回退
                if len(stack) == 0:
                    # 已经回退到起点，无法继续
                    return current_chain, backtrack_count, "死路：无法达到目标长度"

                if backtrack_count >= max_backtracks:
                    return current_chain, backtrack_count, f"达到最大回退次数({max_backtracks})"

                # 回退一步
                stack.pop()
                visited.remove(current_chain[-1])
                current_chain.pop()
                backtrack_count += 1

                if backtrack_count <= 5:  # 只打印前几次回退
                    print(f"   ↩  回退到第{len(current_chain)}节点 (累计回退{backtrack_count}次)")
                elif backtrack_count == 6:
                    print(f"   ... (省略后续回退日志)")

                continue

            # 有可用选择，记录当前节点的状态
            if len(stack) < len(current_chain):
                # 新节点，创建回溯记录
                node = BacktrackNode(
                    paper_id=current_paper,
                    available_choices=available.copy(),
                    chosen_index=0
                )
                stack.append(node)
            else:
                # 已经访问过，从下一个选择继续
                node = stack[-1]
                node.chosen_index += 1

                if node.chosen_index >= len(node.available_choices):
                    # 所有选择都试过，需要回退
                    stack.pop()
                    visited.remove(current_chain[-1])
                    current_chain.pop()
                    backtrack_count += 1
                    continue

            # 选择下一个节点
            node = stack[-1]
            next_paper = node.available_choices[node.chosen_index]

            current_chain.append(next_paper)
            visited.add(next_paper)

            if len(current_chain) > self.max_depth_reached:
                self.max_depth_reached = len(current_chain)

        status = f"成功构建{len(current_chain)}节点链，回退{backtrack_count}次"
        return current_chain, backtrack_count, status

    def find_longest_chain_dfs(self, start_paper: Optional[str] = None) -> List[str]:
        """
        使用DFS找出从某篇论文出发的最长链（不重复节点）
        """
        if start_paper is None:
            start_paper = random.choice(list(self.papers.keys()))

        longest = []

        def dfs(current: str, visited: Set[str], path: List[str]):
            nonlocal longest
            if len(path) > len(longest):
                longest = path.copy()

            candidates = self.citation_graph.get(current, [])
            for next_paper in candidates:
                if next_paper not in visited and next_paper in self.papers:
                    visited.add(next_paper)
                    path.append(next_paper)
                    dfs(next_paper, visited, path)
                    path.pop()
                    visited.remove(next_paper)

        dfs(start_paper, {start_paper}, [start_paper])
        return longest

    def analyze_kg_connectivity(self) -> Dict:
        """分析KG的连接性，找出潜在的链"""
        print("\n分析KG连接性...")

        # 统计每个论文的出度（引用数）
        out_degrees = {p: len(c) for p, c in self.citation_graph.items()}

        # 统计每个论文的入度（被引用数）
        in_degrees = {p: 0 for p in self.papers}
        for cites in self.citation_graph.values():
            for cited in cites:
                if cited in in_degrees:
                    in_degrees[cited] += 1

        # 找出入度=0的论文（起点候选）
        zero_in_degree = [p for p, d in in_degrees.items() if d == 0]

        # 找出度=0的论文（终点候选）
        zero_out_degree = [p for p in self.papers if p not in self.citation_graph]

        print(f"  起点候选（无被引用）: {len(zero_in_degree)}篇")
        print(f"  终点候选（无引用）: {len(zero_out_degree)}篇")
        print(f"  高引用论文（>5引用）: {sum(1 for d in out_degrees.values() if d > 5)}篇")

        # 尝试找几条长链
        print("\n  尝试找长链...")
        chain_lengths = []

        # 从paper_1开始（已知引用较多）
        if 'paper_1' in self.papers:
            chain = self.find_longest_chain_dfs('paper_1')
            chain_lengths.append(('paper_1', len(chain)))
            print(f"    从paper_1: 最长链{len(chain)}节点")

        # 随机选几个起点
        for _ in range(5):
            start = random.choice(list(self.papers.keys()))
            chain = self.find_longest_chain_dfs(start)
            chain_lengths.append((start, len(chain)))

        chain_lengths.sort(key=lambda x: x[1], reverse=True)
        print(f"\n  最长链统计（Top 5）:")
        for start, length in chain_lengths[:5]:
            print(f"    {start}: {length}节点")

        return {
            "zero_in_degree": len(zero_in_degree),
            "zero_out_degree": len(zero_out_degree),
            "max_chain_length": max(chain_lengths, key=lambda x: x[1])[1] if chain_lengths else 0
        }


def test_backtrack():
    """测试回溯机制"""
    print("=" * 70)
    print("回溯回退机制测试")
    print("=" * 70)
    print()

    builder = BacktrackChainBuilder()

    # 先分析KG
    stats = builder.analyze_kg_connectivity()
    print()

    # 测试不同目标长度
    test_lengths = [10, 8, 5, 3]

    for target in test_lengths:
        print(f"\n目标: {target}节点链")
        print("-" * 50)

        # 尝试3次
        for i in range(3):
            chain, backtracks, status = builder.build_chain_with_backtrack(
                target_length=target,
                max_backtracks=50
            )
            print(f"  尝试{i+1}: 链长={len(chain)}, 回退={backtracks}次, 状态={status}")

            if len(chain) >= target:
                print(f"    ✓ 成功!")
                break

    # 演示详细回溯过程
    print("\n" + "=" * 70)
    print("详细回溯过程演示")
    print("=" * 70)

    chain, backtracks, status = builder.build_chain_with_backtrack(
        start_paper='paper_1',
        target_length=5,
        max_backtracks=20
    )

    print(f"\n最终链 ({len(chain)}节点):")
    for i, paper_id in enumerate(chain):
        paper = builder.papers.get(paper_id, {})
        year = paper.get('publication_date', '')[:4]
        print(f"  [{i+1}] {paper_id}: [{year}] {paper.get('title', 'Unknown')[:40]}...")


if __name__ == "__main__":
    test_backtrack()
