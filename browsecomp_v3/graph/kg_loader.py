"""
知识图谱加载器

从文件加载QandA知识图谱。
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import networkx as nx

from browsecomp_v3.core.exceptions import KnowledgeGraphException
from browsecomp_v3.core.config import get_config

logger = logging.getLogger(__name__)


class KnowledgeGraphLoader:
    """知识图谱加载器"""

    def __init__(self, kg_path: Optional[str] = None):
        """
        初始化知识图谱加载器

        Args:
            kg_path: 知识图谱文件路径
        """
        self.config = get_config()
        self.kg_path = kg_path or self.config.kg_path
        self._graph: Optional[nx.Graph] = None
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []

    def load(self) -> nx.Graph:
        """
        加载知识图谱

        Returns:
            NetworkX图对象
        """
        if self._graph is not None:
            logger.debug("Using cached knowledge graph")
            return self._graph

        if self.kg_path is None:
            raise KnowledgeGraphException("Knowledge graph path not configured")

        kg_file = Path(self.kg_path)
        if not kg_file.exists():
            raise KnowledgeGraphException(f"Knowledge graph file not found: {self.kg_path}")

        try:
            logger.info(f"Loading knowledge graph from {self.kg_path}")
            with open(kg_file, 'r', encoding='utf-8') as f:
                kg_data = json.load(f)

            self._graph = nx.DiGraph()  # 有向图
            self._parse_kg_data(kg_data)

            logger.info(f"Loaded knowledge graph: {self.node_count} nodes, {self.edge_count} edges")
            return self._graph

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in knowledge graph file: {e}")
            raise KnowledgeGraphException(f"Invalid JSON in knowledge graph file: {e}")
        except Exception as e:
            logger.error(f"Failed to load knowledge graph: {e}")
            raise KnowledgeGraphException(f"Failed to load knowledge graph: {e}")

    def _parse_kg_data(self, kg_data: Dict[str, Any]):
        """解析知识图谱数据 - QandA格式"""
        metadata = kg_data.get("metadata", {})

        # 解析节点 - QandA格式: 属性直接在节点对象中
        nodes_data = kg_data.get("nodes", [])
        for node in nodes_data:
            node_id = node.get("id")
            if node_id:
                # 保存完整节点数据
                self._nodes[node_id] = node

                # 添加到图，排除id字段
                node_attrs = {k: v for k, v in node.items() if k != "id"}
                # 规范化type为大写（为了匹配枚举）
                if "type" in node_attrs:
                    node_attrs["original_type"] = node_attrs["type"]
                    node_attrs["type"] = node_attrs["type"].upper()
                self._graph.add_node(node_id, **node_attrs)

        # 解析边 - QandA格式: source_id, target_id, relation_type
        edges_data = kg_data.get("edges", [])
        for edge in edges_data:
            source = edge.get("source_id")
            target = edge.get("target_id")
            edge_type = edge.get("relation_type")
            if source and target and edge_type:
                # 边属性直接在边对象中
                edge_attrs = {k: v for k, v in edge.items()
                             if k not in ["source_id", "target_id", "relation_type"]}
                self._graph.add_edge(
                    source,
                    target,
                    edge_type=edge_type,
                    **edge_attrs
                )

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点数据"""
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> List[str]:
        """获取指定类型的所有节点ID"""
        # 支持大小写不敏感的匹配
        node_type_normalized = node_type.upper()
        return [
            node_id for node_id, node_data in self._nodes.items()
            if node_data.get("type", "").upper() == node_type_normalized
        ]

    def get_all_nodes(self) -> Dict[str, Dict[str, Any]]:
        """获取所有节点"""
        return self._nodes.copy()

    def get_graph(self) -> nx.Graph:
        """获取图对象"""
        if self._graph is None:
            self.load()
        return self._graph

    @property
    def node_count(self) -> int:
        """节点数量"""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """边数量"""
        return self._graph.number_of_edges() if self._graph else 0
