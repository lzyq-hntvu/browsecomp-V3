"""
Browsecomp-V3 数据模型定义

定义系统中使用的所有数据结构。
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List
from enum import Enum


class NodeType(str, Enum):
    """知识图谱节点类型"""
    PAPER = "Paper"
    AUTHOR = "Author"
    INSTITUTION = "Institution"
    VENUE = "Venue"
    ENTITY = "Entity"


class EdgeType(str, Enum):
    """知识图谱边类型"""
    HAS_AUTHOR = "HAS_AUTHOR"
    AFFILIATED_WITH = "AFFILIATED_WITH"
    PUBLISHED_IN = "PUBLISHED_IN"
    MENTIONS = "MENTIONS"
    CITES = "CITES"


class ActionType(str, Enum):
    """图操作类型"""
    FILTER_CURRENT_NODE = "filter_current_node"
    TRAVERSE_EDGE = "traverse_edge"
    TRAVERSE_AND_COUNT = "traverse_and_count"


@dataclass
class Constraint:
    """约束条件"""
    constraint_id: str
    constraint_type: str
    target_node: NodeType
    action: ActionType
    edge_type: Optional[EdgeType] = None
    filter_attribute: Optional[str] = None
    filter_condition: Any = None
    description: Optional[str] = None


@dataclass
class ConstraintSet:
    """约束集合"""
    template_id: str
    constraints: List[Constraint]
    logical_operator: str = "AND"  # AND/OR


@dataclass
class TraversalStep:
    """图遍历步骤"""
    step_id: int
    action: ActionType
    target_node: NodeType
    edge_type: Optional[EdgeType] = None
    filter_condition: Any = None
    result_count: int = 0
    description: Optional[str] = None


@dataclass
class ReasoningChain:
    """推理链"""
    template_id: str
    start_node: NodeType
    steps: List[TraversalStep] = field(default_factory=list)
    final_answer: str = ""
    total_hops: int = 0


@dataclass
class Answer:
    """答案"""
    text: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class GeneratedQuestion:
    """生成的问题"""
    question_id: str
    question_text: str
    answer: Answer
    template_id: str
    reasoning_chain: ReasoningChain
    constraint_set: ConstraintSet
    difficulty: str = "medium"  # easy/medium/hard
    validity: bool = True
    generated_at: str = ""


@dataclass
class QueryResult:
    """查询结果"""
    candidates: List[Any]
    reasoning_chain: ReasoningChain
    execution_time: float
