"""
查询执行器

执行基于约束的图查询。
"""

from typing import List, Dict, Any, Optional
import time

from browsecomp_v3.core.models import ConstraintSet, ReasoningChain, QueryResult
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.traversal import GraphTraversal
from browsecomp_v3.core.config import get_config


class QueryExecutor:
    """查询执行器"""

    def __init__(self, kg_loader: Optional[KnowledgeGraphLoader] = None):
        """
        初始化查询执行器

        Args:
            kg_loader: 知识图谱加载器
        """
        self.config = get_config()
        self.kg_loader = kg_loader or KnowledgeGraphLoader()
        self.graph = self.kg_loader.load()
        self.traversal = GraphTraversal(self.graph)

    def execute(
        self,
        constraint_set: ConstraintSet,
        start_nodes: Optional[List[str]] = None
    ) -> QueryResult:
        """
        执行查询

        Args:
            constraint_set: 约束集合
            start_nodes: 起始节点列表（None则使用所有节点）

        Returns:
            查询结果
        """
        start_time = time.time()

        # 确定起始节点
        if start_nodes is None:
            # 根据模板确定起始节点类型
            from browsecomp_v3.templates.template_loader import TemplateLoader
            template_loader = TemplateLoader()
            start_node_type = template_loader.get_start_node_type(constraint_set.template_id)
            start_nodes = self.kg_loader.get_nodes_by_type(start_node_type)

        # 执行遍历
        candidates, steps = self.traversal.traverse(
            start_nodes=start_nodes,
            constraints=constraint_set.constraints,
            return_steps=True
        )

        execution_time = time.time() - start_time

        # 构建推理链
        reasoning_chain = ReasoningChain(
            template_id=constraint_set.template_id,
            start_node=candidates[0] if candidates else "",
            steps=steps,
            total_hops=len(steps)
        )

        return QueryResult(
            candidates=candidates,
            reasoning_chain=reasoning_chain,
            execution_time=execution_time
        )

    def execute_batch(
        self,
        constraint_sets: List[ConstraintSet]
    ) -> List[QueryResult]:
        """
        批量执行查询

        Args:
            constraint_sets: 约束集合列表

        Returns:
            查询结果列表
        """
        results = []
        for constraint_set in constraint_sets:
            try:
                result = self.execute(constraint_set)
                results.append(result)
            except Exception as e:
                # 记录错误但继续处理
                continue
        return results
