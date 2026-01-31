"""
图遍历引擎

执行知识图谱遍历操作。
"""

from typing import List, Any, Optional, Tuple, Dict
from collections import Counter
import networkx as nx

from browsecomp_v3.core.models import Constraint, NodeType, EdgeType, ActionType, TraversalStep
from browsecomp_v3.core.exceptions import GraphTraversalException


class GraphTraversal:
    """图遍历引擎"""

    def __init__(self, graph: nx.DiGraph):
        """
        初始化图遍历引擎

        Args:
            graph: NetworkX有向图对象
        """
        self.graph = graph

    def traverse(
        self,
        start_nodes: List[str],
        constraints: List[Constraint],
        return_steps: bool = True
    ) -> Tuple[List[str], List[TraversalStep]]:
        """
        执行图遍历

        Args:
            start_nodes: 起始节点ID列表
            constraints: 约束条件列表
            return_steps: 是否返回遍历步骤

        Returns:
            (候选节点列表, 遍历步骤列表)
        """
        current_nodes = start_nodes[:]
        steps = []

        for i, constraint in enumerate(constraints):
            step = TraversalStep(
                step_id=i + 1,
                action=constraint.action,
                target_node=constraint.target_node,
                edge_type=constraint.edge_type,
                filter_condition=constraint.filter_condition,
                description=constraint.description
            )

            try:
                if constraint.action == ActionType.FILTER_CURRENT_NODE:
                    current_nodes = self._filter_nodes(
                        current_nodes,
                        constraint.filter_attribute,
                        constraint.filter_condition
                    )
                    step.result_count = len(current_nodes)

                elif constraint.action == ActionType.TRAVERSE_EDGE:
                    current_nodes = self._traverse_edge(
                        current_nodes,
                        constraint.edge_type,
                        constraint.target_node,
                        constraint.filter_condition  # 用于边属性过滤
                    )
                    step.result_count = len(current_nodes)

                elif constraint.action == ActionType.TRAVERSE_AND_COUNT:
                    current_nodes = self._traverse_and_count(
                        current_nodes,
                        constraint.edge_type,
                        constraint.filter_condition
                    )
                    step.result_count = len(current_nodes)

                else:
                    raise GraphTraversalException(f"Unknown action: {constraint.action}")

            except Exception as e:
                raise GraphTraversalException(f"Step {i + 1} failed: {e}")

            steps.append(step)

            # 早期终止
            if len(current_nodes) == 0:
                break

        return current_nodes, steps if return_steps else []

    def _filter_nodes(
        self,
        nodes: List[str],
        attribute: Optional[str],
        condition: Any
    ) -> List[str]:
        """
        过滤节点

        Args:
            nodes: 待过滤的节点ID列表
            attribute: 过滤属性名
            condition: 过滤条件

        Returns:
            过滤后的节点ID列表
        """
        if not nodes:
            return []

        if attribute is None:
            return nodes

        filtered = []
        for node_id in nodes:
            node_data = self.graph.nodes.get(node_id, {})
            attr_value = self._get_node_attribute(node_data, attribute)

            if self._match_condition(attr_value, condition):
                filtered.append(node_id)

        return filtered

    def _traverse_edge(
        self,
        nodes: List[str],
        edge_type: EdgeType,
        target_node: Optional[NodeType],
        edge_filter: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        沿边遍历

        Args:
            nodes: 当前节点ID列表
            edge_type: 边类型
            target_node: 目标节点类型（None表示不限制）
            edge_filter: 边属性过滤条件

        Returns:
            遍历后的节点ID列表
        """
        if not nodes:
            return []

        result_nodes = []
        edge_type_str = edge_type.value if hasattr(edge_type, 'value') else str(edge_type)

        for node_id in nodes:
            try:
                # 获取邻居（双向遍历）
                successors = list(self.graph.successors(node_id))
                predecessors = list(self.graph.predecessors(node_id))
                neighbors = successors + predecessors

                for neighbor_id in neighbors:
                    # 检查边类型（双向）
                    edge_data = self._get_edge_data(node_id, neighbor_id)
                    if not edge_data:
                        continue

                    if edge_data.get("edge_type") != edge_type_str:
                        continue

                    # 边属性过滤
                    if edge_filter and not self._match_edge_condition(edge_data, edge_filter):
                        continue

                    # 检查目标节点类型
                    if target_node:
                        neighbor_data = self.graph.nodes.get(neighbor_id, {})
                        neighbor_type = neighbor_data.get("type", "")
                        target_node_str = target_node.value if hasattr(target_node, 'value') else str(target_node)
                        if neighbor_type.upper() != target_node_str.upper():
                            continue

                    result_nodes.append(neighbor_id)

            except Exception:
                continue

        return list(set(result_nodes))  # 去重

    def _traverse_and_count(
        self,
        nodes: List[str],
        edge_type: EdgeType,
        condition: Any
    ) -> List[str]:
        """
        遍历并计数

        Args:
            nodes: 当前节点ID列表
            edge_type: 边类型
            condition: 计数条件（如 {"=": 5} 表示恰好5条边）

        Returns:
            满足计数条件的源节点ID列表
        """
        if not nodes:
            return []

        result_nodes = []
        edge_type_str = edge_type.value if hasattr(edge_type, 'value') else str(edge_type)

        for node_id in nodes:
            try:
                # 计算该节点的指定类型边数量
                count = 0
                successors = list(self.graph.successors(node_id))
                predecessors = list(self.graph.predecessors(node_id))
                neighbors = successors + predecessors

                for neighbor_id in neighbors:
                    edge_data = self._get_edge_data(node_id, neighbor_id)
                    if edge_data and edge_data.get("edge_type") == edge_type_str:
                        count += 1

                # 检查计数条件
                if self._match_condition(count, condition):
                    result_nodes.append(node_id)

            except Exception:
                continue

        return result_nodes

    def _get_node_attribute(self, node_data: Dict[str, Any], attribute: str) -> Any:
        """
        获取节点属性值

        支持从嵌套结构中提取值
        """
        # 直接获取
        if attribute in node_data:
            return node_data[attribute]

        # 特殊属性处理
        if attribute == "publication_year":
            pub_date = node_data.get("publication_date")
            if pub_date:
                try:
                    return int(pub_date[:4])
                except (ValueError, TypeError):
                    return None
            return None

        if attribute == "title_word_count":
            title = node_data.get("title", "")
            return len(title.split()) if title else 0

        if attribute == "reference_count":
            # 通过CITES边计数
            node_id = node_data.get("id")
            if node_id:
                count = 0
                for neighbor in self.graph.successors(node_id):
                    edge_data = self.graph.get_edge_data(node_id, neighbor)
                    if edge_data and edge_data.get("edge_type") == "CITES":
                        count += 1
                return count
            return 0

        # 默认返回None
        return None

    def _get_edge_data(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """
        获取边数据（支持双向）

        Args:
            source: 源节点ID
            target: 目标节点ID

        Returns:
            边数据字典
        """
        # 尝试正向边
        if self.graph.has_edge(source, target):
            return self.graph.get_edge_data(source, target)

        # 尝试反向边
        if self.graph.has_edge(target, source):
            return self.graph.get_edge_data(target, source)

        return None

    def _match_edge_condition(self, edge_data: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        匹配边属性条件

        Args:
            edge_data: 边数据
            condition: 条件字典

        Returns:
            是否匹配
        """
        if not condition:
            return True

        for attr, req_value in condition.items():
            attr_value = edge_data.get(attr)
            if attr_value != req_value:
                return False

        return True

    def _match_condition(self, value: Any, condition: Any) -> bool:
        """
        匹配条件

        Args:
            value: 实际值
            condition: 条件

        Returns:
            是否匹配
        """
        if condition is None:
            return True

        if value is None and condition is not None:
            return False

        # 字典形式的条件（操作符 + 值）
        if isinstance(condition, dict):
            for op, cond_value in condition.items():
                if not self._eval_operation(value, op, cond_value):
                    return False
            return True

        # 直接值比较
        return value == condition

    def _eval_operation(self, value: Any, op: str, cond_value: Any) -> bool:
        """
        执行单个条件操作

        Args:
            value: 实际值
            op: 操作符
            cond_value: 条件值

        Returns:
            是否满足条件
        """
        # 数值比较
        if op == "=":
            return value == cond_value
        elif op == "!=":
            return value != cond_value
        elif op == ">":
            return value is not None and value > cond_value
        elif op == "<":
            return value is not None and value < cond_value
        elif op == ">=":
            return value is not None and value >= cond_value
        elif op == "<=":
            return value is not None and value <= cond_value

        # 范围操作
        elif op == "between":
            if isinstance(cond_value, (list, tuple)) and len(cond_value) == 2:
                return value is not None and cond_value[0] <= value <= cond_value[1]
            return False

        # 集合操作
        elif op == "in":
            return value in cond_value
        elif op == "not_in":
            return value not in cond_value

        # 字符串操作
        elif op == "contains":
            return cond_value in str(value) if value else False
        elif op == "not_contains":
            return cond_value not in str(value) if value else True
        elif op == "starts_with":
            return str(value).startswith(cond_value) if value else False
        elif op == "ends_with":
            return str(value).endswith(cond_value) if value else False

        # 存在性
        elif op == "exists":
            return value is not None
        elif op == "not_exists":
            return value is None

        # 正则表达式
        elif op == "regex":
            import re
            try:
                return bool(re.search(cond_value, str(value))) if value else False
            except re.error:
                return False

        return False
