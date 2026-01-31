"""
约束生成器

根据模板生成约束条件组合。
"""

import logging
import random
from typing import List, Optional, Any, Set

from browsecomp_v3.core.models import Constraint, ConstraintSet, NodeType, ActionType, EdgeType
from browsecomp_v3.core.config import get_config
from browsecomp_v3.templates.template_loader import TemplateLoader
from browsecomp_v3.constraints.mapping_loader import MappingLoader
from browsecomp_v3.constraints.value_generator import ConstraintValueGenerator

logger = logging.getLogger(__name__)


class ConstraintGenerator:
    """约束生成器"""

    # 支持的约束类型白名单
    VALID_CONSTRAINT_TYPES: Set[str] = {
        "temporal", "author_count", "citation", "title_format",
        # 未来可扩展：更多约束类型需要实现多跳遍历后添加
    }

    def __init__(self, kg_loader=None):
        """
        初始化约束生成器

        Args:
            kg_loader: 知识图谱加载器（用于生成约束值）
        """
        self.config = get_config()
        self.template_loader = TemplateLoader()
        self.mapping_loader = MappingLoader()
        self.value_generator = ConstraintValueGenerator(kg_loader)

        # 从配置读取有效约束类型（如果配置了则覆盖默认值）
        if hasattr(self.config, 'valid_constraint_types') and self.config.valid_constraint_types is not None:
            self.valid_constraint_types = set(self.config.valid_constraint_types)
        else:
            self.valid_constraint_types = self.VALID_CONSTRAINT_TYPES.copy()

    def _pre_filter_valid_constraints(self, constraint_ids: List[str]) -> List[str]:
        """
        预过滤约束ID，只保留属于有效约束类型的约束

        Args:
            constraint_ids: 约束ID列表

        Returns:
            过滤后的约束ID列表
        """
        valid_ids = []
        for constraint_id in constraint_ids:
            try:
                rule = self.mapping_loader.get_constraint_rule(constraint_id)
                constraint_type = rule.get("constraint_type")
                if constraint_type in self.valid_constraint_types:
                    valid_ids.append(constraint_id)
            except Exception:
                # 如果无法获取规则，跳过该约束
                continue
        return valid_ids

    def _filter_invalid_constraints(self, constraints: List[Constraint]) -> List[Constraint]:
        """
        过滤无效约束

        Args:
            constraints: 约束列表

        Returns:
            过滤后的有效约束列表
        """
        valid_constraints = []

        for c in constraints:
            # 检查约束类型是否在白名单中
            if c.constraint_type not in self.valid_constraint_types:
                logger.debug(f"Skipping constraint type '{c.constraint_type}' (not in valid types)")
                continue

            # 检查约束条件是否存在
            if c.filter_condition is None:
                logger.debug(f"Skipping constraint {c.constraint_id} (filter_condition is None)")
                continue

            # 检查约束条件是否为 "unknown"
            if c.filter_condition == "unknown":
                logger.debug(f"Skipping constraint {c.constraint_id} (filter_condition is 'unknown')")
                continue

            # 检查是否存在性约束（exists: True 不提供实际过滤）
            if isinstance(c.filter_condition, dict) and "exists" in c.filter_condition:
                logger.debug(f"Skipping constraint {c.constraint_id} (exists constraint provides no filtering)")
                continue

            valid_constraints.append(c)

        return valid_constraints

    def generate(
        self,
        template_id: str,
        min_constraints: Optional[int] = None,
        max_constraints: Optional[int] = None,
    ) -> ConstraintSet:
        """
        为指定模板生成约束组合

        Args:
            template_id: 模板ID
            min_constraints: 最小约束数量
            max_constraints: 最大约束数量

        Returns:
            约束集合
        """
        min_constraints = min_constraints or self.config.default_min_constraints
        max_constraints = max_constraints or self.config.default_max_constraints

        # 获取模板适用的约束类型，并预过滤只保留有效类型
        applicable_constraint_ids = self.template_loader.get_applicable_constraints(template_id)

        if not applicable_constraint_ids:
            raise ValueError(f"No applicable constraints for template '{template_id}'")

        # 预过滤：只保留属于有效约束类型的约束ID
        valid_applicable_ids = self._pre_filter_valid_constraints(applicable_constraint_ids)

        if not valid_applicable_ids:
            raise ValueError(f"No valid constraint types available for template '{template_id}'")

        # 随机确定约束数量
        num_constraints = random.randint(min_constraints, max_constraints)

        # 随机选择约束类型（可以重复）
        selected_constraint_ids = random.choices(
            valid_applicable_ids,
            k=min(num_constraints, len(valid_applicable_ids) * 2)  # 允许重复
        )

        # 生成具体约束
        constraints = []
        for constraint_id in selected_constraint_ids:
            constraint = self._instantiate_constraint(constraint_id)
            if constraint:
                constraints.append(constraint)

        if not constraints:
            raise ValueError(f"Failed to generate any constraints for template '{template_id}'")

        # 去重（保持顺序）
        # 避免重复的约束类型（不同值的同类型约束会造成AND冲突）
        seen_types = set()
        seen_ids = set()
        unique_constraints = []
        for c in constraints:
            # 对于某些约束类型（如person_name, institution_affiliation），避免重复
            if c.constraint_type in ["person_name", "institution_affiliation", "location",
                                      "position_title", "award_honor", "birth_info",
                                      "editorial_role", "conference_event", "research_topic"]:
                if c.constraint_type in seen_types:
                    continue
                seen_types.add(c.constraint_type)

            # 使用约束ID去重（避免完全相同的约束）
            if c.constraint_id not in seen_ids:
                seen_ids.add(c.constraint_id)
                unique_constraints.append(c)

        # 最终过滤（移除unknown值等）
        filtered_constraints = self._filter_invalid_constraints(unique_constraints)

        if not filtered_constraints:
            raise ValueError(f"No valid constraints after filtering for template '{template_id}'")

        logger.debug(f"Generated {len(filtered_constraints)} valid constraints for template '{template_id}'")

        return ConstraintSet(
            template_id=template_id,
            constraints=filtered_constraints,
            logical_operator="AND"
        )

    def _instantiate_constraint(self, constraint_id: str) -> Optional[Constraint]:
        """
        实例化单个约束

        Args:
            constraint_id: 约束ID

        Returns:
            约束对象，如果无法实例化则返回None
        """
        try:
            # 获取映射规则
            rule = self.mapping_loader.get_constraint_rule(constraint_id)
            graph_op = rule.get("graph_operation", {})

            # 解析基本属性
            constraint_type = rule.get("constraint_type")
            action_str = graph_op.get("action")
            target_node_str = graph_op.get("target_node")
            edge_type_str = graph_op.get("edge_type")
            filter_attribute = graph_op.get("filter_attribute")

            # 转换为枚举类型
            action = ActionType(action_str)
            target_node = NodeType(target_node_str) if target_node_str else None
            edge_type = EdgeType(edge_type_str) if edge_type_str else None

            # 生成具体的约束值
            filter_condition = self.value_generator.generate_value(
                constraint_id=constraint_id,
                filter_attribute=filter_attribute,
                constraint_type=constraint_type,
                target_node=target_node
            )

            # 生成描述
            description = self._generate_constraint_description(
                rule.get("constraint_name", ""),
                filter_condition
            )

            # 创建约束对象
            constraint = Constraint(
                constraint_id=constraint_id,
                constraint_type=constraint_type,
                target_node=target_node,
                action=action,
                edge_type=edge_type,
                filter_attribute=filter_attribute,
                filter_condition=filter_condition,
                description=description,
            )

            return constraint

        except Exception as e:
            # 使用 logging 记录错误
            logger.warning(f"Failed to instantiate constraint {constraint_id}: {e}")
            return None

    def _generate_constraint_description(self, base_name: str, condition: Any) -> str:
        """
        生成约束的自然语言描述

        Args:
            base_name: 约束基础名称
            condition: 约束条件

        Returns:
            自然语言描述
        """
        if condition is None:
            return base_name

        # 根据条件类型生成描述
        if isinstance(condition, dict):
            op = list(condition.keys())[0]
            value = condition[op]

            if op == "=":
                return f"{base_name} = {value}"
            elif op == ">":
                return f"{base_name} > {value}"
            elif op == "<":
                return f"{base_name} < {value}"
            elif op == ">=":
                return f"{base_name} >= {value}"
            elif op == "<=":
                return f"{base_name} <= {value}"
            elif op == "between":
                return f"{base_name} 在 {value[0]} 到 {value[1]} 之间"
            elif op == "in":
                return f"{base_name} 在 {value} 中"
            elif op == "contains":
                return f"{base_name} 包含 '{value}'"
            elif op == "ends_with":
                return f"{base_name} 以 '{value}' 结尾"
            elif op == "starts_with":
                return f"{base_name} 以 '{value}' 开头"

        return f"{base_name}: {condition}"
