# Browsecomp-V3

> **约束驱动的复杂学术问题生成器**

基于 QandA 学术知识图谱，使用 7 个推理链模板和 30 个约束映射规则自动生成 Browsecomp 风格的多跳推理问答对。

## 项目概述

Browsecomp-V3 是一个独立的问题生成系统，能够：

- 基于知识图谱自动生成复杂学术问答
- 支持多跳推理（5-10跳）
- 每个问题包含完整推理链
- 输出 JSON 和 Markdown 双格式

## 快速开始

### 1. 安装

```bash
cd ~/projects/browsecomp-V3

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 准备数据

将以下文件复制到 `data/templates/` 目录：

- `推理链模板.md` - 从 `/home/huyuming/browsecomp-V2/deliverables/` 复制
- `constraint_to_graph_mapping.json` - 从 `/home/huyuming/browsecomp-V2/deliverables/` 复制

### 3. 运行

```bash
# 生成 50 个问题
python -m browsecomp_v3.main --count 50

# 使用指定模板
python -m browsecomp_v3.main --template A --count 20

# 只输出 JSON
python -m browsecomp_v3.main --format json
```

## 项目结构

```
browsecomp-V3/
├── browsecomp_v3/          # 主包
│   ├── core/               # 核心模块
│   ├── templates/          # 模板管理
│   ├── constraints/        # 约束处理
│   ├── graph/              # 图遍历
│   ├── generator/          # 问题生成
│   ├── validator/          # 质量验证
│   └── output/             # 格式化输出
├── tests/                  # 测试
├── data/                   # 数据目录
├── output/                 # 输出目录
├── config/                 # 配置文件
├── main.py                 # 主入口
└── README.md
```

## 7个推理链模板

| 模板 | 名称 | 频率 | 覆盖问题 |
|------|------|------|----------|
| A | Paper-Author-Institution | 30% | 论文特征→作者→机构 |
| B | Person-Academic-Path | 22% | 教育→获奖→职位 |
| C | Citation-Network | 15% | 引用关系网络 |
| D | Collaboration-Network | 10% | 多论文合作 |
| E | Event-Participation | 16% | 会议演讲参与 |
| F | Technical-Content | 5% | 技术内容分析 |
| G | Acknowledgment-Relation | 2% | 致谢人际关系 |

## 输出示例

```json
{
  "question_id": "Q0001",
  "question_text": "2022年发表的14位作者合著的论文中，第一作者是Kejun Bu的论文标题是什么？",
  "answer": {
    "text": "Nested order-disorder framework...",
    "entity_id": "paper_12345",
    "entity_type": "Paper"
  },
  "template_id": "A",
  "reasoning_chain": { ... },
  "constraints": [ ... ],
  "difficulty": "medium"
}
```

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 代码格式化
black browsecomp_v3/

# 类型检查
mypy browsecomp_v3/
```

## 相关项目

- [Browsecomp-V2](https://github.com/lzyq-hntvu/browsecomp-V2) - 模板和映射规则定义
- [QandA](https://github.com/your-org/QandA) - 学术知识图谱系统

## 许可证

MIT License
