# Spec: 约束驱动的动态推理链生成

**状态**: 草案 (Draft)
**日期**: 2026-02-03
**背景**: 基于与杨逸飞的第2次沟通

---

## 1. 背景与动机

### 1.1 当前V3的问题

当前Browsecomp-V3采用**模板驱动**的架构：

```
Template A（固定）: Paper → Author → Institution  [3跳]
Template B（固定）: Author → Education → Awards   [3跳]
Template C（固定）: Paper → Cites → Paper         [2跳]
...共7个固定模板
```

**问题**:
- 推理链结构被模板**锁死**，无法灵活扩展
- 跳数受模板限制（最多5跳，由coauthor模板固定）
- 约束只能在预定义的模板路径上生效

### 1.2 杨逸飞的核心建议

> "规则和约束可以无限循环着选节点和边，如果不能循环着选那推理链跳数就被限制住了"

**解读**: 从"模板驱动"改为"约束驱动"，让约束决定推理路径，而非模板预设路径。

---

## 2. 新方案概述

### 2.1 核心思想

**约束驱动的动态推理链构建**:

```
从任意节点类型开始（如 Paper）
    ↓ 根据约束1选择边类型（如 HAS_AUTHOR）
到达 Author 节点
    ↓ 根据约束2选择边类型（如 AFFILIATED_WITH）
到达 Institution 节点
    ↓ 根据约束3可以继续...甚至可以回到 Paper！
回到 Paper 节点（通过 AUTHOR_OF 反向边）
    ↓ ...继续扩展
```

### 2.2 关键特性

| 特性 | 说明 |
|------|------|
| **节点数量上限** | 可配置（如 max_nodes=5），而非被模板限制 |
| **循环路径** | 支持 Paper→Author→Paper→Author 的循环遍历 |
| **约束驱动** | 每个步骤由当前适用的约束决定，而非预设模板 |
| **动态构建** | 推理链在生成时动态构建，不是预定义 |

---

## 3. 详细设计

### 3.1 推理链构建流程

```
输入: 起始节点类型 (如 "Paper"), 最大节点数 (如 5)
输出: 动态构建的推理链

步骤:
1. 初始化: current_node_type = 起始类型
2. 循环直到达到 max_nodes:
   a. 查询当前节点类型适用的约束列表
   b. 根据策略选择一个约束
   c. 约束决定: (1) 边类型 (2) 下一节点类型 (3) 过滤条件
   d. 执行图遍历，获取下一跳节点
   e. current_node_type = 下一节点类型
   f. 记录遍历步骤
3. 从终点反向确定答案节点
4. 生成问题
```

### 3.2 约束的新角色

当前V3中约束只是**过滤条件**:
```yaml
constraint:
  type: "publication_year"
  value: 2022
  # 只是检查当前节点是否满足条件
```

新方案中约束还决定**遍历方向**:
```yaml
constraint:
  type: "person_name"
  value: "张三"
  # 决定: 使用 HAS_AUTHOR 边
  # 决定: 下一跳节点类型是 Author
  # 决定: 过滤条件 name="张三"
```

### 3.3 支持的"循环"路径示例

```
1. 合著者网络（2跳）:
   Paper A --HAS_AUTHOR--> Author X --AUTHOR_OF--> Paper B

2. 扩展合著者网络（4跳）:
   Paper A --> Author X --> Paper B --> Author Y --> Paper C

3. 引用网络（3跳）:
   Paper A --CITES--> Paper B --CITES--> Paper C

4. 复杂循环（5跳）:
   Paper --> Author --> Institution --> Author --> Paper
   （找同机构的其他作者发表的论文）
```

### 3.4 节点数量限制 vs 跳数限制

| | 当前V3 | 新方案 |
|---|---|---|
| 限制方式 | 模板固定跳数 | 配置 max_nodes |
| 示例 | Template A 固定3跳 | max_nodes=5 可构建1-5跳的链 |
| 灵活性 | 低 | 高 |

---

## 4. 与V3架构对比

### 4.1 当前V3架构

```
[Template Selector] → [Constraint Generator] → [Query Executor]
      (选A-G)              (在模板路径上选约束)       (执行固定遍历)
```

### 4.2 新架构

```
[Chain Builder] → [Constraint Selector] → [Traversal Executor] → [Loop?]
   (初始化起点)      (动态选择约束)         (执行单步遍历)
         ↑___________________________________________|
                    (未达max_nodes则继续)
```

### 4.3 关键差异

| 方面 | V3 | 新方案 |
|------|-----|--------|
| 驱动方式 | 模板驱动 | 约束驱动 |
| 路径确定时机 | 设计时（模板定义） | 运行时（动态构建） |
| 跳数限制 | 模板固定 | max_nodes配置 |
| 循环支持 | 否（模板是线性的） | 是（可回到已访问节点类型） |
| 复杂度 | 相对简单 | 需要处理状态和历史 |

---

## 5. 数据范围限定

根据杨逸飞建议：

> "咱就在现有的知识图谱上进行问答生成，把只关注论文本身的问答做好了之后，看刘升华的反映"

**Phase 1 范围**: 仅使用与Paper直接相关的节点类型
- ✅ Paper（中心节点）
- ✅ Author（论文作者）
- ✅ Institution（作者机构）
- ✅ Venue（发表期刊/会议）
- ❌ Award（暂不考虑）
- ❌ Education（暂不考虑）

**目标**: 把"论文网络"内的推理做到极致，不扩展KG数据。

---

## 6. 待确认问题

### 6.1 对杨逸飞意图的确认

请确认以下理解是否正确：

1. **"无限循环"** 指的是约束可以动态选择边类型，使得推理链可以灵活延伸，包括回到已访问的节点类型（如 Paper→Author→Paper），而非真正的无限死循环，对吗？

2. **节点数量上限** 是用户可配置的参数（如设置max_nodes=5），而非固定模板，对吗？

3. **约束决定遍历** 意味着需要为每种约束类型定义：(a)适用的节点类型 (b)可选择的边类型 (c)目标节点类型，对吗？

4. **数据范围** 先限定在Paper-Author-Institution-Venue这个子图上，不扩展QandA KG的其他属性，对吗？

### 6.2 技术决策待确认

1. 是否需要支持真正的"循环"（如 A→B→C→A），还是只是"可回到同类型节点"？
2. max_nodes 的默认值设为多少合适？
3. 约束选择策略：随机选择还是按某种优先级？
4. 是否需要保证推理链的终点一定是特定类型（如必须回到Paper）？

---

## 7. 初步实现思路

### 7.1 核心组件

```python
class DynamicChainBuilder:
    """动态推理链构建器"""

    def build_chain(self, start_type: str, max_nodes: int) -> ReasoningChain:
        """动态构建推理链"""
        pass

    def select_next_constraint(self, current_type: str, history: List) -> Constraint:
        """根据当前节点选择下一个约束"""
        pass

    def get_available_edges(self, node_type: str) -> List[EdgeType]:
        """获取从当前节点类型可出发的边类型"""
        pass
```

### 7.2 约束定义扩展

```python
class Constraint:
    type: str                    # 约束类型
    value: Any                   # 约束值

    # 新增字段
    applicable_on: List[str]     # 适用的节点类型
    outgoing_edges: List[str]    # 可选择的出边类型
    target_node_type: str        # 目标节点类型
```

---

## 8. 后续步骤

1. **确认Spec**: 与你确认上述理解是否正确
2. **细化设计**: 确认后完善技术设计
3. **原型实现**: 先实现MVP版本验证思路
4. **评估对比**: 与V3模板方式对比效果

---

**等待你的反馈和确认。**
