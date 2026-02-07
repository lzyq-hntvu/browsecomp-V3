# Browsecomp-V3 快速开始

本文档帮助新用户快速上手 Browsecomp-V3 项目。

---

## 1 分钟速览

```
项目: 学术问题生成器
技术: 知识图谱 + 多跳推理 + 约束驱动
架构: 藏宝图模型 + 漏斗模型（混合）
状态: V3项目Phase 3完成，AgentFounder方法研究完成
当前阶段: 方向决策（继续V3 vs 采用AgentFounder）
```

---

## 安装

```bash
# 克隆项目
cd /home/huyuming/projects/browsecomp-V3

# 安装依赖
pip install -r requirements.txt

# 或安装为包
pip install -e .
```

---

## 快速生成问题

### 基础使用

```bash
# 生成 50 个问题（默认）
python main.py --count 50

# 推荐配置（最佳质量）
python main.py --count 100 --min-constraints 2 --max-constraints 3

# 大规模生成
python main.py --count 500 --min-constraints 2 --max-constraints 4

# 详细调试模式
python main.py --count 50 -v
```

### 输出格式

```bash
# JSON 格式
python main.py --format json

# Markdown 格式
python main.py --format markdown

# 双格式（默认）
python main.py --format both
```

### 模板选择

```bash
# 使用特定模板
python main.py --template A --count 20

# 可用模板: A, B, C, D, E, F, G
```

---

## 快速测试

```bash
# Phase 3 约束测试
python test_phase3_constraints.py

# 所有 30 种约束测试
python test_all_30_constraints.py

# 多跳遍历测试
python test_multi_hop_traversal.py

# 大规模测试
python test_multi_hop_scale.py

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/
```

---

## 输出位置

生成的文件保存在 `output/questions/` 目录：

```
output/questions/
├── questions_20260203_095247.json    # JSON 格式
└── questions_20260203_095247.md      # Markdown 格式
```

---

## 核心概念速览

### 推理链模板 (A-G)

| 模板 | 名称 | 示例路径 |
|------|------|----------|
| A | Paper-Author-Institution | Paper → Author → Institution |
| B | Person-Academic-Path | Education → Awards → Positions |
| C | Citation-Network | Citation relationships |
| D | Collaboration-Network | Multi-paper collaboration |
| E | Event-Participation | Conference presentations |
| F | Technical-Content | Technical content analysis |
| G | Acknowledgment-Relation | Acknowledgment relationships |

### 约束类型

- **Phase 1**: 单跳约束 (4种) - temporal, author_count, citation, title_format
- **Phase 2**: 多跳约束 (3种) - person_name, author_order, institution_affiliation
- **Phase 3**: 高级多跳 (3种) - coauthor(5跳), cited_by_author(反向), publication_venue

### 问题生成机制

```
藏宝图阶段: 从真实 KG 采样约束值（保证答案存在）
    +
漏斗阶段: 逐层过滤候选集（保证约束一致性）
    =
高质量问题
```

---

## 了解更多

### 5 分钟了解项目

1. 阅读 `docs/PROJECT_MEMORY.md` 的"项目概览"和"关键指标"
2. 查看"2026-02-05 AgentFounder方法研究"
3. 理解当前决策点：V3项目 vs 新项目（AgentFounder）
4. 阅读 `docs/QANDA_KG_ANALYSIS.md` 了解数据基础

### 深入研究

| 主题 | 文档 |
|------|------|
| 系统架构 | `docs/ARCHITECTURE.md` |
| 常见问题 | `docs/FAQ.md` |
| 科普文档 | `docs/BROWSECOMP_V3_PRIMER.md` |
| 生成机制 | `docs/GENERATION_MECHANISM_ANALYSIS.md` |
| Phase 3实现 | `docs/PHASE3_COMPLETE_REPORT.md` |

---

## 下一步

当前项目处于方向决策阶段：

1. **采用AgentFounder方法**（推荐）- 5天完成
2. **继续V3项目改进** - 1-2月
3. **实现方案A v3.0** - 3-4周

详见 `docs/PROJECT_MEMORY.md` 的"下一步建议"章节。
