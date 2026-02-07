# Browsecomp-V3 项目状态快照

**最后更新**: 2026-02-05
**项目状态**: 方向探索 - AgentFounder方法研究完成
**当前版本**: v0.5.2 (AgentFounder Research Completed)

---

## 项目概览

Browsecomp-V3 是一个**约束驱动的复杂学术问题生成器**，基于知识图谱生成多跳推理问答对。

### 核心特性
- 支持 **20 种约束类型**（Phase 1-3 完整实现）
- 支持 **2-5 跳推理链**（含反向遍历）
- 生成 easy/medium 难度问题
- 支持 JSON/Markdown 双格式输出
- **代码注入机制**实现高级约束

### 当前状态快照

| 指标 | 数值 | 说明 |
|------|------|------|
| **约束类型** | 20/30 种 | 66.7% 可用 |
| **Phase 1** | 4/4 种 | temporal, author_count, citation, title_format |
| **Phase 2** | 3/3 种 | person_name, author_order, institution_affiliation |
| **Phase 3** | 3/3 种 | coauthor, cited_by_author, publication_venue |
| **推理跳数** | 1-5 跳 | 最高 5 跳（coauthor） |
| **生成速度** | 33-57 Q/秒 | 取决于规模 |
| **最佳多样性** | 67% | 100 问题规模 |

---

## 项目结构

```
browsecomp-V3/
├── browsecomp_v3/          # 主包
│   ├── core/               # 核心模块
│   ├── templates/          # 7个推理链模板(A-G)
│   ├── constraints/        # 约束处理
│   ├── graph/              # 图遍历
│   ├── generator/          # 问题生成
│   ├── validator/          # 质量验证
│   └── output/             # 格式化输出
├── experiments/            # 实验目录
│   └── yang-chain/         # 杨逸飞推理链实验
├── tests/                  # 测试
├── docs/                   # 文档
└── output/                 # 输出目录
```

---

## 快速命令

### 生成问题
```bash
# 推荐配置（最佳质量）
python main.py --count 100 --min-constraints 2 --max-constraints 3

# 大规模生成
python main.py --count 500 --min-constraints 2 --max-constraints 4

# 详细调试
python main.py --count 50 -v
```

### 运行测试
```bash
# Phase 3 约束测试
python test_phase3_constraints.py

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/
```

---

## 文档索引（快速查找）

| 想要... | 阅读文档 |
|---------|---------|
| 了解当前状态 | 本文件 |
| 快速上手 | `QUICK_START.md` |
| 查看常见问题 | `FAQ.md` |
| 了解架构设计 | `ARCHITECTURE.md` |
| 查看版本历史 | `CHANGELOG.md` |
| 查看完整文档索引 | `README.md` |

**更多文档**: 见 `docs/README.md` 完整索引

---

## 当前决策点

**关键问题**: 选择技术方向

### 选项1: 采用AgentFounder方法（推荐）
- 冻结browsecomp-V3项目
- 创建新项目 browsecomp-agentfounder
- 5天快速实施
- 成本: $0.3/1000题
- 适合2人团队技术探索

### 选项2: 继续V3项目改进
- 扩展QandA KG数据（1-2月）
- 实现全部30种约束
- 适合如果有足够时间和人力

### 选项3: 实现方案A v3.0
- 从零实现Virtual Web Graph
- 3-4周开发时间
- 需要2-3人团队

---

## 下一步建议

### 如果选择AgentFounder（1周）
1. Day 1: 环境准备 + Clone阿里巴巴仓库
2. Day 2-3: 数据转换脚本
3. Day 4: 问题生成 + LLM-as-Judge过滤
4. Day 5: 质量评估 + 技术报告

### 如果继续V3（1-2月）
1. Week 1-2: 扩展QandA KG
2. Week 3-4: 实现剩余11种约束
3. Week 5-6: 测试和优化
4. Week 7-8: 大规模验证

---

## 外部依赖

1. **知识图谱**: `/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json`
   - 节点数: 3,404（52论文+260作者+113机构+2943实体）
   - 边数: 4,063

2. **模板和映射**: `/home/huyuming/browsecomp-V2/deliverables/`
   - 7个推理链模板定义
   - 30个约束映射规则

---

## 最近更新

### 2026-02-05: AgentFounder方法研究
- 完成阿里巴巴 DeepResearch 方法研究
- 分析 QandA KG 数据基础
- 提出方案C（5天完成，$0.3/1000题）

**相关文档**:
- `docs/DeepResearch.md` - 阿里巴巴方法分析
- `docs/QANDA_KG_ANALYSIS.md` - QandA KG完整分析

### 2026-02-04: 杨逸飞推理链实验
- 实验完成，采用方案C（折中混合）
- 2-hop 引用链构建成功
- 4种推理模式实现

**相关文档**:
- `docs/YANG_CHAIN_CONCLUSION.md` - 实验结论

### 2026-02-02: Phase 3 完成
- 代码注入机制实现
- 3种高级多跳约束
- 20/30 种约束可用

**相关文档**:
- `docs/PHASE3_COMPLETE_REPORT.md` - Phase 3实现报告

---

**最后更新**: 2026-02-05
**联系方式**: 项目 Issue 追踪
