#!/usr/bin/env python3
"""
杨逸飞推理链Demo - 带缓存的API数据获取

解决API限流问题：
1. 将API结果缓存到本地
2. 优先从缓存读取
3. 缓存未命中时才调用API
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional, List
import urllib.request
import urllib.error
import urllib.parse


class CachedSemanticScholarAPI:
    """带缓存的Semantic Scholar API"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, cache_dir: str = "cache", delay: float = 1.5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.last_call_time = 0
        self.cache_hits = 0
        self.api_calls = 0

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用MD5避免文件名过长
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{key_hash}.json"

    def _load_cache(self, key: str) -> Optional[Dict]:
        """从缓存加载"""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self.cache_hits += 1
                    return json.load(f)
            except:
                return None
        return None

    def _save_cache(self, key: str, data: Dict):
        """保存到缓存"""
        cache_path = self._get_cache_path(key)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call_time = time.time()

    def _make_request(self, url: str, retries: int = 3) -> Optional[Dict]:
        """发送请求"""
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
                    self.api_calls += 1
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"        限流，等待{wait}秒...")
                    time.sleep(wait)
                    continue
                return None
            except Exception:
                return None
        return None

    def search_paper(self, title: str) -> Optional[Dict]:
        """搜索论文（带缓存）"""
        cache_key = f"search:{title}"

        # 先查缓存
        cached = self._load_cache(cache_key)
        if cached:
            print(f"      [缓存命中] {title[:40]}...")
            return cached

        # 调用API
        print(f"      [API查询] {title[:40]}...")
        clean_title = title.replace('"', '').replace("'", "")[:100]
        url = f"{self.BASE_URL}/paper/search?query={urllib.parse.quote(clean_title)}&fields=paperId,title,year,authors,citationCount&limit=1"

        result = self._make_request(url)
        if result:
            self._save_cache(cache_key, result)

        return result

    def get_references(self, ss_id: str, limit: int = 50) -> List[Dict]:
        """获取参考文献（带缓存）"""
        cache_key = f"refs:{ss_id}:{limit}"

        cached = self._load_cache(cache_key)
        if cached:
            return cached.get('data', [])

        url = f"{self.BASE_URL}/paper/{ss_id}/references?fields=paperId,title,year,authors&limit={limit}"
        result = self._make_request(url)

        if result:
            self._save_cache(cache_key, result)
            return result.get('data', [])
        return []

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "cache_hits": self.cache_hits,
            "api_calls": self.api_calls,
            "cache_files": len(list(self.cache_dir.glob("*.json")))
        }


def main():
    print("=" * 70)
    print("带缓存的API数据获取")
    print("=" * 70)

    script_dir = Path(__file__).parent
    cache_path = script_dir / ".." / "cache" / "ss_api"
    api = CachedSemanticScholarAPI(cache_dir=str(cache_path), delay=1.5)

    # 测试论文
    test_titles = [
        "Nested order-disorder framework containing a crystalline matrix",
        "Atomic packing and short-to-medium-range order in metallic glasses",
        "Melting of hybrid organic–inorganic perovskites",
        "Metal–Organic Frameworks: Opportunities for Catalysis",
        "Long-Range Topological Order in Metallic Glass"
    ]

    print(f"\n测试 {len(test_titles)} 篇论文...")
    print("-" * 50)

    for i, title in enumerate(test_titles, 1):
        print(f"\n[{i}/{len(test_titles)}]")
        result = api.search_paper(title)

        if result and result.get('data'):
            paper = result['data'][0]
            print(f"      ✓ SS ID: {paper.get('paperId', 'N/A')[:25]}...")
            print(f"      ✓ 引用数: {paper.get('citationCount', 0)}")
        else:
            print(f"      ✗ 未找到")

    # 再次查询（测试缓存）
    print("\n" + "=" * 70)
    print("第二次查询（测试缓存效果）")
    print("=" * 70)

    for title in test_titles[:3]:
        api.search_paper(title)

    # 统计
    stats = api.get_stats()
    print(f"\n{'='*70}")
    print("统计信息")
    print(f"{'='*70}")
    print(f"  API调用次数: {stats['api_calls']}")
    print(f"  缓存命中次数: {stats['cache_hits']}")
    print(f"  缓存文件数: {stats['cache_files']}")
    print(f"  命中率: {stats['cache_hits'] / (stats['api_calls'] + stats['cache_hits']) * 100:.1f}%")


if __name__ == "__main__":
    main()
