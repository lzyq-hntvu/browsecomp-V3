# 约束系统验证测试

本目录包含约束生成系统的验证脚本，用于测试和验证各种约束类型是否正常工作。

## 文件说明

| 文件 | 用途 | 运行方式 |
|------|------|----------|
| `test_constraints.py` | 基础约束类型测试（时间、计数等） | `python test_constraints.py` |
| `test_single_constraints.py` | 单约束生成测试 | `python test_single_constraints.py` |
| `test_all_30_constraints.py` | 30种约束类型全面测试 | `python test_all_30_constraints.py` |
| `test_multi_constraints.py` | 多约束组合测试 | `python test_multi_constraints.py` |
| `test_multi_hop_traversal.py` | 多跳遍历功能测试 | `python test_multi_hop_traversal.py` |
| `test_multi_hop_scale.py` | 多跳遍历规模测试 | `python test_multi_hop_scale.py` |
| `test_coauthor_constraint.py` | 合著者约束专项测试 | `python test_coauthor_constraint.py` |
| `test_phase3_constraints.py` | Phase3约束测试 | `python test_phase3_constraints.py` |

## 与单元测试的区别

- **单元测试** (`tests/unit/`)：使用 pytest 框架，用于回归测试
- **验证测试** (`tests/validation/`)：独立脚本，用于开发阶段验证约束功能

## 运行所有验证测试

```bash
cd tests/validation
for f in test_*.py; do
    echo "Running $f..."
    python3 "$f"
    echo ""
done
```

## 注意事项

这些脚本直接操作知识图谱，运行时请确保：
1. KG 数据已正确加载
2. 配置环境变量（如有需要）
3. 部分测试可能需要较长时间（特别是 `test_all_30_constraints.py`）
