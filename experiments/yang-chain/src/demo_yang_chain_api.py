#!/usr/bin/env python3
"""
杨逸飞推理链Demo - Semantic Scholar API数据补充

通过API获取真实引用关系，构建10节点链

API文档: https://api.semanticscholar.org/api-docs/
- 免费使用，无需API Key（有Rate Limit）
- 支持批量查询
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error


@dataclass
class PaperData:
    """论文数据结构"""
    paper_id: str  # 我们的ID (paper_1, paper_2...)
    ss_id: Optional[str]  # Semantic Scholar ID
    title: str
    authors: List[str]
    year: int
    citation_count: int
    reference_ids: List[str]  # 引用的论文SS ID列表
    abstract: str = ""


class SemanticScholarAPI:
    """Semantic Scholar API客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, delay: float = 1.0):
        self.delay = delay  # API调用间隔（避免触发限流）
        self.last_call_time = 0

    def _rate_limit(self):
        """简单的速率限制"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call_time = time.time()

    def _make_request(self, url: str) -> Optional[Dict]:
        """发送HTTP请求"""
        try:
            self._rate_limit()
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "BrowseComp-Experiment/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    触发限流，等待5秒...")
                time.sleep(5)
                return self._make_request(url)  # 重试
            print(f"    HTTP错误: {e.code}")
            return None
        except Exception as e:
            print(f"    请求失败: {e}")
            return None

    def search_paper(self, title: str) -> Optional[Dict]:
        """根据标题搜索论文"""
        # 简化标题，去除特殊字符
        clean_title = title.replace('"', '').replace("'", "")[:100]
        url = f"{self.BASE_URL}/paper/search?query={urllib.parse.quote(clean_title)}&fields=paperId,title,year,authors,citationCount,referenceCount&limit=1"

        result = self._make_request(url)
        if result and result.get('data'):
            return result['data'][0]
        return None

    def get_paper_references(self, ss_id: str, limit: int = 100) -> List[Dict]:
        """获取论文引用的参考文献"""
        url = f"{self.BASE_URL}/paper/{ss_id}/references?fields=paperId,title,year,authors&limit={limit}"

        result = self._make_request(url)
        if result and result.get('data'):
            return [ref.get('citedPaper', {}) for ref in result['data'] if ref.get('citedPaper')]
        return []

    def get_paper_citations(self, ss_id: str, limit: int = 100) -> List[Dict]:
        """获取引用该论文的论文"""
        url = f"{self.BASE_URL}/paper/{ss_id}/citations?fields=paperId,title,year,authors&limit={limit}"

        result = self._make_request(url)
        if result and result.get('data'):
            return [cit.get('citingPaper', {}) for cit in result['data'] if cit.get('citingPaper')]
        return []


class KGDataExtender:
    """KG数据扩展器"""

    def __init__(self, kg_path: str = "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"):
        self.kg_path = Path(kg_path)
        self.kg = None
        self.api = SemanticScholarAPI(delay=1.5)  # 1.5秒间隔，遵守Rate Limit
        self.papers_data: Dict[str, PaperData] = {}

        self._load_kg()

    def _load_kg(self):
        """加载现有KG"""
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            self.kg = json.load(f)

        # 提取论文基本信息
        for node in self.kg['nodes']:
            if node['type'] == 'paper':
                self.papers_data[node['id']] = PaperData(
                    paper_id=node['id'],
                    ss_id=None,
                    title=node.get('title', ''),
                    authors=[],
                    year=self._extract_year(node.get('publication_date', '')),
                    citation_count=0,
                    reference_ids=[]
                )

    def _extract_year(self, date_str: str) -> int:
        """提取年份"""
        if date_str:
            try:
                return int(date_str.split('-')[0])
            except:
                pass
        return 0

    def enrich_papers(self, max_papers: int = 5) -> Dict[str, PaperData]:
        """
        使用API补充论文数据

        Args:
            max_papers: 最多处理多少篇论文（避免API调用过多）

        Returns:
            补充后的论文数据
        """
        print(f"开始补充数据（最多{max_papers}篇论文）...")
        print(f"API调用间隔: {self.api.delay}秒")
        print()

        enriched_count = 0

        # 选择要补充的论文（优先选有引用的）
        paper_ids = list(self.papers_data.keys())[:max_papers]

        for i, paper_id in enumerate(paper_ids, 1):
            paper = self.papers_data[paper_id]
            print(f"[{i}/{len(paper_ids)}] 处理: {paper.title[:50]}...")

            # 1. 搜索论文获取SS ID
            search_result = self.api.search_paper(paper.title)
            if not search_result:
                print(f"    ✗ 未找到匹配论文")
                continue

            ss_id = search_result.get('paperId')
            if not ss_id:
                print(f"    ✗ 无SS ID")
                continue

            paper.ss_id = ss_id
            paper.citation_count = search_result.get('citationCount', 0)
            paper.authors = [a.get('name', '') for a in search_result.get('authors', [])]

            print(f"    ✓ 找到SS ID: {ss_id[:20]}...")
            print(f"    ✓ 引用数: {paper.citation_count}")

            # 2. 获取参考文献
            print(f"    获取参考文献...")
            references = self.api.get_paper_references(ss_id, limit=50)
            paper.reference_ids = [ref.get('paperId') for ref in references if ref.get('paperId')]
            print(f"    ✓ 获取{len(paper.reference_ids)}篇参考文献")

            enriched_count += 1
            print()

        print(f"\n数据补充完成: {enriched_count}/{len(paper_ids)}篇论文")
        return self.papers_data

    def build_extended_citation_graph(self) -> Dict[str, List[str]]:
        """
        构建扩展的引用图
        将API获取的引用关系映射回我们的paper_id
        """
        print("\n构建扩展引用图...")

        # 建立SS ID到paper_id的映射
        ss_to_local = {p.ss_id: p.paper_id for p in self.papers_data.values() if p.ss_id}

        # 构建引用图
        citation_graph = {}

        for paper_id, paper in self.papers_data.items():
            if not paper.ss_id:
                continue

            # 查找引用的论文是否在我们的数据集中
            cited_local_papers = []
            for ref_ss_id in paper.reference_ids:
                if ref_ss_id in ss_to_local:
                    cited_local_papers.append(ss_to_local[ref_ss_id])

            # 同时包含原有的引用关系
            for edge in self.kg.get('edges', []):
                if edge.get('relation_type') == 'CITES' and edge.get('source_id') == paper_id:
                    if edge.get('target_id') not in cited_local_papers:
                        cited_local_papers.append(edge.get('target_id'))

            if cited_local_papers:
                citation_graph[paper_id] = cited_local_papers
                print(f"  {paper_id}: {len(cited_local_papers)}个引用")

        return citation_graph

    def save_extended_data(self, output_path: str = None):
        """保存扩展后的数据"""
        if output_path is None:
            script_dir = Path(__file__).parent
            output_path = script_dir / ".." / "data" / "kg_extended.json"
        """保存扩展后的数据"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建引用图
        citation_graph = self.build_extended_citation_graph()

        # 保存数据
        data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "source": "Semantic Scholar API + Original KG",
                "paper_count": len(self.papers_data),
                "enriched_count": sum(1 for p in self.papers_data.values() if p.ss_id)
            },
            "papers": [asdict(p) for p in self.papers_data.values()],
            "citation_graph": citation_graph
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 数据已保存: {output_path}")
        return output_path


class TenNodeChainBuilder:
    """10节点链构建器（使用扩展数据）"""

    def __init__(self, extended_data_path: str = "data/kg_extended.json"):
        self.data_path = Path(extended_data_path)
        self.citation_graph = {}
        self.papers = {}
        self._load_data()

    def _load_data(self):
        """加载扩展数据"""
        if not self.data_path.exists():
            print(f"扩展数据不存在: {self.data_path}")
            return

        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.citation_graph = data.get('citation_graph', {})
        self.papers = {p['paper_id']: p for p in data.get('papers', [])}

    def build_long_chain(self, start_paper: Optional[str] = None, target_length: int = 10) -> List[str]:
        """构建长链（使用回溯+数据补充）"""
        if not self.citation_graph:
            print("无扩展数据，无法构建长链")
            return []

        if start_paper is None:
            # 选择引用最多的作为起点
            sorted_papers = sorted(
                self.citation_graph.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            if sorted_papers:
                start_paper = sorted_papers[0][0]
            else:
                start_paper = list(self.papers.keys())[0]

        print(f"构建{target_length}节点链，起点: {start_paper}")

        # 使用DFS找最长链
        longest = []
        visited = set()

        def dfs(current: str, path: List[str]):
            nonlocal longest
            if len(path) > len(longest):
                longest = path.copy()
                if len(longest) >= target_length:
                    return  # 达到目标

            # 获取可引用的论文
            candidates = self.citation_graph.get(current, [])
            # 随机打乱以增加多样性
            shuffled = candidates.copy()
            random.shuffle(shuffled)

            for next_paper in shuffled:
                if next_paper not in visited and next_paper in self.papers:
                    visited.add(next_paper)
                    path.append(next_paper)
                    dfs(next_paper, path)
                    if len(longest) >= target_length:
                        return
                    path.pop()
                    visited.remove(next_paper)

        visited.add(start_paper)
        dfs(start_paper, [start_paper])

        return longest


def main():
    print("=" * 70)
    print("Semantic Scholar API 数据补充 + 10节点链构建")
    print("=" * 70)
    print()

    # 步骤1: 数据补充
    extender = KGDataExtender()
    enriched = extender.enrich_papers(max_papers=3)  # 先处理3篇测试

    # 步骤2: 保存扩展数据
    data_path = extender.save_extended_data()

    # 步骤3: 构建长链
    print("\n" + "=" * 70)
    print("测试10节点链构建")
    print("=" * 70)

    builder = TenNodeChainBuilder(str(data_path))

    for target in [10, 8, 5]:
        print(f"\n尝试构建{target}节点链:")
        chain = builder.build_long_chain(target_length=target)
        print(f"  结果: {len(chain)}节点")
        if len(chain) >= 2:
            for i, pid in enumerate(chain[:5]):  # 只显示前5个
                paper = builder.papers.get(pid, {})
                print(f"    [{i+1}] {pid}: {paper.get('title', 'Unknown')[:40]}...")
            if len(chain) > 5:
                print(f"    ... ({len(chain)-5} more)")


if __name__ == "__main__":
    import urllib.parse
    main()
