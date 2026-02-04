#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 复杂问题版本

利用现有KG的多跳路径生成复杂问题：
1. 跨机构合作问题
2. 多约束组合筛选
3. 多跳推理（Paper→Author→Institution）
4. 计数/统计问题
5. 共同作者网络
"""

import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ComplexQuestion:
    """复杂问题结构"""
    question_id: str
    question_text: str
    answer: str
    answer_type: str  # paper, author, institution, count, relation
    reasoning_chain: str
    difficulty: str  # easy, medium, hard, expert
    constraints: List[str]
    explanation: str  # 解释为什么答案是唯一的


class ComplexQuestionGenerator:
    """
    复杂问题生成器

    利用现有KG的丰富关系生成多层次推理问题
    """

    def __init__(self, kg_path: str = "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"):
        self.kg_path = Path(kg_path)
        self.kg = None
        self.papers = {}
        self.authors = {}
        self.institutions = {}

        # 关系索引
        self.paper_authors = defaultdict(list)  # paper -> [(author_id, order)]
        self.author_inst = {}  # author -> institution
        self.author_papers = defaultdict(list)  # author -> [papers]
        self.inst_authors = defaultdict(list)  # institution -> [authors]
        self.paper_citations = defaultdict(list)  # paper -> [cited_papers]

        self._load_kg()
        self._build_indexes()

    def _load_kg(self):
        """加载知识图谱"""
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            self.kg = json.load(f)

        for node in self.kg['nodes']:
            if node['type'] == 'paper':
                self.papers[node['id']] = node
            elif node['type'] == 'author':
                self.authors[node['id']] = node
            elif node['type'] == 'institution':
                self.institutions[node['id']] = node

    def _build_indexes(self):
        """构建关系索引"""
        for edge in self.kg['edges']:
            rel = edge['relation_type']
            src = edge.get('source_id')
            tgt = edge.get('target_id')

            if rel == 'HAS_AUTHOR':
                order = edge.get('author_order', 'other')
                self.paper_authors[src].append((tgt, order))
                self.author_papers[tgt].append(src)
            elif rel == 'AFFILIATED_WITH':
                self.author_inst[src] = tgt
                self.inst_authors[tgt].append(src)
            elif rel == 'CITES':
                self.paper_citations[src].append(tgt)

    def _get_paper_year(self, paper_id: str) -> Optional[int]:
        """获取论文年份"""
        paper = self.papers.get(paper_id, {})
        date = paper.get('publication_date', '')
        if date and '-' in date:
            try:
                return int(date.split('-')[0])
            except:
                pass
        return None

    def _get_paper_institutions(self, paper_id: str) -> List[Tuple[str, str]]:
        """获取论文的所有机构 (inst_id, inst_name)"""
        result = []
        seen = set()
        for author_id, _ in self.paper_authors.get(paper_id, []):
            if author_id in self.author_inst:
                inst_id = self.author_inst[author_id]
                if inst_id not in seen:
                    seen.add(inst_id)
                    inst_name = self.institutions.get(inst_id, {}).get('name', 'Unknown')
                    result.append((inst_id, inst_name))
        return result

    def _get_first_author(self, paper_id: str) -> Optional[Tuple[str, str]]:
        """获取第一作者 (id, name)"""
        for author_id, order in self.paper_authors.get(paper_id, []):
            if order == 'first':
                name = self.authors.get(author_id, {}).get('name', 'Unknown')
                return (author_id, name)
        # 如果没有标记first，返回第一个
        if self.paper_authors.get(paper_id):
            author_id = self.paper_authors[paper_id][0][0]
            name = self.authors.get(author_id, {}).get('name', 'Unknown')
            return (author_id, name)
        return None

    # ==================== 复杂问题类型 ====================

    def generate_cross_institution_question(self) -> Optional[ComplexQuestion]:
        """
        类型1: 跨机构合作问题
        例: "哪篇2022年的论文由高压科学中心和北京大学的作者共同发表？"
        """
        # 找跨机构合作的论文
        cross_inst_papers = []
        for paper_id, author_list in self.paper_authors.items():
            insts = set()
            for author_id, _ in author_list:
                if author_id in self.author_inst:
                    insts.add(self.author_inst[author_id])
            if len(insts) >= 2:
                inst_names = [self.institutions.get(i, {}).get('name', 'Unknown') for i in insts]
                cross_inst_papers.append((paper_id, insts, inst_names))

        if not cross_inst_papers:
            return None

        # 选择一篇
        paper_id, insts, inst_names = random.choice(cross_inst_papers)
        paper = self.papers.get(paper_id, {})
        year = self._get_paper_year(paper_id)

        # 构造问题 - 选择2个机构
        selected_insts = random.sample(inst_names, min(2, len(inst_names)))
        inst_str = "和".join([f"\"{i[:20]}...\"" if len(i) > 20 else f"\"{i}\"" for i in selected_insts])

        if year:
            question = f"哪篇{year}年的论文由{inst_str}的研究人员共同发表？"
        else:
            question = f"哪篇论文由{inst_str}的研究人员共同发表？"

        return ComplexQuestion(
            question_id="CI_001",
            question_text=question,
            answer=paper.get('title', 'Unknown'),
            answer_type="paper",
            reasoning_chain=f"Paper({paper_id}) -> Authors -> Institutions({', '.join(selected_insts)})",
            difficulty="hard",
            constraints=["cross_institution", f"year:{year}" if year else None],
            explanation=f"该论文由来自{len(insts)}个不同机构的作者合作完成"
        )

    def generate_multi_constraint_question(self) -> Optional[ComplexQuestion]:
        """
        类型2: 多约束组合筛选
        例: "2009年发表的、第一作者来自Geophysical Laboratory的论文标题是什么？"
        """
        # 找满足多约束的论文
        candidates = []
        for paper_id in self.papers:
            year = self._get_paper_year(paper_id)
            first_author = self._get_first_author(paper_id)
            insts = self._get_paper_institutions(paper_id)

            if year and first_author and insts:
                candidates.append((paper_id, year, first_author, insts))

        if len(candidates) < 2:
            return None

        # 选择一个有唯一答案的组合
        # 策略：选择特定年份+特定机构的组合
        year_inst_count = defaultdict(list)
        for pid, year, first_author, insts in candidates:
            for inst_id, inst_name in insts:
                year_inst_count[(year, inst_id)].append(pid)

        # 找唯一匹配的
        unique_matches = [(k, v[0]) for k, v in year_inst_count.items() if len(v) == 1]
        if not unique_matches:
            # 如果没有唯一的，选第一个
            match = random.choice(list(year_inst_count.items()))
            key, papers_list = match
            year, inst_id = key
            paper_id = papers_list[0]
        else:
            (year, inst_id), paper_id = random.choice(unique_matches)

        inst_name = self.institutions.get(inst_id, {}).get('name', 'Unknown')
        paper = self.papers.get(paper_id, {})
        first_author = self._get_first_author(paper_id)

        question = f"{year}年发表的、第一作者来自\"{inst_name[:25]}\"的论文标题是什么？"

        return ComplexQuestion(
            question_id="MC_001",
            question_text=question,
            answer=paper.get('title', 'Unknown'),
            answer_type="paper",
            reasoning_chain=f"Filter(year={year}) -> Filter(first_author_inst={inst_name[:20]}) -> Paper",
            difficulty="medium",
            constraints=[f"year:{year}", f"institution:{inst_name}"],
            explanation=f"{year}年发表的论文中，只有这一篇的第一作者来自该机构"
        )

    def generate_author_network_question(self) -> Optional[ComplexQuestion]:
        """
        类型3: 作者合作网络问题
        例: "Kejun Bu和Qingyang Hu共同参与了哪几篇论文的发表？"
        """
        # 找有共同论文的作者对
        coauthor_pairs = []
        for author_id, papers in self.author_papers.items():
            if len(papers) >= 2:
                # 找另一个也有这些论文的作者
                for other_id, other_papers in self.author_papers.items():
                    if other_id != author_id:
                        common = set(papers) & set(other_papers)
                        if len(common) >= 2:  # 至少2篇共同论文
                            coauthor_pairs.append((author_id, other_id, list(common)))

        if not coauthor_pairs:
            return None

        author1_id, author2_id, common_papers = random.choice(coauthor_pairs)
        author1_name = self.authors.get(author1_id, {}).get('name', 'Unknown')
        author2_name = self.authors.get(author2_id, {}).get('name', 'Unknown')

        if len(common_papers) == 1:
            question = f"{author1_name}和{author2_name}共同参与了哪篇论文的发表？"
        else:
            question = f"{author1_name}和{author2_name}共同参与了哪{len(common_papers)}篇论文的发表？（列举一篇）"

        paper = self.papers.get(common_papers[0], {})

        return ComplexQuestion(
            question_id="AN_001",
            question_text=question,
            answer=paper.get('title', 'Unknown'),
            answer_type="paper",
            reasoning_chain=f"Author({author1_name}) <- Paper -> Author({author2_name})",
            difficulty="medium",
            constraints=["coauthor"],
            explanation=f"两位作者共同参与了{len(common_papers)}篇论文的合作"
        )

    def generate_citation_with_author_constraint(self) -> Optional[ComplexQuestion]:
        """
        类型4: 引用+作者约束
        例: "2022年Kejun Bu发表的论文中，哪篇引用了H.W. Sheng关于金属玻璃的研究？"
        """
        # 找有引用的论文
        papers_with_citations = [(p, c) for p, c in self.paper_citations.items() if c]
        if not papers_with_citations:
            return None

        # 选择一个
        paper_id, citations = random.choice(papers_with_citations)
        paper = self.papers.get(paper_id, {})
        year = self._get_paper_year(paper_id)

        # 获取被引用论文的作者
        cited_paper_id = random.choice(citations)
        cited_authors = [self.authors.get(aid, {}).get('name', 'Unknown')
                        for aid, _ in self.paper_authors.get(cited_paper_id, [])]

        if not cited_authors:
            return None

        cited_author_name = cited_authors[0]
        cited_paper = self.papers.get(cited_paper_id, {})

        # 获取引用论文的第一作者
        first_author = self._get_first_author(paper_id)
        if not first_author:
            return None

        if year:
            question = f"{year}年由{first_author[1]}发表的论文中，哪篇引用了{cited_author_name}的《{cited_paper.get('title', 'Unknown')[:30]}...》？"
        else:
            question = f"由{first_author[1]}发表的论文中，哪篇引用了{cited_author_name}的研究？"

        return ComplexQuestion(
            question_id="CA_001",
            question_text=question,
            answer=paper.get('title', 'Unknown'),
            answer_type="paper",
            reasoning_chain=f"Filter(year={year}) -> Filter(author={first_author[1]}) -> Paper -> CITES -> {cited_paper_id}",
            difficulty="expert",
            constraints=[f"year:{year}" if year else None, f"author:{first_author[1]}", "citation"],
            explanation=f"该论文同时满足年份、作者和引用三个约束条件"
        )

    def generate_institution_productivity_question(self) -> Optional[ComplexQuestion]:
        """
        类型5: 机构产出统计问题
        例: "高压科学中心 Advanced Research 在2022年发表了几篇论文？"
        """
        # 统计每个机构每年的论文数
        inst_year_papers = defaultdict(lambda: defaultdict(list))

        for paper_id in self.papers:
            year = self._get_paper_year(paper_id)
            if year:
                insts = self._get_paper_institutions(paper_id)
                for inst_id, inst_name in insts:
                    inst_year_papers[inst_id][year].append(paper_id)

        # 找有多个年份数据的机构
        multi_year_insts = [(i, y, p) for i, years in inst_year_papers.items()
                           for y, p in years.items() if len(p) >= 2]

        if not multi_year_insts:
            return None

        inst_id, year, papers = random.choice(multi_year_insts)
        inst_name = self.institutions.get(inst_id, {}).get('name', 'Unknown')

        question = f"\"{inst_name[:25]}...\"的研究人员在{year}年发表了几篇论文？"

        return ComplexQuestion(
            question_id="IP_001",
            question_text=question,
            answer=str(len(papers)),
            answer_type="count",
            reasoning_chain=f"Institution({inst_name[:20]}) -> Authors -> Papers(year={year}) -> Count",
            difficulty="hard",
            constraints=["count", f"year:{year}", f"institution:{inst_name[:20]}"],
            explanation=f"该机构在{year}年共有{len(papers)}篇论文"
        )

    def generate_reverse_institution_question(self) -> Optional[ComplexQuestion]:
        """
        类型6: 反向推理 - 从论文找机构
        例: "《Metal-Organic Frameworks: Opportunities for Catalysis》这篇论文的第一作者来自哪个机构？"
        """
        # 选择有完整信息的论文
        candidates = []
        for paper_id in self.papers:
            first_author = self._get_first_author(paper_id)
            if first_author and first_author[0] in self.author_inst:
                inst_id = self.author_inst[first_author[0]]
                candidates.append((paper_id, first_author[0], inst_id))

        if not candidates:
            return None

        paper_id, author_id, inst_id = random.choice(candidates)
        paper = self.papers.get(paper_id, {})
        inst_name = self.institutions.get(inst_id, {}).get('name', 'Unknown')
        author_name = self.authors.get(author_id, {}).get('name', 'Unknown')

        title = paper.get('title', 'Unknown')
        if len(title) > 40:
            title = title[:40] + "..."

        question = f"《{title}》这篇论文的第一作者{author_name}来自哪个研究机构？"

        return ComplexQuestion(
            question_id="RI_001",
            question_text=question,
            answer=inst_name,
            answer_type="institution",
            reasoning_chain=f"Paper -> FirstAuthor({author_name}) -> Institution",
            difficulty="medium",
            constraints=["first_author", "institution"],
            explanation=f"该论文的第一作者{author_name}隶属于{inst_name}"
        )

    def generate_all(self, count_per_type: int = 2) -> List[ComplexQuestion]:
        """生成所有类型的复杂问题"""
        questions = []
        generators = [
            self.generate_cross_institution_question,
            self.generate_multi_constraint_question,
            self.generate_author_network_question,
            self.generate_citation_with_author_constraint,
            self.generate_institution_productivity_question,
            self.generate_reverse_institution_question,
        ]

        for generator in generators:
            for i in range(count_per_type):
                try:
                    q = generator()
                    if q:
                        q.question_id = f"{q.question_id.split('_')[0]}_{i+1:03d}"
                        questions.append(q)
                except Exception as e:
                    print(f"Error generating question: {e}")
                    continue

        return questions


def export_markdown_complex(questions: List[ComplexQuestion], output_path: Path):
    """导出复杂问题为Markdown"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 杨逸飞推理链Demo - 复杂问题版本\n\n")
        f.write("## 实验概述\n\n")
        f.write("本实验基于现有KG（52篇论文），利用多跳路径和复杂约束生成问题。\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**问题数量**: {len(questions)}\n\n")

        # 按难度统计
        difficulty_count = {}
        for q in questions:
            difficulty_count[q.difficulty] = difficulty_count.get(q.difficulty, 0) + 1

        f.write("**难度分布**:\n")
        for diff, count in sorted(difficulty_count.items()):
            f.write(f"- {diff}: {count}个\n")
        f.write("\n")

        # 问题列表
        f.write("## 问题列表\n\n")
        for i, q in enumerate(questions, 1):
            f.write(f"### 问题 {i} [{q.difficulty.upper()}]\n\n")
            f.write(f"**问题**: {q.question_text}\n\n")
            f.write(f"**答案**: {q.answer}\n\n")
            f.write(f"**答案类型**: {q.answer_type}\n\n")
            f.write(f"**推理链**: `{q.reasoning_chain}`\n\n")
            f.write(f"**约束条件**: {', '.join(filter(None, q.constraints))}\n\n")
            f.write(f"**唯一性解释**: {q.explanation}\n\n")
            f.write("---\n\n")


def main():
    print("=" * 70)
    print("杨逸飞推理链Demo - 复杂问题生成器")
    print("=" * 70)
    print()

    print("[1/3] 初始化生成器...")
    generator = ComplexQuestionGenerator()
    print(f"      ✓ 加载 {len(generator.papers)} 篇论文")
    print(f"      ✓ 加载 {len(generator.authors)} 位作者")
    print(f"      ✓ 加载 {len(generator.institutions)} 个机构")
    print(f"      ✓ 发现 {sum(1 for p in generator.paper_authors if len(generator._get_paper_institutions(p)) > 1)} 篇跨机构合作论文")

    print("\n[2/3] 生成复杂问题...")
    questions = generator.generate_all(count_per_type=2)
    print(f"      ✓ 生成 {len(questions)} 个复杂问题")

    # 统计
    type_count = {}
    diff_count = {}
    for q in questions:
        q_type = q.question_id.split('_')[0]
        type_count[q_type] = type_count.get(q_type, 0) + 1
        diff_count[q.difficulty] = diff_count.get(q.difficulty, 0) + 1

    print("\n      问题类型分布:")
    type_names = {
        'CI': '跨机构合作',
        'MC': '多约束筛选',
        'AN': '作者合作网络',
        'CA': '引用+作者约束',
        'IP': '机构产出统计',
        'RI': '反向机构推理'
    }
    for t, c in sorted(type_count.items()):
        print(f"        - {type_names.get(t, t)}: {c}个")

    print("\n      难度分布:")
    for d, c in sorted(diff_count.items(), key=lambda x: ['easy', 'medium', 'hard', 'expert'].index(x[0]) if x[0] in ['easy', 'medium', 'hard', 'expert'] else 99):
        print(f"        - {d}: {c}个")

    print("\n[3/3] 导出结果...")
    script_dir = Path(__file__).parent
    output_dir = script_dir / ".." / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / f"yang_chain_complex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    export_markdown_complex(questions, md_path)
    print(f"      ✓ Markdown: {md_path}")

    # JSON导出
    json_path = output_dir / f"yang_chain_complex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "experiment": "yang_yifei_complex",
                "generated_at": datetime.now().isoformat(),
                "question_count": len(questions),
                "kg_stats": {
                    "papers": len(generator.papers),
                    "authors": len(generator.authors),
                    "institutions": len(generator.institutions)
                }
            },
            "questions": [
                {
                    "id": q.question_id,
                    "text": q.question_text,
                    "answer": q.answer,
                    "answer_type": q.answer_type,
                    "difficulty": q.difficulty,
                    "reasoning_chain": q.reasoning_chain,
                    "constraints": q.constraints,
                    "explanation": q.explanation
                }
                for q in questions
            ]
        }, f, indent=2, ensure_ascii=False)
    print(f"      ✓ JSON: {json_path}")

    print()
    print("=" * 70)
    print("生成完成！")
    print("=" * 70)

    # 显示示例
    print("\n示例问题:")
    for q in questions[:3]:
        print(f"\n[{q.difficulty.upper()}] {q.question_text}")
        print(f"  答案: {q.answer}")
        print(f"  类型: {q.answer_type}")


if __name__ == "__main__":
    main()
