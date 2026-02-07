# Browsecomp-V3 常见问题 FAQ

本文档收集了 Browsecomp-V3 项目的常见问题及其解答。

---

## 项目状态相关

### Q1: 当前项目状态是什么？

**A**: 方向决策阶段（2026-02-05）

```
V3项目状态:
  - Phase 3完成（20种约束可用）
  - 识别出数据限制问题
  - 继续改进需要1-2个月

AgentFounder研究:
  - 完成方法调研
  - 分析QandA KG数据
  - 提出方案C（5天完成）

当前决策:
  - 选项1: 继续V3项目（扩展KG数据）
  - 选项2: 新项目采用AgentFounder ⭐ 推荐
  - 选项3: 实现方案A v3.0设计
```

### Q2: 为什么推荐AgentFounder而不是继续V3？

**A**: 性价比和团队适配性

```
团队情况:
  - 2人（胡老师 + 胡云舒本科生）
  - 目标: 技术探索（不是发顶会）
  - 质量要求: 80%够用

V3项目:
  - 需要扩展QandA KG数据（1-2月工作量）
  - 继续改进ROI低
  - 数据限制是根本问题

AgentFounder:
  - 5天完成 vs V3的1-2月
  - $0.3成本 vs V3需要扩展数据
  - 有开源代码直接使用
  - 学习价值大（工业界最新方法）
  - 100%真实数据（利用现有QandA KG）
```

### Q3: QandA KG能支持AgentFounder方法吗？

**A**: 可以，但有限制

```
可用数据:
  - 52篇论文 → 论文元数据陈述
  - 260个作者 → 作者-论文关系
  - 56条引用 → 引用推理链
  - 3234条MENTIONS → 实体关系网络

限制:
  - Browse Complexity较低（2-3跳为主）
  - 问题类型受限于现有关系
  - 预期生成300-500题

但足够技术探索:
  - 验证AgentFounder方法可行性
  - 理解实体锚定记忆架构
  - 学习FAS离线合成技术
  - 可写成技术报告
```

### Q4: 如果采用AgentFounder，V3项目怎么办？

**A**: 冻结V3，创建新项目

```
browsecomp-V3/ (冻结)
  - 保留所有代码和文档
  - 作为参考和对比基准
  - Phase 3成果可复用

browsecomp-agentfounder/ (新项目)
  - 独立项目目录
  - 复用QandA KG数据
  - 采用阿里巴巴开源代码
  - 5天快速实施

未来可能:
  - 如果AgentFounder成功 → 深入研究
  - 如果需要高质量 → 回到V3或v3.0设计
  - 两个项目可并行存在
```

---

## 系统架构相关

### Q5: 漏斗模型和藏宝图模型是什么？

**A**: 这是 Browsecomp 的两种核心问题生成策略：

**漏斗模型** (Funnel Model):
- 策略: 先用规则过滤（筛选），再生成问题
- 实现: 4 种图遍历操作逐层过滤候选集
- 代码: `graph/traversal.py`
- 优点: 保证约束一致性
- 缺点: 可能过滤掉所有候选

**藏宝图模型** (Treasure Map Model):
- 策略: 先埋宝藏（定答案），再画地图（写问题）
- 实现: 从真实 KG 采样约束值
- 代码: `constraints/value_generator.py`
- 优点: 保证答案存在
- 缺点: 难以处理复杂多跳

**V3 混合策略**: 先藏宝图采样值，再用漏斗过滤，结合两者优势

### Q6: 什么是Phase 1/2/3约束？

**A**: V3项目分阶段实现的约束类型

| Phase | 约束数 | 类型 | 特点 |
|-------|--------|------|------|
| Phase 1 | 4种 | 单跳 | temporal, author_count, citation, title_format |
| Phase 2 | 3种 | 2-3跳 | person_name, author_order, institution_affiliation |
| Phase 3 | 3种 | 2-5跳+反向 | coauthor(5跳), cited_by_author(反向), publication_venue |

### Q7: 代码注入机制是什么？

**A**: Phase 3 实现的一种无需修改配置文件的约束扩展方式

```python
# 15% 概率注入 Phase 3 虚拟约束
if random.random() < 0.15:
    virtual_id = random.choice([
        'PHASE3_COAUTHOR',
        'PHASE3_CITED_BY_AUTHOR',
        'PHASE3_PUBLICATION_VENUE'
    ])
    selected_constraint_ids.append(virtual_id)
```

优点：向后兼容、易于扩展、无需修改外部配置

---

## 问题生成相关

### Q8: 为什么复杂问题生成约束数少？

**A**: 数据可用性限制，不是代码问题

```
目标配置: --min-constraints 3 --max-constraints 5
实际结果: 平均 1.2 个约束/问题

原因分析:
  1. 约束值生成器返回 "unknown" (46%)
  2. "unknown" 约束被过滤掉
  3. 知识图谱缺失所需属性数据

根本原因:
  QandA KG 只包含论文引用关系
  缺少 Author.phd_year, Institution.location 等
```

解决方案: 扩展 QandA 知识图谱或使用新数据源

### Q9: 生成速度如何？

**A**: 根据规模不同

| 规模 | 速度 |
|------|------|
| 100问题 | 57 Q/秒 |
| 200问题 | 54 Q/秒 |
| 500问题 | 33 Q/秒 |

### Q10: 成功率和多样性如何？

**A**: 取决于问题规模

| 规模 | 成功率 | 多样性 |
|------|--------|--------|
| 100问题 | 14% | 67% |
| 200问题 | 15% | 52% |
| 500问题 | 10% | 32% |

---

## 技术问题相关

### Q11: 如何运行测试？

**A**: 使用以下命令

```bash
# Phase 3 约束测试
python test_phase3_constraints.py

# 所有 30 种约束测试
python test_all_30_constraints.py

# 多跳遍历测试
python test_multi_hop_traversal.py

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/
```

### Q12: 如何生成问题？

**A**: 使用主入口脚本

```bash
# 推荐配置（最佳质量，含 Phase 3 约束）
python main.py --count 100 --min-constraints 2 --max-constraints 3

# 大规模生成（500 问题）
python main.py --count 500 --min-constraints 2 --max-constraints 4

# 详细调试
python main.py --count 50 -v
```

---

## 数据相关

### Q13: QandA知识图谱有什么特点？

**A**: 数据规模和特点

| 类型 | 数量 | 占比 |
|-----|------|------|
| 论文 | 52 | 1.5% |
| 作者 | 260 | 7.6% |
| 机构 | 113 | 3.3% |
| 期刊 | 36 | 1.1% |
| 实体 | 2,943 | 86.5% |

关键发现：
- 实体网络丰富（平均每篇论文62个实体）
- 引用关系稀疏（平均1.08条/论文）
- 缺少作者教育背景、导师关系

详细分析见：`docs/QANDA_KG_ANALYSIS.md`

---

## 更多文档

- 项目状态: `docs/PROJECT_MEMORY.md`
- 系统架构: `docs/ARCHITECTURE.md`
- 快速开始: `docs/QUICK_START.md`
- 科普文档: `docs/BROWSECOMP_V3_PRIMER.md`
