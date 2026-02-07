# Browsecomp-V3 版本历史

本文档记录 Browsecomp-V3 项目的版本历史和主要变更。

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.5.2 | 2026-02-05 | AgentFounder方法研究完成 + 方向决策阶段 |
| v0.5.1 | 2026-02-05 | 方案A v3.0风险缓解文档 + QandA KG完整分析 |
| v0.5.0 | 2026-02-05 | 方案A设计文档发布（DETAILED_DESIGN + V2_BROWSE_COMPLEXITY） |
| v0.4.2 | 2026-02-04 | 知识图谱结构分析（KG_STRUCTURE_ANALYSIS.md） |
| v0.4.1 | 2026-02-04 | 科普文档发布（BROWSECOMP_V3_PRIMER.md） |
| v0.4.0 | 2026-02-04 | 战略方向讨论记录（STRATEGIC_DIRECTION_DISCUSSION.md） |
| v0.3.3 | 2026-02-04 | 杨逸飞推理链实验完成（方案C折中混合） |
| v0.3.2 | 2026-02-04 | 低成本构建研究报告发布 |
| v0.3.1 | 2026-02-03 | 固定搭配Demo实现（50个同类问题批量生成） |
| v0.3.0 | 2026-02-03 | 问题生成机制分析完成，数据限制识别 |
| v0.2.2 | 2026-02-02 | Phase 3 完成，代码注入机制，20 种约束可用 |
| v0.2.0 | 2026-01-XX | Phase 2 完成，多跳遍历，7 种约束 |
| v0.1.0 | 2025-XX-XX | Phase 1 完成，基础架构，4 种约束 |

---

## v0.5.2 (2026-02-05)

### 新增
- 阿里巴巴 DeepResearch 方法研究完成
- AgentFounder 框架分析
- FAS（一阶动作合成）方法研究
- 实体锚定开放世界记忆架构分析
- 方向决策阶段进入

### 文档
- `docs/DeepResearch.md` - 阿里巴巴方法完整分析

---

## v0.5.1 (2026-02-05)

### 新增
- QandA 知识图谱完整分析报告（35页）
- 方案A v3.0 风险缓解文档

### 文档
- `docs/QANDA_KG_ANALYSIS.md` - 完整35页分析报告
- `docs/SOLUTION_A_V3_RISK_MITIGATION.md` - 方案A v3.0设计

---

## v0.5.0 (2026-02-05)

### 新增
- 方案A详细设计文档
- 方案A v2.0基于浏览复杂度重构

### 文档
- `docs/SOLUTION_A_DETAILED_DESIGN.md` - 方案A详细设计
- `docs/SOLUTION_A_V2_BROWSE_COMPLEXITY.md` - 方案A v2.0设计

---

## v0.4.2 (2026-02-04)

### 新增
- 知识图谱结构分析

### 文档
- `docs/KG_STRUCTURE_ANALYSIS.md` - QandA知识图谱结构分析

---

## v0.4.1 (2026-02-04)

### 新增
- 科普文档（新手必读）

### 文档
- `docs/BROWSECOMP_V3_PRIMER.md` - 科普文档

---

## v0.4.0 (2026-02-04)

### 新增
- 战略方向讨论记录
- 三个战略方向对比

### 文档
- `docs/STRATEGIC_DIRECTION_DISCUSSION.md` - 战略方向讨论

---

## v0.3.3 (2026-02-04)

### 新增
- 杨逸飞推理链实验完成
- 方案C（折中混合）决策

### 实验
- `experiments/yang-chain/` - 实验目录
- 5个实现版本（基础/复杂/回溯/降级/模拟）

### 文档
- `docs/YANG_CHAIN_EXPERIMENT_PLAN.md` - 实验计划
- `docs/YANG_CHAIN_TEST_REPORT.md` - 测试报告
- `docs/YANG_CHAIN_CONCLUSION.md` - 结论与决策

---

## v0.3.2 (2026-02-04)

### 新增
- 低成本构建研究报告

### 文档
- `docs/LOW_COST_CONSTRUCTION_REPORT.md` - 低成本构建研究

---

## v0.3.1 (2026-02-03)

### 新增
- 固定搭配Demo实现
- 批量生成50个同类问题

### 代码
- `demo_fixed_rule.py` - 固定搭配Demo脚本

### 文档
- `docs/SPEC_DYNAMIC_CONSTRAINT_CHAIN.md` - 固定搭配设计文档

---

## v0.3.0 (2026-02-03)

### 新增
- 问题生成机制深度分析
- 漏斗模型 + 藏宝图模型混合架构解析
- 数据限制识别

### 文档
- `docs/GENERATION_MECHANISM_ANALYSIS.md` - 生成机制分析
- `docs/TEST_VALIDATION_REPORT.md` - 测试验证报告
- `docs/COMPLEX_QUESTION_GENERATION_ANALYSIS.md` - 复杂问题生成分析

---

## v0.2.2 (2026-02-02)

### 新增
- Phase 3 高级多跳约束完整实现
- 代码注入机制
- 3种新约束：coauthor, cited_by_author, publication_venue

### 代码变更
- `constraint_generator.py`: +40行（注入机制）
- `value_generator.py`: +35行（值生成器）

### 约束统计
- 20/30 种约束可用（66.7%）
- Phase 3 生成率：13.36%

### 文档
- `docs/PHASE3_COMPLETE_REPORT.md` - Phase 3完整实现报告
- `docs/PHASE3_FIX_REPORT.md` - Phase 3修复报告

---

## v0.2.0 (2026-01-XX)

### 新增
- Phase 2 多跳遍历实现
- 双向遍历机制
- 3种多跳约束

### 特性
- 2-3跳推理链
- 难度分级（easy/medium）

### 文档
- `docs/MULTI_HOP_IMPLEMENTATION_REPORT.md` - Phase 2实现报告
- `docs/MULTI_HOP_SCALE_TEST_REPORT.md` - 规模测试报告

---

## v0.1.0 (2025-XX-XX)

### 新增
- Phase 1 基础架构实现
- 知识图谱加载
- 模板系统
- 4种单跳约束

### 约束类型
- temporal, author_count, citation, title_format
