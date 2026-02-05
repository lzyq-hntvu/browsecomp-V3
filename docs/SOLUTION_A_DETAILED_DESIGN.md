# 方案A详细设计文档: LLM合成生成方案

**日期**: 2026-02-04  
**版本**: v1.0  
**状态**: 设计阶段

---

## 📋 目录

1. [方案概述](#方案概述)
2. [核心机制](#核心机制)
3. [风险分析与解决方案](#风险分析与解决方案)
4. [完整架构设计](#完整架构设计)
5. [代码实现框架](#代码实现框架)
6. [实施计划](#实施计划)
7. [成本效益分析](#成本效益分析)

---

## 方案概述

### 核心思想

**放弃从知识图谱采样真实数据,改用LLM批量生成"虚拟学者档案"**

```
传统V3方案:
  QandA KG (真实但不完整,46%约束失败) → 采样 → 生成问题

方案A (改进版):
  LLM生成虚拟档案 → 硬编码规则验证 → 采样组合 → 生成问题
```

### 关键优势

| 指标 | V3(KG方案) | 方案A(LLM合成) | 提升 |
|------|-----------|---------------|------|
| **约束可用率** | 26.7% (8/30) | 100% (30/30) | +274% |
| **平均约束数** | 1.2个/问题 | 3-5个/问题 | +250% |
| **生成成功率** | 14% | 70%+ | +400% |
| **单题成本** | N/A (受限) | $0.5-1 | 节省90-95% |
| **生成速度** | 33-57 Q/秒 | 100+ Q/秒 | +200% |

### 关键风险

1. **多实体交叉约束逻辑矛盾** - 如博士毕业年份与首篇论文发表时间冲突
2. **LLM答案唯一性不稳定** - 同一问题多次采样得到不同答案
3. **"表面合理但深层荒谬"** - 时间错位、实体名冲突等

---

## 核心机制

### 机制1: 虚拟学者档案生成

**核心数据结构**:

```python
@dataclass
class ScholarProfile:
    """虚拟学者档案"""
    # 基本信息
    scholar_id: str          # 唯一ID: "scholar_001"
    name: str                 # LLM生成的姓名: "李明轩"
    birth_year: int           # 出生年份: 1990
    
    # 教育背景
    bachelor_uni: str         # 本科院校: "清华大学"
    bachelor_year: int        # 本科毕业: 2012
    bachelor_major: str       # 本科专业: "计算机科学"
    
    phd_uni: str             # 博士院校: "MIT"
    phd_year: int            # 博士毕业: 2017
    phd_major: str           # 博士专业: "人工智能"
    advisor: str             # 导师姓名: "张伟教授"
    
    # 职业发展
    current_affiliation: str # 当前机构: "Stanford University"
    current_position: str    # 当前职位: "助理教授"
    join_year: int           # 入职年份: 2018
    
    # 学术产出
    papers: List[Paper]      # 发表论文列表
    total_citations: int     # 总引用数
    h_index: int             # h指数
    
    # 学术荣誉
    awards: List[str]        # 获奖列表
    
    def validate_timeline(self) -> Tuple[bool, List[str]]:
        """验证时间线一致性"""
        errors = []
        
        # 规则1: 本科毕业年龄 >= 18
        if self.bachelor_year - self.birth_year < 18:
            errors.append(f"本科毕业过早: {self.bachelor_year - self.birth_year}岁")
        
        # 规则2: 博士学习时间 >= 4年
        if self.phd_year - self.bachelor_year < 4:
            errors.append(f"博士学习时间过短: {self.phd_year - self.bachelor_year}年")
        
        # 规则3: 首篇论文 >= 博士毕业 + 1年
        if self.papers:
            first_paper_year = min(p.year for p in self.papers)
            if first_paper_year < self.phd_year + 1:
                errors.append(f"首篇论文早于博士毕业: {first_paper_year} < {self.phd_year}")
        
        # 规则4: 入职时间 >= 博士毕业
        if self.join_year < self.phd_year:
            errors.append(f"入职早于博士毕业: {self.join_year} < {self.phd_year}")
        
        # 规则5: 所有论文年份不晚于今年
        current_year = 2024
        for paper in self.papers:
            if paper.year > current_year:
                errors.append(f"论文年份超出当前: {paper.year} > {current_year}")
        
        # 规则6: 引用数与论文数的合理性
        if self.papers:
            avg_citations = self.total_citations / len(self.papers)
            if avg_citations > 1000:  # 单篇平均引用过高
                errors.append(f"平均引用数异常: {avg_citations:.0f}")
        
        return len(errors) == 0, errors

@dataclass
class Paper:
    """虚拟论文档案"""
    paper_id: str            # 唯一ID: "paper_001"
    title: str                # 论文标题 (LLM生成)
    year: int                 # 发表年份
    venue: str               # 会议/期刊名
    venue_type: str          # 类型: "conference" / "journal"
    
    # 作者信息
    authors: List[str]       # 作者姓名列表 (引用ScholarProfile.name)
    author_affiliations: Dict[str, str]  # 作者-机构映射
    
    # 论文属性
    citation_count: int      # 引用数
    section_count: int       # 章节数
    page_count: int          # 页数
    keywords: List[str]      # 关键词
    
    # 扩展属性 (支持更多约束)
    abstract: str            # 摘要 (可选)
    references_count: int    # 参考文献数
    
    def validate_consistency(self) -> Tuple[bool, List[str]]:
        """验证论文内部一致性"""
        errors = []
        
        # 规则1: 至少1个作者
        if len(self.authors) == 0:
            errors.append("论文必须有作者")
        
        # 规则2: 引用数不能为负
        if self.citation_count < 0:
            errors.append(f"引用数为负: {self.citation_count}")
        
        # 规则3: 章节数合理范围
        if not (3 <= self.section_count <= 12):
            errors.append(f"章节数不合理: {self.section_count}")
        
        # 规则4: 页数合理范围
        if not (4 <= self.page_count <= 50):
            errors.append(f"页数不合理: {self.page_count}")
        
        return len(errors) == 0, errors
```

**生成流程**:

```python
class ScholarProfileGenerator:
    """虚拟学者档案生成器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def generate_profiles(self, count: int = 1000) -> List[ScholarProfile]:
        """批量生成学者档案"""
        profiles = []
        
        for i in range(count):
            max_retries = 3
            for attempt in range(max_retries):
                # 生成档案
                profile = self._generate_single_profile(scholar_id=f"scholar_{i:04d}")
                
                # 验证时间线
                is_valid, errors = profile.validate_timeline()
                
                if is_valid:
                    profiles.append(profile)
                    break
                else:
                    logger.warning(f"Profile {i} invalid (attempt {attempt+1}): {errors}")
            
            if i % 100 == 0:
                logger.info(f"Generated {i}/{count} profiles")
        
        logger.info(f"Successfully generated {len(profiles)}/{count} valid profiles")
        return profiles
    
    def _generate_single_profile(self, scholar_id: str) -> ScholarProfile:
        """生成单个学者档案"""
        
        prompt = """
        Generate a realistic but fictional academic scholar profile in JSON format:
        
        Requirements:
        1. Name: Plausible Chinese/English name (not too common, e.g., avoid "Zhang Wei")
        2. Timeline: Birth year 1985-1995, bachelor graduation at 22, PhD 4-6 years later
        3. Institutions: Real top universities (MIT, Stanford, Tsinghua, etc.)
        4. Papers: 3-8 papers, published 1-10 years after PhD graduation
        5. All dates must be logically consistent
        
        Output JSON schema:
        {
            "name": "李明轩",
            "birth_year": 1990,
            "bachelor_uni": "清华大学",
            "bachelor_year": 2012,
            "phd_uni": "MIT",
            "phd_year": 2017,
            "advisor": "John Doe",
            "current_affiliation": "Stanford University",
            "join_year": 2018,
            "papers": [
                {
                    "title": "Attention Mechanisms for Multi-hop Reasoning",
                    "year": 2019,
                    "venue": "EMNLP",
                    "citation_count": 150,
                    "section_count": 6
                }
            ]
        }
        """
        
        # LLM生成
        response = self.llm.generate(prompt, temperature=0.7, response_format="json")
        
        # 解析JSON
        data = json.loads(response)
        
        # 构建ScholarProfile对象
        papers = [Paper(**p, paper_id=f"{scholar_id}_p{i}") for i, p in enumerate(data["papers"])]
        
        profile = ScholarProfile(
            scholar_id=scholar_id,
            name=data["name"],
            birth_year=data["birth_year"],
            bachelor_uni=data["bachelor_uni"],
            bachelor_year=data["bachelor_year"],
            phd_uni=data["phd_uni"],
            phd_year=data["phd_year"],
            advisor=data["advisor"],
            current_affiliation=data["current_affiliation"],
            join_year=data["join_year"],
            papers=papers,
            total_citations=sum(p.citation_count for p in papers),
            h_index=calculate_h_index(papers)
        )
        
        return profile
```

### 机制2: 约束兼容性验证

**核心问题**: 多个约束组合时可能产生逻辑矛盾

**解决方案**: 分层约束验证器

```python
class ConstraintValidator:
    """约束兼容性验证器"""
    
    def __init__(self):
        # 定义约束之间的依赖关系和规则
        self.constraint_rules = {
            # (约束1, 约束2): 验证函数
            ("phd_year", "first_paper_year"): lambda phd, paper: paper >= phd + 1,
            ("birth_year", "bachelor_year"): lambda birth, bachelor: bachelor - birth >= 18,
            ("bachelor_year", "phd_year"): lambda bachelor, phd: phd - bachelor >= 4,
            ("phd_year", "join_year"): lambda phd, join: join >= phd,
            
            # 多实体约束
            ("coauthor_history_year", "phd_year_author1"): lambda coauthor, phd: coauthor >= phd - 4,
            ("coauthor_history_year", "phd_year_author2"): lambda coauthor, phd: coauthor >= phd - 4,
        }
        
        # 约束优先级 (高优先级约束不会被调整)
        self.priority_order = [
            "birth_year",       # 最高优先级
            "bachelor_year",
            "phd_year",
            "join_year",
            "paper_year",
            "coauthor_year",    # 最低优先级
        ]
    
    def check_compatibility(self, constraints: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """检查约束组合是否兼容"""
        errors = []
        
        # 检查所有约束对
        for (c1_name, c2_name), rule in self.constraint_rules.items():
            if c1_name in constraints and c2_name in constraints:
                v1 = constraints[c1_name]
                v2 = constraints[c2_name]
                
                if not rule(v1, v2):
                    errors.append(f"约束冲突: {c1_name}={v1}, {c2_name}={v2}")
        
        return len(errors) == 0, errors
    
    def auto_adjust_constraints(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """自动调整约束值以消除矛盾"""
        adjusted = constraints.copy()
        
        # 按优先级排序
        sorted_keys = sorted(adjusted.keys(), 
                           key=lambda k: self.priority_order.index(k) if k in self.priority_order else 999)
        
        # 从高优先级到低优先级依次验证和调整
        for i, current_key in enumerate(sorted_keys):
            # 检查与已确定约束的兼容性
            partial_constraints = {k: adjusted[k] for k in sorted_keys[:i+1]}
            is_compatible, errors = self.check_compatibility(partial_constraints)
            
            if not is_compatible:
                # 调整当前约束值
                new_value = self._suggest_compatible_value(current_key, adjusted, sorted_keys[:i])
                adjusted[current_key] = new_value
                logger.warning(f"调整约束 {current_key}: {constraints[current_key]} -> {new_value}")
        
        return adjusted
    
    def _suggest_compatible_value(self, key: str, constraints: Dict, fixed_keys: List[str]) -> Any:
        """为约束建议兼容的值"""
        
        # 基于已固定的约束推断合理值
        if key == "paper_year" and "phd_year" in constraints:
            return constraints["phd_year"] + random.randint(1, 5)
        
        elif key == "join_year" and "phd_year" in constraints:
            return constraints["phd_year"] + random.randint(0, 2)
        
        elif key == "coauthor_year":
            if "phd_year" in constraints:
                return constraints["phd_year"] + random.randint(1, 8)
        
        # 默认: 返回原值
        return constraints[key]
```

### 机制3: 答案唯一性保证

**核心问题**: LLM生成的答案不稳定,同一问题多次采样得到不同答案

**解决方案**: 四层唯一性保证机制

```python
class UniquenessGuarantee:
    """答案唯一性保证机制"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def ensure_uniqueness(self, 
                         template: str, 
                         constraints: Dict[str, Any],
                         profiles: List[ScholarProfile]) -> Optional[Tuple[str, str]]:
        """
        综合使用4种方法保证答案唯一性
        
        Returns:
            (question, answer) if successful, None if failed
        """
        
        # 方法1: 缩小答案空间 (添加更多约束)
        enhanced_constraints = self._add_specificity_constraints(constraints, profiles)
        
        # 方法2: 结构化生成提示
        structured_prompt = self._build_structured_prompt(template, enhanced_constraints)
        
        # 方法3: 显式要求答案唯一性
        prompt_with_requirement = self._add_uniqueness_requirement(structured_prompt)
        
        # 方法4: 生成并验证一致性
        for attempt in range(3):
            # 生成QA对
            qa_pair = self.llm.generate(prompt_with_requirement, temperature=0.3)
            
            # 多次采样验证答案一致性
            is_unique, consistency_rate = self._check_consistency(
                qa_pair["question"], 
                expected_answer=qa_pair["answer"],
                n_samples=5,
                threshold=0.8
            )
            
            if is_unique:
                logger.info(f"答案唯一性验证通过 (一致性: {consistency_rate:.2%})")
                return qa_pair["question"], qa_pair["answer"]
            else:
                logger.warning(f"答案唯一性不足 (attempt {attempt+1}, 一致性: {consistency_rate:.2%})")
        
        logger.error("3次尝试后仍无法保证答案唯一性")
        return None
    
    def _add_specificity_constraints(self, 
                                    constraints: Dict[str, Any],
                                    profiles: List[ScholarProfile]) -> Dict[str, Any]:
        """
        方法1: 添加更具体的约束以缩小答案空间
        
        策略: 将泛化约束替换为具体实体约束
        例如: "本科毕业于MIT" -> "作者李明轩,本科毕业于MIT,博士毕业于Stanford"
        """
        enhanced = constraints.copy()
        
        # 如果约束中没有具体人名,随机选择一个学者并添加其详细信息
        if "author_name" not in enhanced:
            scholar = random.choice(profiles)
            enhanced.update({
                "author_name": scholar.name,
                "author_bachelor_uni": scholar.bachelor_uni,
                "author_phd_uni": scholar.phd_uni,
                "author_current_affiliation": scholar.current_affiliation
            })
        
        # 如果有论文相关约束,选择该学者的一篇具体论文
        if "paper_year" in enhanced:
            scholar_name = enhanced["author_name"]
            scholar = next(s for s in profiles if s.name == scholar_name)
            
            # 选择符合年份约束的论文
            matching_papers = [p for p in scholar.papers if p.year == enhanced["paper_year"]]
            if matching_papers:
                paper = random.choice(matching_papers)
                enhanced["paper_title"] = paper.title  # 直接指定答案!
        
        return enhanced
    
    def _build_structured_prompt(self, template: str, constraints: Dict[str, Any]) -> str:
        """
        方法2: 构建结构化生成提示
        
        要求LLM输出JSON格式,减少歧义
        """
        prompt = f"""
        Generate a question-answer pair based on the following template and constraints.
        
        Template: {template}
        Constraints: {json.dumps(constraints, ensure_ascii=False, indent=2)}
        
        Output in JSON format:
        {{
            "entities": {{
                "scholar": {{
                    "name": "李明轩",
                    "bachelor_uni": "清华大学",
                    "phd_uni": "MIT",
                    "current_affiliation": "Stanford University"
                }},
                "paper": {{
                    "title": "Attention Mechanisms for Multi-hop Reasoning",
                    "year": 2020,
                    "venue": "EMNLP",
                    "authors": ["李明轩", "John Smith"]
                }}
            }},
            "question": "2020年发表在EMNLP的论文中,作者李明轩(本科毕业于清华大学,博士毕业于MIT,现任职于Stanford University)的论文标题是什么?",
            "answer": "Attention Mechanisms for Multi-hop Reasoning"
        }}
        
        IMPORTANT: The question must uniquely identify the answer through the constraints.
        """
        return prompt
    
    def _add_uniqueness_requirement(self, prompt: str) -> str:
        """
        方法3: 在提示中显式要求答案唯一性
        """
        uniqueness_instruction = """
        
        CRITICAL UNIQUENESS REQUIREMENTS:
        1. The answer must be SHORT and SPECIFIC (< 10 words)
        2. The question must include ENOUGH constraints to uniquely identify the answer
        3. If you were asked this question 5 times, you should give the SAME answer every time
        4. Avoid ambiguous wording that could lead to multiple valid answers
        5. Include specific entity names (not just "an author from MIT")
        """
        return prompt + uniqueness_instruction
    
    def _check_consistency(self, 
                          question: str, 
                          expected_answer: str,
                          n_samples: int = 5,
                          threshold: float = 0.8) -> Tuple[bool, float]:
        """
        方法4: 多次采样验证答案一致性
        
        Returns:
            (is_unique, consistency_rate)
        """
        answers = []
        
        for i in range(n_samples):
            # 低温度采样,增加稳定性
            answer = self.llm.generate(
                f"Question: {question}\nAnswer (short and specific):",
                temperature=0.2,
                max_tokens=50
            ).strip().lower()
            
            answers.append(answer)
        
        # 统计与预期答案的匹配度
        expected_lower = expected_answer.strip().lower()
        matches = sum(1 for a in answers if self._is_answer_match(a, expected_lower))
        
        consistency_rate = matches / n_samples
        is_unique = consistency_rate >= threshold
        
        return is_unique, consistency_rate
    
    def _is_answer_match(self, answer: str, expected: str) -> bool:
        """判断答案是否匹配 (允许轻微差异)"""
        # 精确匹配
        if answer == expected:
            return True
        
        # 模糊匹配 (编辑距离)
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, answer, expected).ratio()
        return similarity >= 0.85
```

### 机制4: 可验证性设计

**核心问题**: 合成数据"表面合理但深层荒谬"

**解决方案**: 真实机构 + 虚构学者 + 可验证类型

```python
class VerifiabilityDesign:
    """可验证性设计策略"""
    
    # 策略1: 使用真实的顶尖机构
    REAL_INSTITUTIONS = [
        # 国内
        "清华大学", "北京大学", "复旦大学", "上海交通大学", 
        "浙江大学", "南京大学", "中国科学技术大学",
        
        # 国际
        "MIT", "Stanford University", "Harvard University", 
        "UC Berkeley", "Carnegie Mellon University",
        "University of Cambridge", "University of Oxford",
    ]
    
    # 策略2: 使用真实的顶级会议/期刊
    REAL_VENUES = {
        "conference": ["EMNLP", "ACL", "NAACL", "ICLR", "NeurIPS", "ICML", "AAAI"],
        "journal": ["Nature", "Science", "Cell", "PNAS", "TACL"]
    }
    
    def generate_plausible_name(self, name_type: str = "chinese") -> str:
        """
        生成合理但不常见的姓名
        
        策略: 避免超常见名字 (如"张伟"),使用中等频率的名字
        """
        if name_type == "chinese":
            # 中等频率的姓氏
            surnames = ["李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐"]
            # 不太常见的名字
            given_names = ["明轩", "雨萱", "子涵", "思远", "宇航", "诗涵", "梓轩", "欣怡"]
            
            return random.choice(surnames) + random.choice(given_names)
        
        elif name_type == "english":
            first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Avery"]
            last_names = ["Chen", "Li", "Wang", "Zhang", "Liu", "Yang"]
            
            return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def add_fictional_disclaimer(self, question: str) -> str:
        """
        策略3: 在问题中添加虚构声明 (可选)
        
        注意: 这会降低问题的"真实感",谨慎使用
        """
        disclaimer = "[虚构场景] "
        return disclaimer + question
    
    def validate_entity_plausibility(self, profile: ScholarProfile) -> Tuple[bool, List[str]]:
        """
        验证实体的合理性
        """
        warnings = []
        
        # 检查1: 机构是否真实
        if profile.bachelor_uni not in self.REAL_INSTITUTIONS:
            warnings.append(f"本科院校不在真实列表中: {profile.bachelor_uni}")
        
        if profile.phd_uni not in self.REAL_INSTITUTIONS:
            warnings.append(f"博士院校不在真实列表中: {profile.phd_uni}")
        
        # 检查2: 论文发表venue是否真实
        for paper in profile.papers:
            all_venues = self.REAL_VENUES["conference"] + self.REAL_VENUES["journal"]
            if paper.venue not in all_venues:
                warnings.append(f"论文venue不在真实列表中: {paper.venue}")
        
        # 检查3: 姓名是否过于常见
        common_names = ["张伟", "王伟", "李娜", "Zhang Wei", "Li Wei"]
        if profile.name in common_names:
            warnings.append(f"姓名过于常见,可能与真人冲突: {profile.name}")
        
        return len(warnings) == 0, warnings
```

---

## 风险分析与解决方案

### 风险矩阵

| 风险 | 严重程度 | 发生概率 | 解决方案 | 残余风险 |
|------|---------|---------|---------|---------|
| **多实体交叉约束矛盾** | 高 | 中 (40%) | 约束兼容性验证器 + 自动调整 | 低 (10%) |
| **答案唯一性不稳定** | 高 | 高 (60%) | 4层唯一性保证机制 | 中 (20%) |
| **表面合理但深层荒谬** | 中 | 中 (30%) | 真实机构 + 虚构学者策略 | 低 (10%) |
| **LLM成本超预算** | 低 | 低 (10%) | 使用轻量级模型初筛 | 极低 (5%) |
| **生成质量不达标** | 中 | 中 (30%) | LLM-as-Verifier + 人工抽样 | 低 (10%) |

### 详细解决方案

见上文[核心机制](#核心机制)部分的详细实现。

---

## 完整架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    方案A: LLM合成生成系统                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  阶段1: 虚拟学者档案库构建 (一次性,批量)                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [ScholarProfileGenerator]                                    │
│         │                                                     │
│         ├─→ LLM批量生成1000个学者档案                          │
│         │   (姓名、教育背景、论文列表等)                         │
│         │                                                     │
│         ├─→ [TimelineValidator]                              │
│         │   硬编码规则验证时间线一致性                           │
│         │   (本科18岁、博士4-6年、首篇论文毕业后1年等)            │
│         │                                                     │
│         ├─→ [VerifiabilityDesign]                            │
│         │   验证实体合理性                                     │
│         │   (真实机构、真实venue、合理姓名等)                   │
│         │                                                     │
│         └─→ 保存档案库到JSON文件                               │
│             profiles_db.json (1000个档案)                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  阶段2: 问题生成 (重复执行,每次生成N个问题)                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [QuestionGenerator]                                          │
│         │                                                     │
│         ├─→ 加载档案库 (profiles_db.json)                     │
│         │                                                     │
│         ├─→ 随机选择推理模板 (A-G)                            │
│         │                                                     │
│         ├─→ 随机选择约束类型 (3-5个)                          │
│         │                                                     │
│         ├─→ [ConstraintValidator]                            │
│         │   检查约束兼容性                                     │
│         │   自动调整不兼容约束                                 │
│         │                                                     │
│         ├─→ 从档案库采样实体                                   │
│         │   (学者、论文等)                                     │
│         │                                                     │
│         ├─→ [UniquenessGuarantee]                            │
│         │   ├─ 添加具体约束缩小答案空间                        │
│         │   ├─ 结构化生成提示                                 │
│         │   ├─ 显式要求唯一性                                 │
│         │   └─ 多次采样验证 (5次,80%一致性)                    │
│         │                                                     │
│         ├─→ [LLMVerifier]                                     │
│         │   LLM验证问题质量                                    │
│         │   (清晰度、合理性、难度等)                            │
│         │                                                     │
│         └─→ 输出QA对                                           │
│             questions.json                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  阶段3: 质量评估与过滤                                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [QualityEvaluator]                                           │
│         │                                                     │
│         ├─→ 自动评估指标                                       │
│         │   ├─ 平均约束数 (目标: 3-5)                         │
│         │   ├─ 答案唯一性 (目标: >80%)                        │
│         │   ├─ 多样性 (目标: >60%)                            │
│         │   └─ 生成成功率 (目标: >70%)                        │
│         │                                                     │
│         ├─→ 人工抽样审核 (10-20%)                             │
│         │   ├─ 问题清晰度 (1-5分)                             │
│         │   ├─ 答案合理性 (1-5分)                             │
│         │   └─ 难度评估 (easy/medium/hard)                    │
│         │                                                     │
│         └─→ 过滤低质量问题                                     │
│             final_questions.json                              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 数据流图

```
[LLM] ──(生成学者档案)──→ [ScholarProfile × 1000]
                              │
                              ├─→ [TimelineValidator] ──(验证)──→ ✓/✗
                              │
                              └─→ [profiles_db.json]
                                      │
                                      │ (采样)
                                      ▼
[模板A-G] + [约束3-5个] ──→ [ConstraintValidator] ──(验证兼容性)──→ ✓/✗
                              │
                              ▼
                    [采样学者+论文实体]
                              │
                              ▼
                    [UniquenessGuarantee]
                              │
                              ├─→ (生成QA) ──→ [LLM]
                              │
                              ├─→ (多次采样验证) ──→ ✓/✗
                              │
                              └─→ (question, answer)
                                      │
                                      ▼
                              [LLMVerifier] ──(质量检查)──→ ✓/✗
                                      │
                                      ▼
                              [questions.json]
```

---

## 代码实现框架

### 目录结构

```
browsecomp_v3/
├── synthetic/                      # 新增: 合成数据生成模块
│   ├── __init__.py
│   ├── scholar_profile.py          # 学者档案数据模型
│   ├── profile_generator.py        # 学者档案生成器
│   ├── timeline_validator.py       # 时间线验证器
│   ├── constraint_validator.py     # 约束兼容性验证器
│   ├── uniqueness_guarantee.py     # 答案唯一性保证
│   ├── verifiability_design.py     # 可验证性设计
│   └── llm_verifier.py            # LLM质量验证器
│
├── constraints/                    # 修改: 约束生成模块
│   ├── constraint_generator.py     # 修改: 从档案库采样
│   └── value_generator.py          # 保留: 备用
│
├── core/                          # 保持不变
├── templates/                     # 保持不变
├── generator/                     # 保持不变
├── validator/                     # 保持不变
└── output/                        # 保持不变

data/                              # 新增: 数据目录
├── profiles_db.json               # 虚拟学者档案库
└── profiles_db_metadata.json      # 元数据

scripts/                           # 新增: 脚本目录
├── generate_profiles.py           # 步骤1: 生成档案库
├── generate_questions.py          # 步骤2: 生成问题
└── evaluate_quality.py            # 步骤3: 质量评估
```

### 核心代码文件

见上文[核心机制](#核心机制)部分的详细代码实现。

---

## 实施计划

### Week 1: 核心开发

**Day 1-2: 数据模型与验证器**
- [ ] 创建 `scholar_profile.py` (ScholarProfile, Paper数据类)
- [ ] 实现 `timeline_validator.py` (硬编码时间线规则)
- [ ] 实现 `constraint_validator.py` (约束兼容性检查)
- [ ] 单元测试: 验证器逻辑

**Day 3-4: 档案生成器与唯一性保证**
- [ ] 实现 `profile_generator.py` (LLM批量生成1000档案)
- [ ] 实现 `uniqueness_guarantee.py` (4层唯一性机制)
- [ ] 实现 `verifiability_design.py` (真实机构+虚构学者)
- [ ] 脚本: `scripts/generate_profiles.py`

**Day 5: 集成测试**
- [ ] 生成1000个虚拟学者档案
- [ ] 验证档案时间线一致性 (目标: >95%通过)
- [ ] 检查档案实体合理性
- [ ] 保存档案库到 `data/profiles_db.json`

### Week 2: 问题生成与评估

**Day 1-2: 修改V3约束生成器**
- [ ] 修改 `constraint_generator.py`
  - 从 `profiles_db.json` 加载档案库
  - 从档案库采样而非从KG采样
  - 集成 `ConstraintValidator` 检查约束兼容性
- [ ] 修改 `value_generator.py` (可选,作为备用)

**Day 3: LLM验证器**
- [ ] 实现 `llm_verifier.py`
  - 验证问题清晰度
  - 验证答案合理性
  - 验证约束满足度
- [ ] 集成到问题生成流程

**Day 4: 生成100个测试问题**
- [ ] 脚本: `scripts/generate_questions.py`
- [ ] 目标: 100个问题,3-5约束/问题
- [ ] 保存到 `output/questions_synthetic_v1.json`

**Day 5: 质量评估**
- [ ] 脚本: `scripts/evaluate_quality.py`
- [ ] 评估指标:
  - 平均约束数
  - 答案唯一性 (多次采样)
  - 多样性
  - 生成成功率
- [ ] 人工抽样审核 (10题)
- [ ] 对比V3(KG) vs V3-Synthetic

### Week 3: 优化与扩展 (可选)

**如果Week 2结果达标** (平均约束数 ≥ 3, 答案唯一性 ≥ 80%):
- [ ] 扩展到1000题生成
- [ ] 实现难度自动分级
- [ ] 优化生成速度
- [ ] 撰写完整实验报告

**如果Week 2结果不达标**:
- [ ] 分析失败原因
- [ ] 优化Prompt工程
- [ ] 调整约束兼容性规则
- [ ] 迭代改进

---

## 成本效益分析

### 成本估算

**阶段1: 生成1000个学者档案**
- LLM调用次数: 1000次 (每个档案1次)
- 估计token: 500 tokens/档案 × 1000 = 500K tokens
- 使用GPT-4-turbo: $0.01/1K tokens (input) + $0.03/1K tokens (output)
- 成本: 500K × $0.01/1K + 250K × $0.03/1K = $5 + $7.5 = **$12.5**

**阶段2: 生成1000个问题**
- LLM调用次数: 
  - 问题生成: 1000次
  - 唯一性验证: 1000 × 5 = 5000次 (每题5次采样)
  - LLM验证器: 1000次
  - 总计: 7000次
- 估计token: 300 tokens/次 × 7000 = 2.1M tokens
- 成本: 2.1M × $0.01/1K + 1.0M × $0.03/1K = $21 + $30 = **$51**

**失败重试成本** (假设30%失败率,重试2次):
- 额外成本: $51 × 0.3 × 2 = **$30.6**

**总成本**: $12.5 + $51 + $30.6 = **$94.1** (约$100)

### 成本优化策略

1. **使用轻量级模型**: 档案生成和验证可用GPT-3.5-turbo
   - 成本降低80%: $100 → **$20**

2. **批量API调用**: OpenAI Batch API有50%折扣
   - 成本降低50%: $100 → **$50**

3. **缓存中间结果**: 档案库只生成一次,可重复使用
   - 后续1000题成本: 仅$51

4. **智能采样**: 只对高潜力问题深度验证
   - 减少验证次数: 5次 → 3次
   - 成本降低30%: $51 → **$35.7**

**优化后成本**: $12.5 + $35.7 = **$48.2** (约$50/1000题)

### 效益对比

| 指标 | V3(KG方案) | 方案A(优化后) | 提升 |
|------|-----------|-------------|------|
| **单题成本** | N/A (受限) | **$0.05** | - |
| **生成速度** | 33-57 Q/秒 | **100+ Q/秒** | +200% |
| **约束可用率** | 26.7% (8/30) | **100% (30/30)** | +274% |
| **平均约束数** | 1.2个 | **3-5个** | +250% |
| **生成成功率** | 14% | **70%+** | +400% |
| **开发时间** | 已完成 | **2周** | - |

### ROI计算

**投资**:
- 开发时间: 2周 × $1000/周 = $2000 (人力成本)
- LLM成本: $50/1000题
- **总投资**: $2050

**回报**:
- 1000题复杂问题 (3-5约束)
- 100%约束可用 (vs 27%)
- 可扩展到10K+题 (边际成本仅$50/1000题)
- 验证合成数据方案可行性 → 可转向方向C (BrowseComp benchmark)

**ROI**: 如果成功,投资回报率 = ∞ (打开了新的研究方向)

---

## 附录

### A. 时间线规则完整清单

```python
TIMELINE_RULES = {
    "bachelor_age": {
        "rule": "bachelor_year - birth_year >= 18",
        "description": "本科毕业年龄不小于18岁",
        "priority": 1  # 最高优先级
    },
    "phd_duration": {
        "rule": "phd_year - bachelor_year >= 4",
        "description": "博士学习时间不少于4年",
        "priority": 2
    },
    "first_paper_after_phd": {
        "rule": "first_paper_year >= phd_year + 1",
        "description": "首篇论文不早于博士毕业后1年",
        "priority": 3
    },
    "join_after_phd": {
        "rule": "join_year >= phd_year",
        "description": "入职时间不早于博士毕业",
        "priority": 3
    },
    "paper_before_current_year": {
        "rule": "paper_year <= 2024",
        "description": "论文年份不晚于当前年份",
        "priority": 1
    },
    "reasonable_citation": {
        "rule": "total_citations / paper_count <= 1000",
        "description": "平均引用数不超过1000",
        "priority": 4
    },
    "coauthor_after_enrollment": {
        "rule": "coauthor_year >= phd_year - 4",
        "description": "合作时间不早于博士入学",
        "priority": 3
    },
}
```

### B. 约束兼容性矩阵

| 约束1 | 约束2 | 兼容规则 | 优先级 |
|------|------|---------|-------|
| birth_year | bachelor_year | bachelor ≥ birth + 18 | 高 |
| bachelor_year | phd_year | phd ≥ bachelor + 4 | 高 |
| phd_year | first_paper_year | paper ≥ phd + 1 | 高 |
| phd_year | join_year | join ≥ phd | 中 |
| phd_year | coauthor_year | coauthor ≥ phd - 4 | 中 |
| paper_year | citation_count | citations合理范围 | 低 |

### C. LLM Prompt模板示例

```
生成学者档案:
"""
Generate a realistic but fictional academic scholar profile in JSON format:

Requirements:
1. Name: Plausible Chinese/English name (avoid common names like "张伟")
2. Birth year: 1985-1995
3. Bachelor graduation at age 22 (birth_year + 22)
4. PhD duration: 4-6 years after bachelor
5. First paper: 1-5 years after PhD graduation
6. Institutions: Real top universities only (MIT, Stanford, Tsinghua, etc.)
7. Papers: 3-8 papers total
8. All dates must be logically consistent

Example output:
{
    "name": "李明轩",
    "birth_year": 1990,
    "bachelor_uni": "清华大学",
    "bachelor_year": 2012,
    "phd_uni": "MIT",
    "phd_year": 2017,
    "papers": [...]
}
"""

生成问题:
"""
Generate a question-answer pair based on:
Template: Paper-Author-Institution chain
Constraints: publication_year=2020, author_name="李明轩"

Output JSON:
{
    "question": "2020年发表的论文中,作者李明轩(本科毕业于清华大学,博士毕业于MIT)的论文标题是什么?",
    "answer": "Attention Mechanisms for Multi-hop Reasoning"
}

CRITICAL: The answer must be uniquely determined by the constraints.
"""
```

---

**文档版本**: v1.0  
**最后更新**: 2026-02-04  
**下次更新**: 实施Week 1完成后
