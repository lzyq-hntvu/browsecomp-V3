#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 论文引用链+描述实体

思路:
1. 构建论文引用链 (Paper -> Paper -> Paper)
2. 每个论文附带描述实体 (作者、年份、机构)
3. 用描述实体推理论文，生成问题

简化版:
- 3个论文节点 (由于KG限制，实际使用2-hop链)
- 2-3个描述实体/节点
- 线性链结构
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class PaperNode:
    """论文节点，包含描述实体"""
    paper_id: str
    title: str
    publication_date: str
    connected_entities: List[Dict[str, Any]] = field(default_factory=list)

    def get_entities_by_type(self, entity_type: str) -> List[Dict]:
        """获取指定类型的实体"""
        return [e for e in self.connected_entities if e.get('type') == entity_type]

    def get_year(self) -> Optional[int]:
        """获取发表年份"""
        year_entity = self.get_entities_by_type('Year')
        if year_entity:
            return year_entity[0].get('value')
        # Fallback to date parsing
        if self.publication_date:
            try:
                return int(self.publication_date.split('-')[0])
            except (ValueError, IndexError):
                pass
        return None

    def get_authors(self, max_count: int = 3) -> List[str]:
        """获取作者名称列表"""
        authors = self.get_entities_by_type('Author')
        return [a.get('name', 'Unknown') for a in authors[:max_count]]

    def get_institutions(self) -> List[str]:
        """获取机构名称列表"""
        insts = self.get_entities_by_type('Institution')
        return [i.get('name', 'Unknown') for i in insts]


@dataclass
class PaperChain:
    """论文引用链"""
    papers: List[PaperNode]
    citations: List[tuple]  # [(from_id, to_id), ...]

    def __len__(self):
        return len(self.papers)

    def get_paper_by_id(self, paper_id: str) -> Optional[PaperNode]:
        """根据ID获取论文"""
        for p in self.papers:
            if p.paper_id == paper_id:
                return p
        return None


class PaperChainBuilder:
    """论文引用链构建器"""

    def __init__(self, test_data_path: str = "data/yang_chain_test_set.json"):
        self.test_data_path = Path(test_data_path)
        self.test_data = None
        self._load_test_data()

    def _load_test_data(self):
        """加载测试数据"""
        if not self.test_data_path.exists():
            raise FileNotFoundError(f"Test data not found: {self.test_data_path}")

        with open(self.test_data_path, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)

    def build_chain(self, start_paper_id: Optional[str] = None, length: int = 3) -> Optional[PaperChain]:
        """
        构建论文引用链

        Args:
            start_paper_id: 起始论文ID，None则随机选择
            length: 链长度（由于KG限制，实际最多2）

        Returns:
            PaperChain对象
        """
        if not self.test_data:
            return None

        papers_data = self.test_data.get('papers', [])
        citations = self.test_data.get('citation_chain', [])

        # Build paper nodes
        paper_nodes = {}
        for p_data in papers_data:
            node = PaperNode(
                paper_id=p_data['paper_id'],
                title=p_data['title'],
                publication_date=p_data.get('publication_date', ''),
                connected_entities=p_data.get('connected_entities', [])
            )
            paper_nodes[p_data['paper_id']] = node

        # Build citation mapping
        cites_map = {}  # paper_id -> [papers it cites]
        for c in citations:
            from_id = c.get('from')
            to_id = c.get('to')
            if from_id not in cites_map:
                cites_map[from_id] = []
            cites_map[from_id].append(to_id)

        # Determine start paper
        if start_paper_id is None:
            # Prefer papers that have citations
            papers_with_cites = [p for p in paper_nodes.keys() if p in cites_map]
            if papers_with_cites:
                start_paper_id = random.choice(papers_with_cites)
            else:
                start_paper_id = random.choice(list(paper_nodes.keys()))

        # Build chain
        chain_papers = []
        chain_citations = []
        current_id = start_paper_id

        chain_papers.append(paper_nodes[current_id])

        # Try to extend chain
        for _ in range(length - 1):
            if current_id in cites_map and cites_map[current_id]:
                # Select next paper from citations
                next_id = random.choice(cites_map[current_id])
                if next_id in paper_nodes:
                    chain_papers.append(paper_nodes[next_id])
                    chain_citations.append((current_id, next_id))
                    current_id = next_id
                else:
                    break
            else:
                break

        return PaperChain(papers=chain_papers, citations=chain_citations)

    def get_connected_entities(self, paper_id: str, max_count: int = 3) -> List[Dict]:
        """获取论文的描述实体"""
        papers_data = self.test_data.get('papers', [])
        for p_data in papers_data:
            if p_data['paper_id'] == paper_id:
                entities = p_data.get('connected_entities', [])
                # Prioritize: Year, Author, Institution
                prioritized = []
                for e in entities:
                    if e.get('type') == 'Year':
                        prioritized.append(e)
                for e in entities:
                    if e.get('type') == 'Author':
                        prioritized.append(e)
                for e in entities:
                    if e.get('type') == 'Institution':
                        prioritized.append(e)
                return prioritized[:max_count]
        return []


class YangChainQuestionGenerator:
    """
    杨逸飞推理链问题生成器

    三种推理模式:
    1. 前向推理 (Forward): 描述A，问A引用的B
    2. 后向推理 (Backward): 描述B，问谁引用了B
    3. 跳跃推理 (Hop): 描述A+C，问中间的B
    """

    def __init__(self, chain_builder: PaperChainBuilder):
        self.chain_builder = chain_builder

    def generate_forward_question(self, chain: PaperChain) -> Optional[Dict]:
        """
        前向推理问题
        例: "Kejun Bu于2022年发表的论文引用了哪篇关于'Atomic packing...'的论文？"
        """
        if len(chain.papers) < 2:
            return None

        paper_a = chain.papers[0]
        paper_b = chain.papers[1]

        # Get description entities for paper_a
        year = paper_a.get_year()
        authors = paper_a.get_authors(2)

        # Build question
        if authors and year:
            author_str = "、".join(authors[:2]) if len(authors) > 1 else authors[0]
            question = f"{author_str}于{year}年发表的论文《{paper_a.title[:40]}...》引用了哪篇论文？"
        elif year:
            question = f"{year}年发表的论文《{paper_a.title[:40]}...》引用了哪篇论文？"
        else:
            question = f"论文《{paper_a.title[:40]}...》引用了哪篇论文？"

        return {
            "question_type": "forward",
            "question_text": question,
            "answer": paper_b.title,
            "answer_paper_id": paper_b.paper_id,
            "reasoning_chain": f"{paper_a.paper_id} -CITES-> {paper_b.paper_id}",
            "clue_paper": paper_a.paper_id,
            "target_paper": paper_b.paper_id,
            "difficulty": "easy"
        }

    def generate_backward_question(self, chain: PaperChain) -> Optional[Dict]:
        """
        后向推理问题
        例: "哪篇2022年的论文引用了H.W. Sheng关于原子堆积的研究？"
        """
        if len(chain.papers) < 2:
            return None

        paper_a = chain.papers[0]
        paper_b = chain.papers[1]

        # Get description entities for paper_b
        year_b = paper_b.get_year()
        authors_b = paper_b.get_authors(2)

        # Build question
        if authors_b and year_b:
            author_str = "、".join(authors_b[:2]) if len(authors_b) > 1 else authors_b[0]
            question = f"哪篇{year_b}年发表的论文引用了{author_str}的《{paper_b.title[:40]}...》？"
        elif authors_b:
            author_str = "、".join(authors_b[:2]) if len(authors_b) > 1 else authors_b[0]
            question = f"哪篇论文引用了{author_str}的《{paper_b.title[:40]}...》？"
        elif year_b:
            question = f"哪篇{year_b}年发表的论文引用了《{paper_b.title[:40]}...》？"
        else:
            question = f"哪篇论文引用了《{paper_b.title[:40]}...》？"

        return {
            "question_type": "backward",
            "question_text": question,
            "answer": paper_a.title,
            "answer_paper_id": paper_a.paper_id,
            "reasoning_chain": f"{paper_a.paper_id} -CITES-> {paper_b.paper_id}",
            "clue_paper": paper_b.paper_id,
            "target_paper": paper_a.paper_id,
            "difficulty": "medium"
        }

    def generate_hop_question(self, chain: PaperChain) -> Optional[Dict]:
        """
        跳跃推理问题 (需要3个论文)
        例: "Kejun Bu的论文引用了H.W. Sheng的论文，后者引用了哪篇论文？"
        """
        if len(chain.papers) < 3:
            # Fall back to 2-paper variant
            return self._generate_two_paper_hop(chain)

        paper_a = chain.papers[0]
        paper_b = chain.papers[1]
        paper_c = chain.papers[2]

        # Get key entities
        authors_a = paper_a.get_authors(1)
        authors_b = paper_b.get_authors(1)

        if authors_a and authors_b:
            question = f"{authors_a[0]}的论文引用了{authors_b[0]}的《{paper_b.title[:30]}...》，"
            question += f"后者又引用了哪篇论文？"
        else:
            question = f"论文《{paper_a.title[:30]}...》引用链中的中间论文引用了哪篇论文？"

        return {
            "question_type": "hop",
            "question_text": question,
            "answer": paper_c.title,
            "answer_paper_id": paper_c.paper_id,
            "reasoning_chain": f"{paper_a.paper_id} -CITES-> {paper_b.paper_id} -CITES-> {paper_c.paper_id}",
            "difficulty": "hard"
        }

    def _generate_two_paper_hop(self, chain: PaperChain) -> Optional[Dict]:
        """两论文跳跃问题变体"""
        if len(chain.papers) < 2:
            return None

        paper_a = chain.papers[0]
        paper_b = chain.papers[1]

        year_a = paper_a.get_year()
        authors_b = paper_b.get_authors(1)
        inst_b = paper_b.get_institutions()

        # Combine year from A with entities from B
        clues = []
        if year_a:
            clues.append(f"发表于{year_a}年")
        if authors_b:
            clues.append(f"引用了{authors_b[0]}的论文")
        if inst_b:
            clues.append(f"该作者来自{inst_b[0]}")

        if len(clues) >= 2:
            question = f"哪篇{'且'.join(clues[:2])}？"
        elif clues:
            question = f"哪篇{clues[0]}？"
        else:
            question = f"哪篇论文引用了《{paper_b.title[:40]}...》？"

        return {
            "question_type": "hop_2paper",
            "question_text": question,
            "answer": paper_a.title,
            "answer_paper_id": paper_a.paper_id,
            "reasoning_chain": f"{paper_a.paper_id} -CITES-> {paper_b.paper_id}",
            "difficulty": "medium"
        }

    def generate_comparison_question(self, chain: PaperChain) -> Optional[Dict]:
        """
        比较推理问题
        例: "Kejun Bu 2022年的论文和H.W. Sheng的论文有什么引用关系？"
        """
        if len(chain.papers) < 2:
            return None

        paper_a = chain.papers[0]
        paper_b = chain.papers[1]

        year_a = paper_a.get_year()
        authors_a = paper_a.get_authors(1)
        authors_b = paper_b.get_authors(1)

        entity_parts = []
        if authors_a and year_a:
            entity_parts.append(f"{authors_a[0]}于{year_a}年发表的论文")
        elif authors_a:
            entity_parts.append(f"{authors_a[0]}的论文")

        if authors_b:
            entity_parts.append(f"{authors_b[0]}的论文《{paper_b.title[:30]}...》")

        if len(entity_parts) >= 2:
            question = f"{entity_parts[0]}与{entity_parts[1]}之间有什么引用关系？"
        else:
            question = f"论文《{paper_a.title[:30]}...》与《{paper_b.title[:30]}...》之间有什么引用关系？"

        return {
            "question_type": "comparison",
            "question_text": question,
            "answer": f"《{paper_a.title}》引用了《{paper_b.title}》",
            "answer_paper_id": f"{paper_a.paper_id}->{paper_b.paper_id}",
            "reasoning_chain": f"{paper_a.paper_id} -CITES-> {paper_b.paper_id}",
            "difficulty": "medium"
        }


def export_markdown(questions: List[Dict], output_path: Path, chain_info: Dict = None):
    """导出为Markdown文档"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 杨逸飞推理链Demo - 测试结果\n\n")
        f.write("## 实验概述\n\n")
        f.write("本实验测试基于论文引用链+描述实体的问题生成方法。\n\n")

        if chain_info:
            f.write(f"**测试链**: {chain_info.get('description', 'N/A')}\n\n")
            f.write(f"**论文数量**: {chain_info.get('paper_count', 'N/A')}\n\n")

        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**问题数量**: {len(questions)}\n\n")

        # Summary table
        f.write("## 问题概览\n\n")
        f.write("| # | 类型 | 难度 | 问题 | 答案 |\n")
        f.write("|---|------|------|------|------|\n")
        for i, q in enumerate(questions, 1):
            q_type = q.get('question_type', 'unknown')
            difficulty = q.get('difficulty', 'unknown')
            question_text = q.get('question_text', '')[:50] + "..."
            answer = q.get('answer', '')[:30] + "..."
            f.write(f"| {i} | {q_type} | {difficulty} | {question_text} | {answer} |\n")

        f.write("\n---\n\n")

        # Detailed questions
        for i, q in enumerate(questions, 1):
            f.write(f"## 问题 {i}\n\n")
            f.write(f"**ID**: Q_{i:03d}\n\n")
            f.write(f"**类型**: {q.get('question_type', 'unknown')}\n\n")
            f.write(f"**难度**: {q.get('difficulty', 'unknown')}\n\n")
            f.write(f"**问题**: {q.get('question_text', '')}\n\n")
            f.write(f"**答案**: {q.get('answer', '')}\n\n")
            f.write(f"**推理链**: `{q.get('reasoning_chain', '')}`\n\n")
            f.write("---\n\n")


def main():
    print("=" * 70)
    print("杨逸飞推理链Demo - 论文引用链+描述实体")
    print("=" * 70)
    print()

    # Step 1: Initialize builder
    print("[1/5] 初始化PaperChainBuilder...")
    try:
        builder = PaperChainBuilder()
        print("      ✓ 测试数据加载成功")
    except FileNotFoundError as e:
        print(f"      ✗ 错误: {e}")
        return

    # Step 2: Build chain
    print("[2/5] 构建论文引用链...")
    chain = builder.build_chain(length=3)
    if not chain or len(chain.papers) < 2:
        print("      ✗ 无法构建足够长的引用链")
        return

    print(f"      ✓ 构建成功，包含 {len(chain.papers)} 篇论文")
    for i, p in enumerate(chain.papers, 1):
        year = p.get_year()
        authors = p.get_authors(2)
        print(f"         [{i}] {p.paper_id}: {p.title[:50]}...")
        print(f"             年份: {year}, 作者: {', '.join(authors) if authors else 'N/A'}")

    # Step 3: Initialize generator
    print("[3/5] 初始化问题生成器...")
    generator = YangChainQuestionGenerator(builder)
    print("      ✓ 生成器就绪")

    # Step 4: Generate questions
    print("[4/5] 生成测试问题...")
    questions = []

    # Try different question types
    q_forward = generator.generate_forward_question(chain)
    if q_forward:
        questions.append(q_forward)
        print("      ✓ 前向推理问题")

    q_backward = generator.generate_backward_question(chain)
    if q_backward:
        questions.append(q_backward)
        print("      ✓ 后向推理问题")

    q_hop = generator.generate_hop_question(chain)
    if q_hop:
        questions.append(q_hop)
        print("      ✓ 跳跃推理问题")

    q_compare = generator.generate_comparison_question(chain)
    if q_compare:
        questions.append(q_compare)
        print("      ✓ 比较推理问题")

    # Generate more chains for variety
    print("      生成更多链以获得多样性...")
    for _ in range(3):
        chain2 = builder.build_chain(length=3)
        if chain2 and len(chain2.papers) >= 2:
            q = generator.generate_forward_question(chain2)
            if q:
                questions.append(q)

    print(f"      ✓ 共生成 {len(questions)} 个问题")

    # Step 5: Export
    print("[5/5] 导出结果...")
    output_dir = Path("output/yang_chain_demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export markdown
    md_path = output_dir / f"yang_chain_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    chain_info = {
        "description": " -> ".join([p.paper_id for p in chain.papers]),
        "paper_count": len(chain.papers)
    }
    export_markdown(questions, md_path, chain_info)
    print(f"      ✓ Markdown: {md_path}")

    # Export JSON
    json_path = output_dir / f"yang_chain_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "experiment": "yang_yifei_chain",
                "generated_at": datetime.now().isoformat(),
                "question_count": len(questions),
                "chain_info": chain_info
            },
            "questions": questions
        }, f, indent=2, ensure_ascii=False)
    print(f"      ✓ JSON: {json_path}")

    print()
    print("=" * 70)
    print("生成完成!")
    print(f"输出目录: {output_dir}")
    print("=" * 70)

    # Print sample questions
    print("\n示例问题:")
    for i, q in enumerate(questions[:3], 1):
        print(f"\n{i}. [{q.get('question_type', 'unknown').upper()}]")
        print(f"   Q: {q.get('question_text', '')}")
        print(f"   A: {q.get('answer', '')}")


if __name__ == "__main__":
    main()
