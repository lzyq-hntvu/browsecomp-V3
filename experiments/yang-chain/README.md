# 杨逸飞推理链实验

**实验分支**: `experiment/yang-yifei-chain`

本实验验证"论文引用链+描述实体"生成复杂学术问题的可行性。

## 目录结构

```
experiments/yang-chain/
├── README.md              # 本文件
├── src/                   # 源代码
│   ├── demo_yang_chain.py                 # 基础版本 (3-4节点链)
│   ├── demo_yang_chain_complex.py         # 复杂问题版本 (多约束组合)
│   ├── demo_yang_chain_backtrack.py       # 回溯机制演示
│   ├── demo_yang_chain_fallback.py        # 降级回退机制
│   ├── demo_yang_chain_api.py             # Semantic Scholar API集成
│   ├── demo_yang_chain_api_recursive.py   # 递归API扩展
│   ├── demo_yang_chain_cached.py          # 带缓存的API调用
│   └── demo_yang_chain_10node_simulation.py # 10节点链模拟演示
├── data/                  # 实验数据
│   └── yang_chain_test_set.json   # 测试数据集 (4篇论文)
├── output/                # 生成结果
│   └── *.md, *.json       # 生成的问题文件
└── cache/                 # API缓存 (自动生成)
    └── ss_api/            # Semantic Scholar API缓存

```

## 快速开始

### 1. 基础版本（简单链）

```bash
cd experiments/yang-chain/src
python3 demo_yang_chain.py
```

**功能**: 构建2-4节点论文链，生成前向/后向/跳跃问题

**输出**: `../output/yang_chain_demo_*.md`

### 2. 复杂问题版本

```bash
python3 demo_yang_chain_complex.py
```

**功能**: 基于现有KG生成6种复杂问题类型
- 跨机构合作问题
- 多约束筛选
- 作者合作网络
- 引用+作者约束
- 机构产出统计
- 反向推理

### 3. 10节点链模拟

```bash
python3 demo_yang_chain_10node_simulation.py
```

**功能**: 使用模拟数据展示10节点链的问题生成能力

**说明**: 由于API限流，此版本使用模拟数据演示完整功能

## 核心概念

### 两种回退机制

1. **降级回退** (`demo_yang_chain_fallback.py`)
   ```
   10节点 → 失败 → 8节点 → 5节点 → 3节点 → V3模板
   ```

2. **回溯回退** (`demo_yang_chain_backtrack.py`)
   ```
   P1 → P2 → P3(死路) → 回退到P2 → 选P4 → P5...
   ```

### 问题难度分级

| 级别 | 约束数 | 链长 | 示例 |
|------|--------|------|------|
| Easy | 1-2 | 2 | "2022年论文引用了哪篇研究？" |
| Medium | 2-3 | 3-4 | "2022年+作者X的论文引用了哪篇？" |
| Hard | 3-4 | 5-7 | "跨机构合作的2021年论文引用了哪篇？" |
| Expert | 4+ | 8-10 | "长链中满足多约束的论文是什么？" |

## 技术实现

### 数据流

```
原始KG (52篇论文)
    ↓
API扩展 (Semantic Scholar)
    ↓
扩展KG (200+篇论文，含引用关系)
    ↓
链构建器 (回溯算法)
    ↓
10节点链
    ↓
问题生成器
    ↓
复杂问题 (Expert级别)
```

### 关键组件

- **PaperChainBuilder**: 构建论文引用链
- **YangChainQuestionGenerator**: 生成自然语言问题
- **BacktrackChainBuilder**: 回溯算法实现
- **CachedSemanticScholarAPI**: 带缓存的API客户端

## 实验结果

### 当前限制

- **KG拓扑**: 现有52篇论文为星型结构（paper_1引用所有其他）
- **最长链**: 仅2节点（需要扩展数据才能构建更长链）

### 模拟演示结果

使用50篇模拟论文成功构建：
- ✅ **10节点链**: Paper_0 → Paper_3 → ... → Paper_22
- ✅ **Expert问题**: 5种复杂问题类型
- ✅ **多约束推理**: 年份+机构+引用+位置

## 与V3对比

| 维度 | V3模板 | 杨逸飞链式 |
|------|--------|-----------|
| 链结构 | 固定模板 | 动态构建 |
| 约束来源 | 预定义30种 | 从实体自动提取 |
| 最大链长 | 3跳 | 10+跳（模拟） |
| 问题灵活性 | 中 | 高 |
| 实现复杂度 | 较高 | 中等 |

## 部署建议

### 绕过API限流

```bash
# 1. 预取数据（一次性）
python3 demo_yang_chain_cached.py

# 2. 使用缓存构建扩展KG
python3 demo_yang_chain_api_recursive.py

# 3. 生成10节点链问题
python3 demo_yang_chain_10node_simulation.py
```

### 生产环境建议

1. **批量下载公开数据集** (DBLP/MAG)
2. **建立本地缓存系统**
3. **异步预取论文数据**
4. **与V3模板系统集成**（作为补充）

## 文档索引

- 测试报告: `../../docs/YANG_CHAIN_TEST_REPORT.md`
- 结论与决策: `../../docs/YANG_CHAIN_CONCLUSION.md`
- 原始计划: `../../docs/YANG_CHAIN_EXPERIMENT_PLAN.md`

## 作者

- 实验设计: 杨逸飞
- 实现: Claude Code
- 日期: 2026-02-04
