# 复杂度分析与开发路线图

**文档版本**: v1.0
**更新日期**: 2026-02-01
**作者**: Browsecomp-V3 开发团队

---

## 📊 当前系统复杂度分析

### 测试结果 (2000个问题样本)

| 指标 | 当前值 | 说明 |
|------|--------|------|
| **难度分布** | 100% easy | 无medium/hard问题 |
| **约束数量** | 100% 单约束 | 仅1个约束/问题 |
| **推理跳数** | 100% 单跳 | 仅1跳推理 |

### 生成性能测试

| 规模 | 成功生成 | 耗时 | 成功率 | 唯一问题 | 多样性率 |
|------|----------|------|--------|----------|----------|
| 100 | 100个 | 0.78秒 | 47.6% | 36个 | 36.0% |
| 500 | 500个 | 2.22秒 | 52.4% | 70个 | 14.0% |
| 1000 | 1000个 | 4.17秒 | 52.0% | 93个 | 9.3% |
| 2000 | 2000个 | 7.76秒 | 51.7% | 110个 | 5.5% |

**关键发现**:
- 生成速度: ~128 问题/秒
- 成功率稳定在 50-52%
- 多样性随数量增加而下降
- 理论上限: 约1000-1500个唯一问题

---

## 🆚 与Browsecomp原版对比

### 复杂度指标对比

| 指标 | Browsecomp-V3 | Browsecomp原版 | 差距 |
|------|---------------|----------------|------|
| **约束数量** | 1个 | **3-6个** | **3-6倍** |
| **推理跳数** | 1跳 | **3-7跳** | **3-7倍** |
| **约束类型** | 4种 | **30+种** | **7-8倍** |
| **推理模板** | 4种生效 | **7种全支持** | **1.75倍** |
| **难度等级** | easy only | easy/medium/hard | **缺失2级** |

### 典型问题对比

#### Browsecomp原版示例

```
问题: "A paper published in 2022 was co-authored by 14 researchers.
       The first author, Kejun Bu, was affiliated with Center for
       High Pressure Science and Technology Advanced Research.
       What is the title of this paper?"

答案: "Nested order-disorder framework containing a crystalline
       matrix with self-filled amorphous-like innards"

约束条件:
  ✓ publication_year = 2022
  ✓ author_count = 14
  ✓ first_author = Kejun Bu
  ✓ institution = Center for High Pressure Science...

推理链:
  Paper(year=2022, authors=14)
    → HAS_AUTHOR → Author(Kejun Bu)
    → AFFILIATED_WITH → Institution(...)
    → [回溯] → Paper.title

复杂度: 4个约束, 4跳推理, medium/hard难度
```

#### Browsecomp-V3当前输出

```
问题: "8位作者合著，是哪篇论文？"

答案: "Nested order-disorder framework containing a crystalline
       matrix with self-filled amorphous-like innards"

约束条件:
  ✓ author_count = 8

推理链:
  Paper → [过滤] author_count=8

复杂度: 1个约束, 1跳推理, easy难度
```

### 7种推理链模板支持情况

| 模板 | 名称 | 当前支持 | 复杂度 |
|------|------|----------|--------|
| A | Paper-Author-Institution | ⚠️ 部分 | 需多跳遍历 |
| B | Person-Academic-Path | ❌ 不支持 | 需实体数据 |
| C | Citation-Network | ⚠️ 部分 | 需反向遍历 |
| D | Collaboration-Network | ❌ 不支持 | 需多跳遍历 |
| E | Event-Participation | ❌ 不支持 | 需实体数据 |
| F | Technical-Content | ❌ 不支持 | 需实体数据 |
| G | Acknowledgment-Relation | ❌ 不支持 | 需实体数据 |

---

## 🔍 当前复杂度低的根本原因

### 1. 配置限制

```python
# main.py 默认配置
--min-constraints 1    # ← 仅1个约束
--max-constraints 1    # ← 仅1个约束
```

**影响**: 无法生成多约束组合问题

### 2. 有效约束类型仅4种

```python
# constraint_generator.py
VALID_CONSTRAINT_TYPES = {
    "temporal",      # 时间约束
    "author_count",  # 作者数量
    "citation",       # 引用数
    "title_format",   # 标题格式
}
```

**影响**: 30种约束类型中26种未生效

### 3. 多跳约束未实现

**单跳约束 (当前支持)**:
```python
# Paper → [直接过滤] → 结果
Paper.filter(publication_year > 2020)
```

**多跳约束 (Browsecomp标准)**:
```python
# Paper → HAS_AUTHOR → Author → AFFILIATED_WITH → Institution
Paper.filter(publication_year > 2020)
  .traverse(HAS_AUTHOR)
  .filter(author_order = 1)
  .traverse(AFFILIATED_WITH)
  .filter(name = "MIT")
```

**当前问题**:
- `person_name` 约束需要: Paper → HAS_AUTHOR → Author (2跳)
- `institution_affiliation` 需要: Paper → HAS_AUTHOR → Author → AFFILIATED_WITH → Institution (3跳)
- `coauthor` 约束需要: Paper → HAS_AUTHOR → Author → HAS_AUTHOR(reverse) → Paper → HAS_AUTHOR → Author (5跳)

### 4. 图遍历限制

**当前遍历能力**:
- ✅ 单节点过滤 (filter_current_node)
- ✅ 边遍历 + 计数 (traverse_and_count)
- ❌ 多跳链式遍历 (Chain traversal)
- ❌ 反向边遍历 (Reverse traversal)
- ❌ 边属性过滤 (Edge attribute filtering)

---

## 🛠️ 复杂度提升方案

### 阶段1: 增加约束数量 (立即可做)

**目标**: 从1个约束提升到3-5个约束

**实现方式**:
```bash
# 修改命令行参数
python main.py --count 100 --min-constraints 3 --max-constraints 5
```

**预期效果**:
- 难度: easy → medium
- 成功率: 50% → 30-40% (约束组合更难匹配)
- 多样性: 提升

**工作量**: 0小时 (仅需配置修改)

---

### 阶段2: 实现多跳约束遍历 (核心功能)

**目标**: 支持2-4跳的推理链

**需要实现的遍历模式**:

#### 模式1: Paper → Author 遍历
```python
# 约束: first_author = "Kejun Bu"
# 推理链: Paper → HAS_AUTHOR → Author[order=1]

def traverse_with_filter(nodes, edge_type, target_filter):
    """遍历边并对目标节点过滤"""
    results = []
    for node in nodes:
        for neighbor in graph.neighbors(node):
            edge_data = graph.get_edge_data(node, neighbor)
            if edge_data.get("edge_type") == edge_type:
                neighbor_data = graph.nodes[neighbor]
                if target_filter(neighbor_data):
                    results.append(neighbor)
    return results
```

#### 模式2: 反向遍历
```python
# 约束: cited_by_author = "Kejun Bu"
# 推理链: Author → HAS_AUTHOR(reverse) → Paper → CITES → Paper

def traverse_reverse(nodes, edge_type):
    """反向遍历边"""
    results = []
    for node in nodes:
        for neighbor in graph.predecessors(node):
            edge_data = graph.get_edge_data(neighbor, node)
            if edge_data.get("edge_type") == edge_type:
                results.append(neighbor)
    return results
```

#### 模式3: 链式遍历
```python
# 约束: author_from_institution = "MIT"
# 推理链: Paper → HAS_AUTHOR → Author → AFFILIATED_WITH → Institution

def chain_traverse(start_nodes, chain):
    """
    chain = [
        (EdgeType.HAS_AUTHOR, NodeType.AUTHOR, {"order": 1}),
        (EdgeType.AFFILIATED_WITH, NodeType.INSTITUTION, {"name": "MIT"})
    ]
    """
    current = start_nodes
    for edge_type, target_type, filter_fn in chain:
        current = traverse_with_filter(current, edge_type, filter_fn)
        if not current:
            return []
    return current
```

**工作量**: 8-12小时

**预期效果**:
- 支持6种约束类型 (增加 person_name, institution_affiliation 等)
- 支持2-3跳推理
- 难度: easy/medium

---

### 阶段3: 扩展约束类型 (增强功能)

**目标**: 支持15-20种约束类型

**优先级排序**:

| 优先级 | 约束类型 | 所需遍历 | 工作量 |
|--------|----------|----------|--------|
| P0 | `person_name` | 2跳 | 2小时 |
| P0 | `author_order` | 2跳 | 2小时 |
| P1 | `institution_affiliation` | 3跳 | 3小时 |
| P1 | `coauthor` | 5跳 | 5小时 |
| P2 | `publication_history` | 反向 | 4小时 |
| P2 | `editorial_role` | 实体属性 | 2小时 |
| P3 | `research_topic` | 实体遍历 | 6小时 |
| P3 | `technical_entity` | 实体遍历 | 6小时 |

**工作量**: 30-40小时

**预期效果**:
- 支持15种约束类型
- 支持3-5跳推理
- 难度: easy/medium/hard

---

### 阶段4: 优化问题生成 (质量提升)

**目标**: 提升问题自然度和多样性

**改进方向**:

1. **句式模板扩展**
```python
# 当前: 简单句式
"{constraints}的论文标题是什么？"

# 改进: 多样化句式
"请找出{constraints}的论文，并分析其研究主题。"
"基于{constraints}条件，哪篇论文最符合要求？"
"在{constraints}的条件下，推荐一篇相关论文。"
```

2. **约束组合语义**
```python
# 当前: 简单AND组合
约束1 AND 约束2 AND 约束3

# 改进: 语义化组合
"在{时间范围}发表的、由{作者数}位研究者合作、
 且引用数超过{引用数}的论文是哪篇？"
```

3. **答案上下文化**
```python
# 当前: 简单标题
答案: "Nested order-disorder framework..."

# 改进: 带上下文的答案
答案: "《Nested order-disorder framework...》
       这是一篇2022年发表的材料科学论文，
       由Kejun Bu等14位研究者合作完成。"
```

**工作量**: 20-30小时

---

## 📋 开发路线图

### Phase 1: 配置优化 (1小时)

- [x] 创建本分析文档
- [ ] 测试多约束配置 (`--min-constraints 3`)
- [ ] 分析多约束成功率
- [ ] 调整默认参数

**里程碑**: 支持3-5约束/问题

---

### Phase 2: 多跳遍历实现 (8-12小时)

- [ ] 实现 `traverse_with_filter()`
- [ ] 实现反向遍历 `traverse_reverse()`
- [ ] 实现链式遍历 `chain_traverse()`
- [ ] 更新 `QueryExecutor` 支持多跳
- [ ] 更新 `ReasoningChain` 记录多跳步骤
- [ ] 单元测试
- [ ] 集成测试

**里程碑**: 支持2-3跳推理，6种约束类型

---

### Phase 3: 约束类型扩展 (30-40小时)

- [ ] 实现 `person_name` 约束
- [ ] 实现 `author_order` 约束
- [ ] 实现 `institution_affiliation` 约束
- [ ] 实现 `coauthor` 约束
- [ ] 实现反向引用约束
- [ ] 实现实体类型约束
- [ ] 更新约束映射表
- [ ] 性能优化
- [ ] 全面测试

**里程碑**: 支持15种约束类型，3-5跳推理

---

### Phase 4: 问题生成优化 (20-30小时)

- [ ] 扩展句式模板库
- [ ] 实现约束组合语义化
- [ ] 实现答案上下文化
- [ ] 添加难度评级算法
- [ ] A/B测试生成质量

**里程碑**: 生成自然、多样的问题

---

### Phase 5: 生产优化 (可选)

- [ ] 实现并行化生成
- [ ] 实现缓存机制
- [ ] 实现增量生成
- [ ] 性能基准测试
- [ ] 负载测试

**里程碑**: 生产就绪，支持大规模生成

---

## 🎯 成功指标

### 短期目标 (1-2周)

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 约束数量 | 1个 | 3-5个 |
| 推理跳数 | 1跳 | 2-3跳 |
| 约束类型 | 4种 | 8-10种 |
| 难度分布 | 100% easy | mixed |

### 中期目标 (1-2月)

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 约束数量 | 1个 | 3-6个 |
| 推理跳数 | 1跳 | 3-5跳 |
| 约束类型 | 4种 | 15-20种 |
| 难度分布 | 100% easy | easy/medium/hard |

### 长期目标 (3-6月)

| 指标 | 目标值 |
|------|--------|
| 约束类型 | 30+ 种 (全部支持) |
| 推理模板 | 7种 (全部生效) |
| 生成质量 | 接近Browsecomp原版 |
| 生成速度 | >200 问题/秒 |

---

## 📚 参考文档

- Browsecomp-V2 推理链模板: `/home/huyuming/browsecomp-V2/deliverables/推理链模板.md`
- Browsecomp-V2 约束映射: `/home/huyuming/browsecomp-V2/deliverables/constraint_to_graph_mapping.json`
- 代码评审报告: `CODE_REVIEW_REPORT.md`

---

**维护者**: Browsecomp-V3 开发团队
**最后更新**: 2026-02-01
