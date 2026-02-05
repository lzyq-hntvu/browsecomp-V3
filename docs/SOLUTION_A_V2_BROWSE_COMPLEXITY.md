# 方案A v2.0: 基于浏览复杂度的重构设计

**日期**: 2026-02-04  
**版本**: v2.0 (重大修订)  
**状态**: 设计阶段

---

## 🎯 核心修订

### v1.0 的致命缺陷

**问题**: 误解了BrowseComp的核心指标

```
v1.0 理解 (错误):
  复杂度 = 约束条件数量
  → 生成3-5个约束的问题

BrowseComp 真实定义 (正确):
  复杂度 = Browse Complexity = 独立页面访问数
  → 需要跳转3-5个网页才能回答
```

### v2.0 核心改进

**新目标**: 生成需要**多页跳转推理**的问题

```
❌ v1.0 生成的问题 (单页多属性):
"李明轩(本科清华,博士MIT)2020年发表的论文标题是什么?"
Browse Complexity = 1 (访问李明轩主页即可)

✅ v2.0 应该生成的问题 (多页跳转):
"李明轩(本科清华)2020年与他在MIT的导师共同发表的论文标题是什么?"
Browse Complexity = 3
  Page 1: 李明轩主页 → 获取导师名字
  Page 2: 论文列表页 → 找到2020年论文
  Page 3: 论文详情页 → 确认共同作者
```

---

## 📐 新架构设计

### 核心概念: 虚拟网页网络

**从"学者档案"到"网页图"**

```
v1.0: 虚拟学者档案 (单个对象包含所有信息)
v2.0: 虚拟网页网络 (信息分散在多个页面,需跳转)
```

### 数据结构设计

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class VirtualWebPage:
    """虚拟网页基类"""
    page_id: str              # 唯一标识: "page_001"
    url: str                  # 虚拟URL: "http://virtual.edu/scholar/limingxuan"
    page_type: str            # 页面类型
    title: str                # 页面标题
    content: Dict[str, Any]   # 页面内容 (部分信息)
    outgoing_links: List[str] # 出链 (指向其他page_id)
    
    def get_visible_info(self) -> Dict[str, Any]:
        """获取该页面直接可见的信息 (不需要跳转)"""
        return self.content

@dataclass
class ScholarHomePage(VirtualWebPage):
    """学者个人主页"""
    
    def __init__(self, scholar_name: str, **kwargs):
        super().__init__(
            page_type="scholar_homepage",
            title=f"{scholar_name} - Academic Homepage",
            **kwargs
        )
        
        # 页面内容结构
        self.content = {
            # === 直接可见信息 ===
            "name": scholar_name,
            "current_position": "...",
            "email": "...",
            
            # === 教育背景 (部分) ===
            "education_summary": [
                {"degree": "Ph.D.", "university": "MIT", "year": 2017},
                {"degree": "B.S.", "university": "Tsinghua University", "year": 2012}
            ],
            # ⚠️ 不包含导师信息! 需要跳转到advisor页面
            
            # === 研究兴趣 ===
            "research_interests": ["NLP", "Machine Learning"],
            
            # === 近期论文 (只显示3篇) ===
            "recent_papers": [
                {
                    "title": "Attention Mechanisms...",
                    "year": 2020,
                    "detail_link": "page_101"  # ⚠️ 需要跳转
                },
                # 最多3篇
            ],
            
            # === 链接区域 ===
            "links": {
                "advisor": "page_002",           # ⚠️ 导师信息需要跳转
                "all_publications": "page_050",  # ⚠️ 完整论文列表需要跳转
                "google_scholar": "page_051",    # ⚠️ 引用信息需要跳转
                "coauthors": "page_052"          # ⚠️ 合作者网络需要跳转
            }
        }
        
        self.outgoing_links = list(self.content["links"].values())

@dataclass
class PaperDetailPage(VirtualWebPage):
    """论文详情页"""
    
    def __init__(self, paper_title: str, **kwargs):
        super().__init__(
            page_type="paper_detail",
            title=paper_title,
            **kwargs
        )
        
        self.content = {
            # === 基本信息 ===
            "title": paper_title,
            "year": 2020,
            "venue": "EMNLP",
            "venue_link": "page_201",  # ⚠️ 会议详情需要跳转
            
            # === 作者列表 (只有名字和链接) ===
            "authors": [
                {"name": "李明轩", "order": 1, "homepage_link": "page_001"},
                {"name": "张伟", "order": 2, "homepage_link": "page_002"}
            ],
            # ⚠️ 作者详细信息(教育背景、机构等)需要跳转到各自主页
            
            # === 论文内容 ===
            "abstract": "...",
            "citation_count": 150,
            "citations_link": "page_102",  # ⚠️ 引用列表需要跳转
            
            # === PDF和代码 ===
            "pdf_link": "page_103",
            "code_link": "page_104"
        }

@dataclass
class PublicationListPage(VirtualWebPage):
    """学者完整论文列表页"""
    
    def __init__(self, scholar_name: str, papers: List[Dict], **kwargs):
        super().__init__(
            page_type="publication_list",
            title=f"{scholar_name} - Publications",
            **kwargs
        )
        
        self.content = {
            "scholar_name": scholar_name,
            "scholar_link": "page_001",  # 回到学者主页
            
            # === 论文列表 (按年份分组) ===
            "papers_by_year": {
                "2020": [
                    {
                        "title": "Attention Mechanisms...",
                        "venue": "EMNLP",
                        "detail_link": "page_101"  # ⚠️ 详情需要跳转
                    },
                    # ... 更多论文
                ],
                "2019": [...]
            },
            
            # === 统计信息 ===
            "total_papers": 15,
            "total_citations": 1200,
            "h_index": 8
        }

@dataclass
class AdvisorPage(VirtualWebPage):
    """导师个人主页"""
    
    def __init__(self, advisor_name: str, **kwargs):
        super().__init__(
            page_type="scholar_homepage",
            title=f"{advisor_name} - Faculty Page",
            **kwargs
        )
        
        self.content = {
            "name": advisor_name,
            "title": "Professor",
            "department": "Computer Science",
            "university": "MIT",
            
            # === 学生列表 ===
            "current_students": [
                {"name": "John Doe", "homepage_link": "page_010"}
            ],
            "past_students": [
                {"name": "李明轩", "graduation_year": 2017, "homepage_link": "page_001"}
            ],
            
            # === 研究和论文 ===
            "research_areas": ["Machine Learning", "NLP"],
            "publications_link": "page_060",  # ⚠️ 导师论文列表需要跳转
        }

@dataclass
class VenueProceedings(VirtualWebPage):
    """会议/期刊论文集页面"""
    
    def __init__(self, venue_name: str, year: int, **kwargs):
        super().__init__(
            page_type="venue_proceedings",
            title=f"{venue_name} {year} Proceedings",
            **kwargs
        )
        
        self.content = {
            "venue": venue_name,
            "year": year,
            "location": "Virtual",
            
            # === 论文列表 (只有标题和链接) ===
            "papers": [
                {
                    "title": "Attention Mechanisms...",
                    "authors": ["李明轩", "张伟"],  # 只有名字
                    "detail_link": "page_101"  # ⚠️ 详情需要跳转
                },
                # ... 50-100篇论文
            ],
            
            "total_papers": 85
        }
```

### 虚拟网页图 (Web Graph)

```python
class VirtualWebGraph:
    """虚拟网页网络"""
    
    def __init__(self):
        self.pages: Dict[str, VirtualWebPage] = {}
        self.page_index: Dict[str, List[str]] = {}  # 索引: page_type -> [page_ids]
    
    def add_page(self, page: VirtualWebPage):
        """添加页面到图"""
        self.pages[page.page_id] = page
        
        # 更新索引
        if page.page_type not in self.page_index:
            self.page_index[page.page_type] = []
        self.page_index[page.page_type].append(page.page_id)
    
    def get_page(self, page_id: str) -> Optional[VirtualWebPage]:
        """访问页面 (模拟浏览器跳转)"""
        return self.pages.get(page_id)
    
    def navigate(self, current_page_id: str, link_key: str) -> Optional[VirtualWebPage]:
        """
        从当前页面通过链接跳转到目标页面
        
        模拟用户点击链接的行为
        """
        current_page = self.get_page(current_page_id)
        if not current_page:
            return None
        
        # 获取链接
        if "links" in current_page.content:
            target_page_id = current_page.content["links"].get(link_key)
        else:
            target_page_id = current_page.content.get(link_key)
        
        if target_page_id:
            return self.get_page(target_page_id)
        
        return None
    
    def simulate_browse_path(self, start_page_id: str, question: str) -> List[str]:
        """
        模拟回答问题所需的浏览路径
        
        Returns:
            访问的page_id列表 (Browse Complexity = len(path))
        """
        # 这个函数用于验证问题的Browse Complexity
        # 实现需要NLP理解问题,暂时简化
        pass
```

---

## 🔧 生成流程重构

### 新流程: 先建图,再生成问题

```
阶段1: 构建虚拟网页图 (一次性)
  ├─ LLM生成1000个学者的基本信息
  ├─ 为每个学者创建多个页面:
  │   ├─ 个人主页 (ScholarHomePage)
  │   ├─ 完整论文列表页 (PublicationListPage)
  │   ├─ 导师页面 (AdvisorPage)
  │   └─ Google Scholar页面
  ├─ 为每篇论文创建:
  │   └─ 论文详情页 (PaperDetailPage)
  ├─ 为每个会议/期刊创建:
  │   └─ 论文集页面 (VenueProceedings)
  └─ 保存到 virtual_web_graph.json

阶段2: 从网页图采样生成问题
  ├─ 随机选择起始页面
  ├─ 设计需要跳转的查询路径
  │   例如: ScholarHome → Advisor → Paper → Coauthor
  ├─ 提取路径上的约束条件
  ├─ 生成问题文本
  └─ 验证Browse Complexity
```

### 关键: 强制跨实体跳转

```python
class BrowseComplexityController:
    """控制Browse Complexity的问题生成器"""
    
    def __init__(self, web_graph: VirtualWebGraph):
        self.graph = web_graph
    
    def generate_question(self, target_complexity: int = 3) -> Dict:
        """
        生成指定Browse Complexity的问题
        
        Args:
            target_complexity: 目标浏览复杂度 (2-5)
        
        Returns:
            {
                "question": "...",
                "answer": "...",
                "browse_path": [page_id1, page_id2, ...],
                "complexity": 3
            }
        """
        
        # 步骤1: 设计浏览路径
        browse_path = self._design_browse_path(target_complexity)
        
        # 步骤2: 从路径提取约束和答案
        constraints, answer = self._extract_constraints_from_path(browse_path)
        
        # 步骤3: 生成问题文本
        question = self._generate_question_text(constraints, answer)
        
        # 步骤4: 验证Browse Complexity
        actual_complexity = self._verify_complexity(question, browse_path)
        
        if actual_complexity != target_complexity:
            # 重试
            return self.generate_question(target_complexity)
        
        return {
            "question": question,
            "answer": answer,
            "browse_path": browse_path,
            "complexity": actual_complexity
        }
    
    def _design_browse_path(self, target_complexity: int) -> List[str]:
        """
        设计需要指定跳转次数的浏览路径
        
        Complexity 2: Scholar → Paper
        Complexity 3: Scholar → Advisor → Paper
        Complexity 4: Scholar → Paper → Coauthor → Institution
        Complexity 5: Scholar → Advisor → Paper → Venue → Another Paper
        """
        
        if target_complexity == 2:
            # 路径模板: Scholar → Paper
            scholar_page = random.choice(self.graph.page_index["scholar_homepage"])
            scholar = self.graph.get_page(scholar_page)
            paper_link = scholar.content["recent_papers"][0]["detail_link"]
            
            return [scholar_page, paper_link]
        
        elif target_complexity == 3:
            # 路径模板: Scholar → Advisor → Paper (合作论文)
            scholar_page = random.choice(self.graph.page_index["scholar_homepage"])
            scholar = self.graph.get_page(scholar_page)
            
            advisor_page = scholar.content["links"]["advisor"]
            advisor = self.graph.get_page(advisor_page)
            
            # 找到学者与导师的合作论文
            coauthor_paper = self._find_coauthor_paper(scholar.content["name"], 
                                                       advisor.content["name"])
            
            return [scholar_page, advisor_page, coauthor_paper.page_id]
        
        elif target_complexity == 4:
            # 路径模板: Scholar → Paper → Coauthor → Institution
            scholar_page = random.choice(self.graph.page_index["scholar_homepage"])
            scholar = self.graph.get_page(scholar_page)
            
            paper_link = scholar.content["recent_papers"][0]["detail_link"]
            paper = self.graph.get_page(paper_link)
            
            # 选择第二作者
            coauthor_link = paper.content["authors"][1]["homepage_link"]
            coauthor = self.graph.get_page(coauthor_link)
            
            # 获取第二作者的机构
            institution_info = coauthor.content["current_position"]
            
            return [scholar_page, paper_link, coauthor_link, "institution_page"]
        
        elif target_complexity == 5:
            # 路径模板: Scholar → Advisor → Shared Paper → Venue → Another Paper in Same Venue
            # ... 更复杂的路径
            pass
        
        return []
    
    def _extract_constraints_from_path(self, path: List[str]) -> Tuple[Dict, str]:
        """
        从浏览路径提取约束条件和答案
        
        例如路径: [scholar_page, advisor_page, paper_page]
        
        提取:
        - 约束: 学者本科院校, 导师关系, 论文年份
        - 答案: 论文标题
        """
        constraints = {}
        answer = None
        
        # 访问路径上的每个页面,提取信息
        for i, page_id in enumerate(path):
            page = self.graph.get_page(page_id)
            
            if page.page_type == "scholar_homepage":
                # 从学者主页提取约束
                constraints["scholar_name"] = page.content["name"]
                if "education_summary" in page.content:
                    bachelor = [e for e in page.content["education_summary"] 
                               if e["degree"] == "B.S."]
                    if bachelor:
                        constraints["bachelor_university"] = bachelor[0]["university"]
            
            elif page.page_type == "paper_detail":
                # 从论文页提取约束和答案
                constraints["paper_year"] = page.content["year"]
                constraints["paper_venue"] = page.content["venue"]
                
                # 最后访问的论文页,其标题就是答案
                if i == len(path) - 1:
                    answer = page.content["title"]
        
        return constraints, answer
    
    def _generate_question_text(self, constraints: Dict, answer: str) -> str:
        """
        根据约束生成问题文本
        
        关键: 问题中只提供需要跳转才能获取的信息
        """
        
        # 构建问题模板
        template_parts = []
        
        if "scholar_name" in constraints:
            template_parts.append(f"{constraints['scholar_name']}")
        
        if "bachelor_university" in constraints:
            template_parts.append(f"(本科毕业于{constraints['bachelor_university']})")
        
        # ⚠️ 关键: 不直接提供导师名字,而是要求"与导师合作"
        # 这样必须先跳转到导师页面才能知道导师是谁
        template_parts.append("与他的博士导师")
        
        if "paper_year" in constraints:
            template_parts.append(f"在{constraints['paper_year']}年")
        
        if "paper_venue" in constraints:
            template_parts.append(f"发表在{constraints['paper_venue']}的")
        
        template_parts.append("合作论文标题是什么?")
        
        question = "".join(template_parts)
        
        return question
    
    def _verify_complexity(self, question: str, expected_path: List[str]) -> int:
        """
        验证问题的实际Browse Complexity
        
        方法: 模拟人类回答问题的过程,计算需要访问的页面数
        """
        
        # 简化实现: 直接返回路径长度
        return len(expected_path)
        
        # 完整实现需要:
        # 1. NLP解析问题,提取查询条件
        # 2. 模拟搜索和浏览过程
        # 3. 记录访问的页面数
```

### 示例: 生成Complexity=3的问题

```python
controller = BrowseComplexityController(web_graph)

result = controller.generate_question(target_complexity=3)

print(result)
# {
#     "question": "李明轩(本科毕业于清华大学)与他的博士导师在2020年发表在EMNLP的合作论文标题是什么?",
#     "answer": "Attention Mechanisms for Multi-hop Reasoning",
#     "browse_path": [
#         "page_001",  # 李明轩主页
#         "page_002",  # 张伟(导师)主页
#         "page_101"   # 论文详情页
#     ],
#     "complexity": 3
# }

# 验证浏览路径:
# Step 1: 访问page_001 (李明轩主页)
#         → 看到本科清华 ✓
#         → 看到advisor链接指向page_002
#         → 点击advisor链接

# Step 2: 访问page_002 (张伟主页)
#         → 确认张伟是李明轩的导师 ✓
#         → 需要找他们的合作论文
#         → 返回李明轩主页或访问论文列表

# Step 3: 访问page_101 (论文详情页)
#         → 看到2020年 ✓, EMNLP ✓
#         → 看到作者包含李明轩和张伟 ✓
#         → 答案: "Attention Mechanisms for Multi-hop Reasoning"

# Browse Complexity = 3 ✓
```

---

## 📊 问题类型设计

### 按Browse Complexity分类

| Complexity | 浏览路径模板 | 示例问题 | 难度 |
|-----------|------------|---------|------|
| **2** | Scholar → Paper | "李明轩(本科清华)2020年发表的第一篇论文标题?" | Easy |
| **3** | Scholar → Advisor → Paper | "李明轩(本科清华)与博士导师合作的2020年论文标题?" | Medium |
| **4** | Scholar → Paper → Coauthor → Institution | "李明轩2020年EMNLP论文的第二作者来自哪个机构?" | Medium-Hard |
| **5** | Scholar → Advisor → Paper → Venue → Related | "李明轩导师在同一会议上发表的另一篇论文?" | Hard |

### 路径模板库

```python
BROWSE_PATH_TEMPLATES = {
    "complexity_2": [
        {
            "name": "scholar_to_paper",
            "path": ["ScholarHome", "PaperDetail"],
            "question_template": "{scholar}({bachelor_uni})在{year}年发表的论文标题?",
            "answer_type": "paper_title"
        },
        {
            "name": "paper_to_author",
            "path": ["PaperDetail", "ScholarHome"],
            "question_template": "{year}年发表在{venue}的论文《{title}》的第一作者毕业于哪所大学?",
            "answer_type": "university"
        }
    ],
    
    "complexity_3": [
        {
            "name": "scholar_advisor_paper",
            "path": ["ScholarHome", "AdvisorPage", "PaperDetail"],
            "question_template": "{scholar}({bachelor_uni})与博士导师在{year}年合作的论文标题?",
            "answer_type": "paper_title",
            "constraints": {
                "scholar_name": "from_path[0]",
                "bachelor_uni": "from_path[0].education",
                "advisor_name": "from_path[1].name",  # ⚠️ 不在问题中直接给出
                "year": "from_path[2].year",
                "coauthors": "must_include_both"
            }
        },
        {
            "name": "paper_author_institution",
            "path": ["PaperDetail", "ScholarHome", "InstitutionPage"],
            "question_template": "{year}年{venue}会议上论文《{title}》的第二作者当前就职于哪个机构?",
            "answer_type": "institution"
        }
    ],
    
    "complexity_4": [
        {
            "name": "scholar_paper_coauthor_paper",
            "path": ["ScholarHome", "PaperDetail", "CoauthorHome", "AnotherPaperDetail"],
            "question_template": "{scholar}在{year1}年{venue1}论文的共同作者在{year2}年发表的另一篇论文标题?",
            "answer_type": "paper_title"
        },
        {
            "name": "advisor_student_paper_venue",
            "path": ["AdvisorPage", "StudentHome", "PaperDetail", "VenueProceedings"],
            "question_template": "MIT教授{advisor}的学生{student}在{venue}发表的论文中,引用数最高的是哪篇?",
            "answer_type": "paper_title"
        }
    ],
    
    "complexity_5": [
        {
            "name": "multi_hop_coauthor_network",
            "path": ["ScholarHome", "PaperDetail", "CoauthorHome", "AdvisorPage", "AnotherPaperDetail"],
            "question_template": "{scholar}与{coauthor}合作的论文中,{coauthor}的导师在同一年发表的论文标题?",
            "answer_type": "paper_title"
        }
    ]
}
```

---

## 🎯 生成示例对比

### ❌ v1.0 生成的问题 (不符合BrowseComp)

```
问题: "李明轩(本科毕业于清华大学,博士毕业于MIT,导师张伟教授)在2020年发表在EMNLP的论文标题是什么?"

约束数: 5个 ✓
Browse Complexity: 1 ✗

浏览路径:
Page 1: 访问李明轩的Google Scholar页面
        → 看到所有信息: 清华本科 ✓, MIT博士 ✓, 导师张伟 ✓
        → 看到2020年EMNLP论文 ✓
        → 直接得到答案

实际只需1个页面! 不符合BrowseComp要求
```

### ✅ v2.0 生成的问题 (符合BrowseComp)

```
问题: "李明轩(本科毕业于清华大学)与他在MIT的博士导师在2020年共同发表在EMNLP的论文标题是什么?"

约束数: 4个
Browse Complexity: 3 ✓

浏览路径:
Page 1: Google search "李明轩 清华 MIT"
        → 找到李明轩的个人主页
        
Page 2: 访问李明轩主页
        → 确认本科清华 ✓
        → 确认博士MIT ✓
        → 看到"Advisor: Prof. Wei Zhang"
        → 点击advisor链接

Page 3: 访问张伟教授主页
        → 确认是MIT教授 ✓
        → 点击"Publications"或返回李明轩页面查看论文

Page 4: 访问李明轩的论文列表
        → 筛选2020年的论文
        → 筛选EMNLP会议
        
Page 5: 访问候选论文详情页
        → 检查作者列表是否包含"Wei Zhang"
        → 找到答案: "Attention Mechanisms for Multi-hop Reasoning"

实际Browse Complexity = 3-5 (取决于搜索效率)
```

---

## 💾 实施调整

### 代码修改清单

| 文件 | v1.0 | v2.0 修改 | 状态 |
|------|------|----------|------|
| `scholar_profile.py` | ScholarProfile单对象 | **删除,替换为VirtualWebPage** | 🔄 重构 |
| `profile_generator.py` | 生成学者档案 | **改为生成网页图** | 🔄 重构 |
| **`web_graph.py`** | 不存在 | **新增: 虚拟网页图** | ✅ 新增 |
| **`browse_complexity_controller.py`** | 不存在 | **新增: 控制BC的问题生成** | ✅ 新增 |
| `constraint_validator.py` | 约束兼容性 | 保留,但调整为验证路径可达性 | 🔄 修改 |
| `uniqueness_guarantee.py` | 答案唯一性 | 保留 | ✅ 保留 |

### 新的实施计划

**Week 1: 虚拟网页图构建**

Day 1-2:
- [ ] 创建 `web_graph.py` (VirtualWebPage, VirtualWebGraph)
- [ ] 实现5种页面类型 (ScholarHome, PaperDetail, AdvisorPage, etc.)
- [ ] 单元测试: 页面创建和链接

Day 3-4:
- [ ] 实现 `web_graph_generator.py` (LLM批量生成网页图)
- [ ] 为1000个学者生成多页面结构
- [ ] 验证图的连通性和一致性

Day 5:
- [ ] 生成完整网页图 (约5000个页面)
- [ ] 保存到 `virtual_web_graph.json`
- [ ] 可视化验证 (随机抽样检查)

**Week 2: Browse Complexity控制的问题生成**

Day 1-2:
- [ ] 实现 `browse_complexity_controller.py`
- [ ] 实现路径模板 (Complexity 2-5)
- [ ] 实现路径设计算法

Day 3:
- [ ] 集成唯一性保证机制
- [ ] 集成LLM验证器

Day 4:
- [ ] 生成100个测试问题 (Complexity分布: 2/3/4 = 30/50/20)
- [ ] 验证每个问题的Browse Complexity

Day 5:
- [ ] 质量评估
- [ ] 人工抽样验证浏览路径
- [ ] 撰写实验报告

---

## 📈 评估指标调整

### v1.0 指标 (错误)

```python
metrics = {
    "平均约束数": 3.5,  # ✗ 不是BrowseComp的核心指标
    "答案唯一性": 0.85,  # ✓ 保留
    "多样性": 0.67,      # ✓ 保留
}
```

### v2.0 指标 (正确)

```python
metrics = {
    # === 核心指标 ===
    "平均Browse Complexity": 3.2,  # ⭐ 新增: BrowseComp核心指标
    "Browse Complexity分布": {
        "2": 0.25,
        "3": 0.45,
        "4": 0.25,
        "5": 0.05
    },
    
    # === 质量指标 ===
    "答案唯一性": 0.85,
    "问题多样性": 0.67,
    "路径可达性": 0.95,  # ⭐ 新增: 浏览路径是否可达
    
    # === 辅助指标 ===
    "平均约束数": 3.5,  # 保留,但不作为主要指标
    "生成成功率": 0.72,
}
```

### 人工评估维度

```python
human_evaluation = {
    "Browse Complexity验证": {
        "description": "人工模拟浏览,确认需要访问的页面数",
        "method": "给定问题,不看答案,记录浏览路径",
        "target": "人工测得BC与预期BC的误差 < 1"
    },
    
    "问题自然性": {
        "description": "问题表述是否自然,符合真实搜索场景",
        "scale": "1-5分",
        "target": "> 3.5"
    },
    
    "答案可搜索性": {
        "description": "答案是否可以通过网络搜索验证",
        "method": "真实Google搜索,记录是否找到",
        "target": "> 60% (虚拟数据,期望值较低)"
    }
}
```

---

## 🔚 总结

### 关键修订

1. **核心指标调整**: 从"约束数量"到"Browse Complexity"
2. **架构重构**: 从"学者档案"到"虚拟网页图"
3. **生成策略**: 强制跨实体跳转,禁止单页多属性

### v1.0 vs v2.0 对比

| 维度 | v1.0 | v2.0 |
|------|------|------|
| 数据结构 | ScholarProfile (单对象) | VirtualWebGraph (页面网络) |
| 信息分布 | 集中 (所有信息在一个对象) | 分散 (需要跳转才能获取) |
| 生成目标 | 多约束问题 | 多跳浏览问题 |
| 核心指标 | 约束数 (3-5) | Browse Complexity (3-5) |
| BrowseComp符合度 | ✗ 不符合 | ✓ 符合 |

### 下一步

等待确认后开始实施v2.0方案。

---

**文档版本**: v2.0  
**最后更新**: 2026-02-04  
**关键修订**: 完全重构,对齐BrowseComp真实定义
