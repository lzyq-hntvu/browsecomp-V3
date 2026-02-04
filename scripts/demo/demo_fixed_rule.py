#!/usr/bin/env python3
"""
固定搭配Demo - 论文引用链
规则: Paper → CITES → Paper → CITES → Paper
约束: publication_year, citation_count
"""

import json
import random
from pathlib import Path
from datetime import datetime

# 硬编码规则
RULE = {
    "name": "论文-作者-机构链",
    "description": "Paper-HasAuthor-Author-AffiliatedWith-Institution",
    "pattern": ["Paper", "HAS_AUTHOR", "Author", "AFFILIATED_WITH", "Institution"],
    "constraints": ["publication_year", "author_name"],
    "target_count": 50
}


def load_kg():
    """加载知识图谱"""
    kg_path = "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"
    with open(kg_path, 'r') as f:
        return json.load(f)


def find_paper_author_institution_chains(kg):
    """
    找所有 Paper-HasAuthor-Author-AffiliatedWith-Institution 路径
    返回: [(paper_id, author_id, institution_id), ...]
    """
    # 构建图结构
    paper_info = {}
    author_info = {}
    inst_info = {}

    for node_data in kg.get("nodes", []):
        node_type = node_data.get("type")
        node_id = node_data.get("id")
        if node_type == "paper":
            paper_info[node_id] = node_data
        elif node_type == "author":
            author_info[node_id] = node_data
        elif node_type == "institution":
            inst_info[node_id] = node_data

    # 构建边映射
    paper_authors = {}  # paper_id -> [(author_id, author_order), ...]
    author_inst = {}    # author_id -> institution_id

    for edge in kg.get("edges", []):
        rel_type = edge.get("relation_type")
        if rel_type == "HAS_AUTHOR":
            paper_id = edge.get("source_id")
            author_id = edge.get("target_id")
            author_order = edge.get("author_order", "other")
            if paper_id not in paper_authors:
                paper_authors[paper_id] = []
            paper_authors[paper_id].append((author_id, author_order))
        elif rel_type == "AFFILIATED_WITH":
            author_id = edge.get("source_id")
            inst_id = edge.get("target_id")
            author_inst[author_id] = inst_id

    # 找2跳路径: Paper -> Author -> Institution
    chains = []
    for paper_id in paper_info:
        if paper_id not in paper_authors:
            continue
        for author_id, author_order in paper_authors[paper_id]:
            if author_id in author_inst:
                inst_id = author_inst[author_id]
                if inst_id in inst_info:
                    chains.append((paper_id, author_id, inst_id, author_order))

    return chains, paper_info, author_info, inst_info


def get_paper_year(paper):
    """从publication_date提取年份"""
    date_str = paper.get("publication_date", "")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").year
        except ValueError:
            pass
    return None


def generate_question(chain, paper_info, author_info, inst_info, index):
    """为一条链生成问题 - 确保答案唯一"""
    paper_id, author_id, inst_id, author_order = chain
    paper = paper_info[paper_id]
    author = author_info[author_id]
    inst = inst_info[inst_id]

    year = get_paper_year(paper)
    if year is None:
        year = "未知年份"

    author_name = author.get("name", "Unknown")
    inst_name = inst.get("name", "Unknown")
    paper_title = paper.get("title", "Unknown")

    # 构造问题 - 包含作者名字确保唯一性
    # 句式: "XXX年发表的论文中，作者XXX来自哪个机构？"
    question = f"{year}年发表的论文中，作者{author_name}来自哪个机构？"

    return {
        "question_id": f"FIXED_{index:03d}",
        "question_text": question,
        "answer": inst_name,
        "reasoning_chain": f"{paper_id} → HAS_AUTHOR → {author_id} → AFFILIATED_WITH → {inst_id}",
        "constraints": {
            "publication_year": year,
            "author_name": author_name,
            "author_order": author_order
        },
        "details": {
            "paper_title": paper_title,
            "author_name": author_name,
            "institution": inst_name
        }
    }


def export_markdown(questions, output_path):
    """导出为Markdown"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 固定搭配Demo - 论文作者机构链\n\n")
        f.write(f"**规则**: {RULE['description']}\n\n")
        f.write(f"**约束**: {', '.join(RULE['constraints'])}\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**问题数量**: {len(questions)}\n\n")
        f.write("---\n\n")

        for i, q in enumerate(questions, 1):
            f.write(f"## 问题 {i}\n\n")
            f.write(f"**ID**: {q['question_id']}\n\n")
            f.write(f"**问题**: {q['question_text']}\n\n")
            f.write(f"**答案**: {q['answer']}\n\n")
            f.write(f"**推理链**: `{q['reasoning_chain']}`\n\n")
            f.write(f"**约束值**: {q['constraints']}\n\n")
            f.write(f"**详情**:\n")
            f.write(f"  - 论文: {q['details']['paper_title']}\n")
            f.write(f"  - 作者: {q['details']['author_name']}\n")
            f.write(f"  - 机构: {q['details']['institution']}\n\n")
            f.write("---\n\n")


def main():
    print("=" * 60)
    print("固定搭配Demo - 论文引用链生成器")
    print("=" * 60)
    print(f"规则: {RULE['name']}")
    print(f"目标: 生成{RULE['target_count']}个问题")
    print()

    # 加载KG
    print("[1/4] 加载知识图谱...")
    kg = load_kg()
    print(f"      加载完成")

    # 找引用链
    print("[2/4] 查找论文-作者-机构链...")
    chains, paper_info, author_info, inst_info = find_paper_author_institution_chains(kg)
    print(f"      找到 {len(chains)} 条可能的路径")

    if len(chains) < RULE['target_count']:
        print(f"      警告: 路径数量不足，将生成 {len(chains)} 个问题")
        target = len(chains)
    else:
        target = RULE['target_count']

    # 随机选择
    selected = random.sample(chains, target)

    # 生成问题
    print("[3/4] 生成问题...")
    questions = []
    for i, chain in enumerate(selected, 1):
        q = generate_question(chain, paper_info, author_info, inst_info, i)
        questions.append(q)
        if i % 10 == 0:
            print(f"      已生成 {i}/{target}")

    # 导出
    print("[4/4] 导出Markdown...")
    output_dir = Path("output/demo_fixed_rule")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"fixed_rule_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    export_markdown(questions, output_path)

    print()
    print("=" * 60)
    print("生成完成!")
    print(f"输出文件: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
