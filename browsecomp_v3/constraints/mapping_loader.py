"""
约束映射规则加载器

从JSON文件加载约束映射规则。
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from browsecomp_v3.core.exceptions import ConstraintParseException
from browsecomp_v3.core.config import get_config


class MappingLoader:
    """约束映射规则加载器"""

    def __init__(self, mapping_path: Optional[Path] = None):
        """
        初始化映射加载器

        Args:
            mapping_path: 映射规则文件路径
        """
        self.config = get_config()
        self.mapping_path = mapping_path or self.config.template_dir / self.config.constraint_mapping_file
        self._mappings: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        加载约束映射规则

        Returns:
            映射规则字典
        """
        if self._mappings is None:
            try:
                with open(self.mapping_path, 'r', encoding='utf-8') as f:
                    self._mappings = json.load(f)
            except FileNotFoundError:
                # 如果文件不存在，使用内置的默认映射
                self._mappings = self._get_default_mappings()
            except json.JSONDecodeError as e:
                raise ConstraintParseException(f"Invalid JSON in mapping file: {e}")

        return self._mappings

    def get_constraint_rule(self, constraint_id: str) -> Dict[str, Any]:
        """
        获取指定约束的映射规则

        Args:
            constraint_id: 约束ID (C01-C30)

        Returns:
            约束规则字典
        """
        mappings = self.load()
        for rule in mappings.get("constraint_mappings", []):
            if rule.get("constraint_id") == constraint_id:
                return rule
        raise ConstraintParseException(f"Constraint rule '{constraint_id}' not found")

    def get_rules_by_type(self, constraint_type: str) -> List[Dict[str, Any]]:
        """
        按类型获取约束规则

        Args:
            constraint_type: 约束类型

        Returns:
            约束规则列表
        """
        mappings = self.load()
        return [
            rule for rule in mappings.get("constraint_mappings", [])
            if rule.get("constraint_type") == constraint_type
        ]

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """获取所有约束规则"""
        mappings = self.load()
        return mappings.get("constraint_mappings", [])

    def lookup_by_keywords(self, text: str) -> List[Dict[str, Any]]:
        """
        根据关键词查找匹配的约束规则

        Args:
            text: 要匹配的文本

        Returns:
            匹配的约束规则列表
        """
        text_lower = text.lower()
        matches = []

        for rule in self.get_all_rules():
            for keyword in rule.get("trigger_keywords", []):
                if keyword.lower() in text_lower:
                    matches.append(rule)
                    break

        return matches

    def _get_default_mappings(self) -> Dict[str, Any]:
        """获取默认的约束映射规则（内置fallback）"""
        return {
            "schema_version": "1.0",
            "node_types": ["Paper", "Author", "Institution", "Venue", "Entity"],
            "edge_types": ["HAS_AUTHOR", "AFFILIATED_WITH", "PUBLISHED_IN", "MENTIONS", "CITES"],
            "constraint_mappings": [
                {
                    "constraint_id": "C01",
                    "constraint_type": "temporal",
                    "constraint_name": "时间/发表年份约束",
                    "trigger_keywords": ["published between", "before", "after", "in the 1970s"],
                    "graph_operation": {
                        "action": "filter_current_node",
                        "target_node": None,
                        "edge_type": None,
                        "filter_attribute": "publication_year",
                        "filter_condition": "temporal_range",
                    },
                },
                # ... 可以添加更多默认规则
            ],
        }
