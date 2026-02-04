#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 递归API数据补充

策略:
1. 从起始论文获取引用
2. 为引用的论文也获取API数据
3. 递归扩展，直到达到目标链长度
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
import urllib.parse


@dataclass
class PaperData:
    """论文数据结构"""
    paper_id: str
    ss_id: Optional[str]
    title: str
    authors: List[str]
    year: int
    citation_count: int
    reference_ids: List[str]  # 引用的SS ID列表


class SemanticScholarAPI:
    """Semantic Scholar API客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self.last_call_time = 0
        self.call_count = 0

    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call_time = time.time()
        self.call_count += 1

    def _make_request(self, url: str, retries: int = 3) -> Optional[Dict]:
        """发送HTTP请求"""
        for attempt in range(retries):
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
                    wait_time = 5 * (attempt + 1)
                    print(f"      限流，等待{wait_time}秒...")
                    time.sleep(wait_time)
                    continue
                print(f"      HTTP错误: {e.code}")
                return None
            except Exception as e:
                print(f"      请求失败: {e}")
                return None
        return None

    def search_paper(self, title: str) -> Optional[Dict]:
        """搜索论文"""
        clean_title = title.replace('"', '').replace("'", "")[:100]
        url = f"{self.BASE_URL}/paper/search?query={urllib.parse.quote(clean_title)}&fields=paperId,title,year,authors,citationCount&limit=1"
        result = self._make_request(url)
        if result and result.get('data'):
            return result['data'][0]
        return None

    def get_paper_references(self, ss_id: str, limit: int = 50) -> List[Dict]:
        """获取参考文献"""
        url = f"{self.BASE_URL}/paper/{ss_id}/references?fields=paperId,title,year,authors&limit={limit}"
        result = self._make_request(url)
        if result and result.get('data'):
            return [ref.get('citedPaper', {}) for ref in result['data'] if ref.get('citedPaper')]
        return []


class RecursiveKGExtender:
    """递归KG扩展器"""

    def __init__(self, kg_path: str = "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"):
        self.kg_path = Path(kg_path)
        self.api = SemanticScholarAPI(delay=1.5)

        # 加载现有数据
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            self.kg = json.load(f)

        # 现有论文
        self.existing_papers = {
            n['id']: n for n in self.kg['nodes']
            if n['type'] == 'paper'
        }

        # 扩展的论文池 (SS ID -> PaperData)
        self.extended_papers: Dict[str, PaperData] = {}

        # SS ID映射
        self.ss_to_local: Dict[str, str] = {}
        self.local_to_ss: Dict[str, str] = {}

    def extract_year(self, date_str: str) -> int:
        if date_str:
            try:
                return int(date_str.split('-')[0])
            except:
                pass
        return 0

    def enrich_paper(self, paper_id: str) -> Optional[PaperData]:
        """补充单篇论文数据"""
        if paper_id in self.local_to_ss:
            ss_id = self.local_to_ss[paper_id]
            if ss_id in self.extended_papers:
                return self.extended_papers[ss_id]

        paper = self.existing_papers.get(paper_id)
        if not paper:
            return None

        print(f"    API查询: {paper['title'][:50]}...")

        result = self.api.search_paper(paper['title'])
        if not result:
            return None

        ss_id = result.get('paperId')
        if not ss_id:
            return None

        # 获取参考文献
        refs = self.api.get_paper_references(ss_id, limit=30)
        ref_ids = [r.get('paperId') for r in refs if r.get('paperId')]

        paper_data = PaperData(
            paper_id=paper_id,
            ss_id=ss_id,
            title=paper['title'],
            authors=[a.get('name', '') for a in result.get('authors', [])],
            year=result.get('year', 0) or self.extract_year(paper.get('publication_date', '')),
            citation_count=result.get('citationCount', 0),
            reference_ids=ref_ids
        )

        self.extended_papers[ss_id] = paper_data
        self.ss_to_local[ss_id] = paper_id
        self.local_to_ss[paper_id] = ss_id

        print(f"      ✓ SS ID: {ss_id[:25]}...")
        print(f"      ✓ 引用数: {paper_data.citation_count}")
        print(f"      ✓ 参考文献: {len(ref_ids)}篇")

        return paper_data

    def recursive_extend(self, start_paper_id: str, target_depth: int = 10, max_papers: int = 50) -> Dict[str, PaperData]:
        """
        递归扩展论文数据

        Args:
            start_paper_id: 起始论文
            target_depth: 目标链深度
            max_papers: 最大扩展论文数
        """
        print(f"\n递归扩展: 从 {start_paper_id} 开始，目标深度 {target_depth}")
        print("=" * 60)

        # BFS扩展
        queue = [(start_paper_id, 0)]  # (paper_id, depth)
        visited = {start_paper_id}
        enriched_count = 0

        while queue and enriched_count < max_papers:
            current_id, depth = queue.pop(0)

            if depth >= target_depth:
                continue

            print(f"\n[{enriched_count+1}/{max_papers}] 深度{depth}: {current_id}")

            # 补充当前论文
            paper_data = self.enrich_paper(current_id)
            if not paper_data:
                print(f"      ✗ 无法获取数据")
                continue

            enriched_count += 1

            # 获取参考文献中的论文
            if depth < target_depth - 1:
                for ref_ss_id in paper_data.reference_ids[:5]:  # 只取前5个以控制规模
                    if ref_ss_id not in self.ss_to_local:
                        # 这是一个新论文，创建新的paper_id
                        new_id = f"paper_ext_{len(self.extended_papers)}"

                        # 尝试获取这个引用论文的基本信息
                        # 由于API限制，我们简化处理，只记录SS ID
                        self.ss_to_local[ref_ss_id] = new_id
                        self.local_to_ss[new_id] = ref_ss_id

                        # 标记为待补充
                        if new_id not in visited:
                            visited.add(new_id)
                            queue.append((new_id, depth + 1))

        print(f"\n扩展完成: 共补充 {enriched_count} 篇论文")
        print(f"API调用次数: {self.api.call_count}")

        return {p.paper_id: p for p in self.extended_papers.values()}

    def build_extended_graph(self) -> Dict[str, List[str]]:
        """构建扩展引用图"""
        print("\n构建扩展引用图...")

        graph = {}
        for paper_data in self.extended_papers.values():
            cited_papers = []
            for ref_ss_id in paper_data.reference_ids:
                if ref_ss_id in self.ss_to_local:
                    cited_papers.append(self.ss_to_local[ref_ss_id])

            if cited_papers:
                graph[paper_data.paper_id] = cited_papers
                print(f"  {paper_data.paper_id}: {len(cited_papers)}个引用")

        return graph

    def save_data(self, output_path: str = None):
        """保存数据"""
        if output_path is None:
            script_dir = Path(__file__).parent
            output_path = script_dir / ".." / "data" / "kg_extended_recursive.json"
        """保存数据"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        graph = self.build_extended_graph()

        data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "api_calls": self.api.call_count,
                "paper_count": len(self.extended_papers),
                "original_papers": len(self.existing_papers)
            },
            "papers": [asdict(p) for p in self.extended_papers.values()],
            "citation_graph": graph,
            "ss_to_local": self.ss_to_local
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 数据已保存: {output_path}")
        return output_path


class TenNodeChainBuilder:
    """10节点链构建器"""

    def __init__(self, data_path: str = None):
        if data_path is None:
            script_dir = Path(__file__).parent
            data_path = script_dir / ".." / "data" / "kg_extended_recursive.json"
        self.data_path = Path(data_path)
        self.graph = {}
        self.papers = {}
        self._load()

    def _load(self):
        if not self.data_path.exists():
            return

        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.graph = data.get('citation_graph', {})
        self.papers = {p['paper_id']: p for p in data.get('papers', [])}

    def build_chain_dfs(self, start: str, target: int = 10) -> List[str]:
        """使用DFS构建链"""
        print(f"\n构建{target}节点链，起点: {start}")

        longest = []
        visited = set()

        def dfs(current: str, path: List[str]):
            nonlocal longest
            if len(path) > len(longest):
                longest = path.copy()
                print(f"    发现{len(longest)}节点链...")
                if len(longest) >= target:
                    return

            neighbors = self.graph.get(current, [])
            # 随机打乱
            shuffled = neighbors.copy()
            random.shuffle(shuffled)

            for next_paper in shuffled:
                if next_paper not in visited and next_paper in self.papers:
                    visited.add(next_paper)
                    path.append(next_paper)
                    dfs(next_paper, path)
                    if len(longest) >= target:
                        return
                    path.pop()
                    visited.remove(next_paper)

        visited.add(start)
        dfs(start, [start])

        return longest

    def print_chain(self, chain: List[str]):
        """打印链详情"""
        print(f"\n链详情 ({len(chain)}节点):")
        for i, pid in enumerate(chain):
            paper = self.papers.get(pid, {})
            year = paper.get('year', '?')
            title = paper.get('title', 'Unknown')[:45]
            print(f"  [{i+1:2d}] {pid:15s} [{year}] {title}...")


def main():
    print("=" * 70)
    print("递归API扩展 + 10节点链构建")
    print("=" * 70)

    # Step 1: 递归扩展
    extender = RecursiveKGExtender()
    papers = extender.recursive_extend(
        start_paper_id='paper_1',
        target_depth=10,
        max_papers=15  # 限制数量以控制API调用
    )

    # Step 2: 保存
    data_path = extender.save_data()

    # Step 3: 构建长链
    print("\n" + "=" * 70)
    print("测试10节点链")
    print("=" * 70)

    builder = TenNodeChainBuilder(str(data_path))

    if not builder.graph:
        print("没有扩展数据，无法构建链")
        return

    # 尝试构建
    targets = [10, 8, 5]
    for target in targets:
        chain = builder.build_chain_dfs('paper_1', target)
        builder.print_chain(chain)

        if len(chain) >= target:
            print(f"\n✓ 成功构建{len(chain)}节点链!")
            break
        else:
            print(f"\n✗ 仅构建{len(chain)}节点链（目标{target}）")


if __name__ == "__main__":
    main()
