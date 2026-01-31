"""
Browsecomp-V3: 约束驱动的复杂学术问题生成器

基于 QandA 学术知识图谱，使用 7 个推理链模板和 30 个约束映射规则
自动生成 Browsecomp 风格的多跳推理问答对。
"""

__version__ = "0.1.0"
__author__ = "Hu Family"

from browsecomp_v3.core.models import (
    Constraint,
    ConstraintSet,
    ReasoningChain,
    GeneratedQuestion,
)

__all__ = [
    "__version__",
    "__author__",
    "Constraint",
    "ConstraintSet",
    "ReasoningChain",
    "GeneratedQuestion",
]
