#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 带回退机制的长链生成器

回退策略:
1. 10节点链 -> 8节点 -> 5节点 -> 3节点
2. 严格约束 -> 宽松约束
3. 链式推理 -> V3模板
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class FallbackLevel(Enum):
    """回退级别"""
    LEVEL_10 = "10_nodes"      # 目标：10节点链
    LEVEL_8 = "8_nodes"        # 回退1：8节点
    LEVEL_5 = "5_nodes"        # 回退2：5节点
    LEVEL_3 = "3_nodes"        # 回退3：3节点
    V3_TEMPLATE = "v3"         # 最终回退：V3模板


@dataclass
class ChainAttempt:
    """链构建尝试记录"""
    level: FallbackLevel
    target_length: int
    success: bool
    chain: Optional[List[str]]
    reason: str  # 失败原因或成功说明
    execution_time_ms: float


class FallbackChainBuilder:
    """
    带回退机制的链构建器

    策略:
    1. 尝试构建10节点链
    2. 失败则降低为8节点
    3. 继续失败则5节点
    4. 最终回退到V3模板
    """

    def __init__(self, kg_path: str = "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"):
        self.kg_path = Path(kg_path)
        self.kg = None
        self.papers = {}
        self.citation_graph = {}  # paper -> [cited_papers]
        self._load_kg()

        # 回退配置
        self.fallback_levels = [
            (FallbackLevel.LEVEL_10, 10),
            (FallbackLevel.LEVEL_8, 8),
            (FallbackLevel.LEVEL_5, 5),
            (FallbackLevel.LEVEL_3, 3),
        ]

        # 统计信息
        self.attempt_history: List[ChainAttempt] = []

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
                self.citation_graph[src].append(tgt)

    def _build_chain_attempt(self, start_paper: str, target_length: int,
                            strict_mode: bool = True) -> Tuple[bool, Optional[List[str]], str]:
        """
        单次链构建尝试

        Args:
            start_paper: 起始论文ID
            target_length: 目标链长度
            strict_mode: 严格模式（True=要求精确长度，False=允许短链）

        Returns:
            (成功, 链, 原因)
        """
        import time
        start_time = time.time()

        chain = [start_paper]
        current = start_paper
        visited = {start_paper}

        while len(chain) < target_length:
            # 获取当前论文引用的论文
            candidates = self.citation_graph.get(current, [])

            # 过滤已访问的（避免循环）
            available = [p for p in candidates if p not in visited and p in self.papers]

            if not available:
                # 尝试找其他未访问的论文
                all_papers = set(self.papers.keys())
                unvisited = list(all_papers - visited)
                if unvisited and not strict_mode:
                    # 宽松模式：允许不严格的引用关系
                    available = unvisited[:5]  # 随机选几个
                else:
                    elapsed = (time.time() - start_time) * 1000
                    if len(chain) >= target_length // 2:
                        # 至少完成一半，视为部分成功
                        return True, chain, f"部分链：仅找到{len(chain)}个节点"
                    return False, None, f"链断裂于第{len(chain)}个节点，无可用的引用"

            # 选择下一个节点（策略：随机选择以保持多样性）
            next_paper = random.choice(available)
            chain.append(next_paper)
            visited.add(next_paper)
            current = next_paper

        elapsed = (time.time() - start_time) * 1000
        return True, chain, f"成功构建{len(chain)}节点链"

    def build_chain_with_fallback(self, start_paper: Optional[str] = None) -> Tuple[FallbackLevel, List[str], List[ChainAttempt]]:
        """
        带回退的链构建主方法

        Returns:
            (最终级别, 链, 尝试历史)
        """
        self.attempt_history = []

        # 选择起始论文
        if start_paper is None:
            # 优先选择引用较多的论文
            papers_with_citations = [p for p in self.papers if p in self.citation_graph]
            if papers_with_citations:
                start_paper = random.choice(papers_with_citations)
            else:
                start_paper = random.choice(list(self.papers.keys()))

        print(f"   起始论文: {start_paper}")

        # 逐级尝试
        for level, target_length in self.fallback_levels:
            print(f"   尝试 [{level.value}]: 目标{target_length}节点...", end=" ")

            success, chain, reason = self._build_chain_attempt(
                start_paper, target_length,
                strict_mode=(level != FallbackLevel.LEVEL_3)
            )

            import time
            attempt = ChainAttempt(
                level=level,
                target_length=target_length,
                success=success,
                chain=chain,
                reason=reason,
                execution_time_ms=0.1  # 简化
            )
            self.attempt_history.append(attempt)

            if success and chain:
                print(f"✓ {reason}")
                return level, chain, self.attempt_history
            else:
                print(f"✗ {reason}")

        # 全部失败，返回V3回退
        print(f"   回退到V3模板")
        return FallbackLevel.V3_TEMPLATE, [start_paper], self.attempt_history

    def generate_complex_question_with_fallback(self, chain: List[str]) -> Optional[Dict]:
        """
        基于链长度生成相应复杂度的问题
        """
        if len(chain) < 2:
            return None

        # 根据链长度选择问题复杂度
        if len(chain) >= 8:
            return self._generate_expert_question(chain)
        elif len(chain) >= 5:
            return self._generate_hard_question(chain)
        elif len(chain) >= 3:
            return self._generate_medium_question(chain)
        else:
            return self._generate_simple_question(chain)

    def _generate_expert_question(self, chain: List[str]) -> Dict:
        """专家级问题：长链+多约束"""
        # 使用链的两端和中间点
        paper_a = self.papers.get(chain[0], {})
        paper_mid = self.papers.get(chain[len(chain)//2], {})
        paper_z = self.papers.get(chain[-1], {})

        # 获取年份
        year_a = self._get_year(chain[0])
        year_z = self._get_year(chain[-1])

        question = f"从{year_a}年发表的《{paper_a.get('title', 'Unknown')[:30]}...》出发，"
        question += f"经过一系列引用关系，最终到达{year_z}年的研究。"
        question += f"引用链中间的论文《{paper_mid.get('title', 'Unknown')[:30]}...》"
        question += f"引用了链末端论文的哪个核心概念？"

        return {
            "type": "expert_long_chain",
            "question": question,
            "answer": paper_z.get('title', 'Unknown'),
            "chain_length": len(chain),
            "chain": " -> ".join(chain),
            "difficulty": "expert"
        }

    def _generate_hard_question(self, chain: List[str]) -> Dict:
        """困难问题：中等长度链"""
        paper_a = self.papers.get(chain[0], {})
        paper_b = self.papers.get(chain[-1], {})
        year_a = self._get_year(chain[0])

        question = f"{year_a}年发表的论文《{paper_a.get('title', 'Unknown')[:40]}...》"
        question += f"通过{len(chain)-1}层引用关系，最终引用了哪篇关于"
        question += f"'{paper_b.get('title', 'Unknown').split()[-3:]}'的研究？"

        return {
            "type": "hard_multi_hop",
            "question": question,
            "answer": paper_b.get('title', 'Unknown'),
            "chain_length": len(chain),
            "chain": " -> ".join(chain),
            "difficulty": "hard"
        }

    def _generate_medium_question(self, chain: List[str]) -> Dict:
        """中等问题"""
        paper_a = self.papers.get(chain[0], {})
        paper_c = self.papers.get(chain[-1], {})

        question = f"论文《{paper_a.get('title', 'Unknown')[:30]}...》"
        question += f"引用了哪篇关于'{paper_c.get('title', 'Unknown')[:20]}...'的论文？"

        return {
            "type": "medium_chain",
            "question": question,
            "answer": paper_c.get('title', 'Unknown'),
            "chain_length": len(chain),
            "difficulty": "medium"
        }

    def _generate_simple_question(self, chain: List[str]) -> Dict:
        """简单问题"""
        paper_a = self.papers.get(chain[0], {})
        paper_b = self.papers.get(chain[-1], {}) if len(chain) > 1 else paper_a

        question = f"《{paper_a.get('title', 'Unknown')[:30]}...》引用了哪篇论文？"

        return {
            "type": "simple",
            "question": question,
            "answer": paper_b.get('title', 'Unknown'),
            "chain_length": len(chain),
            "difficulty": "easy"
        }

    def _get_year(self, paper_id: str) -> str:
        """获取论文年份"""
        paper = self.papers.get(paper_id, {})
        date = paper.get('publication_date', '')
        if date:
            return date.split('-')[0]
        return "未知年份"


def test_fallback_mechanism():
    """测试回退机制"""
    print("=" * 70)
    print("回退机制测试")
    print("=" * 70)
    print()

    builder = FallbackChainBuilder()

    print(f"知识图谱统计:")
    print(f"  论文数: {len(builder.papers)}")
    print(f"  有引用的论文: {len(builder.citation_graph)}")
    print(f"  平均引用数: {sum(len(c) for c in builder.citation_graph.values()) / len(builder.citation_graph):.1f}" if builder.citation_graph else "  无引用数据")
    print()

    # 测试多次构建
    results = {
        FallbackLevel.LEVEL_10: 0,
        FallbackLevel.LEVEL_8: 0,
        FallbackLevel.LEVEL_5: 0,
        FallbackLevel.LEVEL_3: 0,
        FallbackLevel.V3_TEMPLATE: 0,
    }

    test_count = 10
    all_chains = []

    for i in range(test_count):
        print(f"测试 {i+1}/{test_count}:")
        level, chain, history = builder.build_chain_with_fallback()
        results[level] += 1
        all_chains.append((level, chain))
        print(f"   最终结果: {level.value} (链长: {len(chain)})")
        print()

    # 统计报告
    print("=" * 70)
    print("回退统计报告")
    print("=" * 70)
    for level, count in results.items():
        percentage = count / test_count * 100
        print(f"  {level.value:15s}: {count:2d}/{test_count} ({percentage:5.1f}%)")

    # 生成问题示例
    print()
    print("=" * 70)
    print("生成问题示例")
    print("=" * 70)

    for level, chain in all_chains[:5]:
        question = builder.generate_complex_question_with_fallback(chain)
        if question:
            print(f"\n[{question['difficulty'].upper()}] {level.value}")
            print(f"  链长: {len(chain)}")
            print(f"  问题: {question['question'][:80]}...")
            print(f"  答案: {question['answer'][:50]}...")


if __name__ == "__main__":
    test_fallback_mechanism()
