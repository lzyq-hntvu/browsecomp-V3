# Browsecomp-V3 系统架构

本文档描述 Browsecomp-V3 的技术架构和实现细节。

---

## 系统架构概览

### 模块化流水线架构

```
模板选择器 (templates/) → 约束生成器 (constraints/) → 查询执行器 (graph/)
     ↓                           ↓                           ↓
问题生成器 (generator/) ← 答案提取器 (generator/) ← 图遍历 (traversal.py)
     ↓
质量验证器 (validator/) → 多样性检查器 (validator/) → 导出器 (output/)
```

---

## 项目结构

```
browsecomp_v3/
├── core/               # 全局配置、Pydantic模型、异常
├── templates/          # 推理链模板 (A-G)
├── constraints/        # 约束生成和映射
│   ├── constraint_generator.py  # Phase 3 注入机制
│   └── value_generator.py       # Phase 3 值生成器
├── graph/              # 知识图谱操作 (NetworkX)
├── generator/          # 问题生成和答案提取
├── validator/          # 质量验证和多样性
├── output/             # JSON/Markdown 导出
└── utils/              # 日志工具
```

---

## 约束类型层次

```
总约束: 30 种（映射文件定义）
    ├── 已启用: 31 种（白名单）
    ├── 可工作: 20 种（67%）
    │   ├── Phase 1: 4 种（单跳）
    │   │   ├── temporal - 时间约束
    │   │   ├── author_count - 作者数量
    │   │   ├── citation - 引用关系
    │   │   └── title_format - 标题格式
    │   ├── Phase 2: 3 种（2-3 跳）
    │   │   ├── person_name - 人员姓名
    │   │   ├── author_order - 作者顺序
    │   │   └── institution_affiliation - 机构隶属
    │   ├── Phase 3: 3 种（2-5 跳，含反向）✅
    │   │   ├── coauthor - 合作者关系 (5跳)
    │   │   ├── cited_by_author - 被引作者 (反向遍历)
    │   │   └── publication_venue - 发表场所
    │   ├── Phase 4: 7 种（filter_current_node）
    │   └── Phase 5: 6 种（Entity 相关）
    └── 待修复: 11 种（需要值生成器或数据支持）
```

---

## 遍历能力

| 跳数 | 类型 | 约束示例 | 复杂度 |
|------|------|----------|--------|
| 1 跳 | 单跳 | temporal, citation | 低 |
| 2 跳 | 多跳 | person_name, publication_venue | 中 |
| 3 跳 | 多跳 | institution_affiliation | 中-高 |
| 5 跳 | 高级多跳 | coauthor | 最高 |
| 反向 | 反向遍历 | cited_by_author | 中 |

---

## 代码注入机制 (Phase 3)

```
正常约束流程:
模板 → 适用约束列表 → 随机选择 → 实例化 → 过滤 → 输出

Phase 3 注入流程:
模板 → 适用约束列表
    → 随机选择
    → [15% 概率注入虚拟 ID]
    → 实例化（检测虚拟 ID）
    → 过滤
    → 输出
```

### 核心代码

```python
# 文件: constraints/constraint_generator.py

# 注入逻辑（在 generate() 方法中）
phase3_injection_rate = 0.15  # 可配置

if random.random() < phase3_injection_rate:
    virtual_id = random.choice([
        'PHASE3_COAUTHOR',
        'PHASE3_CITED_BY_AUTHOR',
        'PHASE3_PUBLICATION_VENUE'
    ])
    selected_constraint_ids.append(virtual_id)

# 虚拟 ID 处理（在 _instantiate_constraint() 方法中）
if constraint_id.startswith('PHASE3_'):
    phase3_mapping = {
        'PHASE3_COAUTHOR': 'coauthor',
        'PHASE3_CITED_BY_AUTHOR': 'cited_by_author',
        'PHASE3_PUBLICATION_VENUE': 'publication_venue'
    }

    constraint_type = phase3_mapping.get(constraint_id)
    virtual_rule = {
        'constraint_type': constraint_type,
        'constraint_id': constraint_id,
        'graph_operation': {...}
    }

    return self._instantiate_multi_hop_constraint(constraint_id, virtual_rule)
```

**优点**:
- 无需修改外部配置文件
- 向后兼容
- 易于调整注入率
- 清晰的虚拟 ID 命名约定

---

## 多跳遍历机制

### 遍历链格式

```python
traversal_chain = [
    {
        "edge_type": "HAS_AUTHOR",
        "target_node": "Author",
        "node_filter": {"name": {"=": "Zhang Wei"}},
        "edge_filter": {"author_order": 1},
        "direction": "reverse"  # 可选，支持反向遍历
    },
    # ... 更多步骤
]
```

### 回溯机制

```python
requires_backtrack = True  # 遍历后回到起始节点类型
```

---

## 约束值生成器

### 支持的约束类型

- coauthor, cited_by_author: 复用 `_generate_person_name_value()`
- publication_venue: 新增 `_generate_venue_value()`

### Venue 值生成器示例

```python
# 文件: constraints/value_generator.py

def _generate_venue_value(self) -> str:
    """从知识图谱提取 Venue 名称"""
    venues = []
    for node_id, node_data in self.kg.nodes(data=True):
        if node_data.get("type", "").upper() == "VENUE":
            venue_name = node_data.get("name")
            if venue_name:
                venues.append(venue_name)

    return random.choice(venues) if venues else "Nature"
```

---

## 问题生成机制

### 混合模型架构

Browsecomp-V3 采用**藏宝图模型 + 漏斗模型**的混合架构：

```
藏宝图阶段（Treasure Map）- 保证答案存在
  ├── 从真实 KG 采样约束值
  ├── 例: publication_year → 2022
  ├── 例: person_name → "Kejun Bu"
  └── 例: institution_name → "MIT"

漏斗阶段（Funnel）- 逐层过滤候选
  ├── filter_current_node: 过滤当前节点属性
  ├── traverse_edge: 沿边遍历到新节点
  ├── traverse_and_count: 遍历并统计数量
  └── multi_hop_traverse: 2-5跳复杂遍历

结果
  └── 从最终候选集中随机选择答案
```

### 8 阶段生成流程

```
1. 模板选择
   └── 从 7 个推理链模板(A-G)中选择

2. 约束值采样 [藏宝图]
   └── value_generator.py: 从 KG 采样真实值

3. 约束实例化
   └── constraint_generator.py: 生成 Constraint 对象

4. 图遍历 [漏斗]
   └── traversal.py: 执行 4 种过滤操作

5. 候选筛选
   └── 去除不满足所有约束的节点

6. 答案选择
   └── 从候选集随机选择

7. 问题生成
   └── question_generator.py: 填充句式模板

8. 质量验证
   └── validator.py: 检查语法、多样性等
```

---

## 推理链模板 (A-G)

| 模板 | 名称 | 频率 | 覆盖范围 |
|------|------|-----------|----------|
| A | Paper-Author-Institution | 30% | Paper → Author → Institution |
| B | Person-Academic-Path | 22% | Education → Awards → Positions |
| C | Citation-Network | 15% | Citation relationships |
| D | Collaboration-Network | 10% | Multi-paper collaboration |
| E | Event-Participation | 16% | Conference presentations |
| F | Technical-Content | 5% | Technical content analysis |
| G | Acknowledgment-Relation | 2% | Acknowledgment relationships |

---

## 核心代码位置

| 模型 | 文件 | 关键方法 |
|------|------|----------|
| 藏宝图 | `constraints/constraint_generator.py` | `generate()` |
| 藏宝图 | `constraints/value_generator.py` | `generate_value()` |
| 漏斗 | `graph/traversal.py` | `traverse()` |
| 漏斗 | `graph/query_executor.py` | `execute()` |

---

## 外部依赖

### 数据依赖

1. **知识图谱**: `/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json`
   - 节点数: 4,700
   - 边数: 5,246

2. **QandA知识图谱**: `/home/huyuming/projects/QandA/data/`
   - 节点数: 3,404
   - 边数: 4,063

3. **模板和映射**: `/home/huyuming/browsecomp-V2/deliverables/`
   - `推理链模板.md` - 7个推理链模板定义
   - `constraint_to_graph_mapping.json` - 30个约束映射规则

### 技术栈

- Python 3.10+
- NetworkX (图操作)
- Pydantic (数据验证)
- Rich (终端输出)
- PyYAML (配置管理)
