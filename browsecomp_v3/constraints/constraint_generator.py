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
        # ===== Phase 1: 基础约束 (4种) =====
        "temporal", "author_count", "citation", "title_format",
        
        # ===== Phase 2: 多跳约束 (3种) =====
        "person_name", "author_order", "institution_affiliation",
        
        # ===== Phase 3: 高级多跳约束 (3种) =====
        "coauthor", "cited_by_author", "publication_venue",
        
        # ===== Phase 4: filter_current_node 类型约束 (8种) =====
        "institution_founding",      # C06 - 机构成立时间
        "paper_structure",           # C13 - 论文结构
        "position_title",            # C17 - 职位头衔
        "birth_info",                # C18 - 出生信息
        "location",                  # C21 - 地理位置
        "editorial_role",            # C24 - 编辑角色
        "publication_details",       # C27 - 出版详情
        "department",                # C30 - 部门
        
        # ===== Phase 5: Entity 相关约束 (9种) =====
        "education_degree",          # C04 - 教育学位
        "award_honor",               # C07 - 奖项荣誉
        "research_topic",            # C10 - 研究主题
        "method_technique",          # C11 - 方法技术
        "data_sample",               # C12 - 数据样本
        "acknowledgment",            # C14 - 致谢
        "funding",                   # C15 - 资助信息
        "conference_event",          # C16 - 会议事件
        "technical_entity",          # C20 - 技术实体
        
        # ===== Phase 6: 其他遍历约束 (3种) =====
        "publication_history",       # C23 - 发表历史
        "measurement_value",         # C25 - 测量值
        "company",                   # C26 - 公司
        "advisor",                   # C29 - 导师关系
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
        
        # ===== Phase 3 约束注入 =====
        # 以一定概率注入 Phase 3 高级多跳约束
        # 这些约束已实现但未在映射文件模板中引用
        phase3_injection_rate = 0.15  # 15% 概率注入 Phase 3 约束
        
        if random.random() < phase3_injection_rate:
            # 定义 Phase 3 虚拟约束 ID
            # 这些 ID 不存在于映射文件，但会被特殊处理
            phase3_virtual_ids = {
                'PHASE3_COAUTHOR': 'coauthor',
                'PHASE3_CITED_BY_AUTHOR': 'cited_by_author', 
                'PHASE3_PUBLICATION_VENUE': 'publication_venue'
            }
            
            # 随机选择一个 Phase 3 约束注入
            virtual_id = random.choice(list(phase3_virtual_ids.keys()))
            selected_constraint_ids.append(virtual_id)
            
            logger.debug(f"Injected Phase 3 constraint: {virtual_id}")

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
        
        # 需要去重的约束类型（基于具体实体/名称的约束）
        dedupe_types = {
            # Phase 2-3: 多跳约束
            "person_name", "institution_affiliation", "coauthor", 
            "cited_by_author", "publication_venue",
            # Phase 4: 过滤约束
            "location", "position_title", "birth_info",
            "editorial_role", "department",
            # Phase 5: Entity 相关约束
            "award_honor", "conference_event", "research_topic",
            "technical_entity", "method_technique", "data_sample",
            "acknowledgment", "funding",
            # Phase 6: 其他
            "company", "advisor", "education_degree"
        }
        
        for c in constraints:
            # 对于某些约束类型，避免重复（不同值的同类型约束会造成AND冲突）
            if c.constraint_type in dedupe_types:
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
            constraint_id: 约束ID（可能是真实 ID 或虚拟 ID）
            
        Returns:
            约束对象，如果无法实例化则返回None
        """
        try:
            # ===== 处理 Phase 3 虚拟约束 ID =====
            if constraint_id.startswith('PHASE3_'):
                # 虚拟 ID 到约束类型的映射
                phase3_mapping = {
                    'PHASE3_COAUTHOR': 'coauthor',
                    'PHASE3_CITED_BY_AUTHOR': 'cited_by_author',
                    'PHASE3_PUBLICATION_VENUE': 'publication_venue'
                }
                
                constraint_type = phase3_mapping.get(constraint_id)
                if not constraint_type:
                    logger.warning(f"Unknown Phase 3 virtual ID: {constraint_id}")
                    return None
                
                # 创建虚拟规则
                virtual_rule = {
                    'constraint_type': constraint_type,
                    'constraint_id': constraint_id,
                    'graph_operation': {
                        'action': 'multi_hop_traverse',
                        'target_node': 'Paper',
                        'edge_type': None,
                        'filter_attribute': 'name'
                    }
                }
                
                # 直接调用多跳实例化
                return self._instantiate_multi_hop_constraint(constraint_id, virtual_rule)
            
            # ===== 正常流程：从映射文件获取规则 =====
            # 获取映射规则
            rule = self.mapping_loader.get_constraint_rule(constraint_id)
            graph_op = rule.get("graph_operation", {})
            
            # 解析基本属性
            constraint_type = rule.get("constraint_type")
            action_str = graph_op.get("action")
            target_node_str = graph_op.get("target_node")
            edge_type_str = graph_op.get("edge_type")
            filter_attribute = graph_op.get("filter_attribute")
            
            # 检查是否需要多跳遍历
            if constraint_type in ["person_name", "author_order", "institution_affiliation", 
                                    "coauthor", "cited_by_author", "publication_venue"]:
                return self._instantiate_multi_hop_constraint(constraint_id, rule)
            
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

    def _instantiate_multi_hop_constraint(self, constraint_id: str, rule: dict) -> Optional[Constraint]:
        """
        实例化多跳约束
        
        Args:
            constraint_id: 约束ID
            rule: 约束规则
            
        Returns:
            多跳约束对象
        """
        try:
            constraint_type = rule.get("constraint_type")
            
            # 定义多跳遍历链
            traversal_chain = None
            requires_backtrack = False
            filter_condition = None
            description = ""
            
            # person_name: Paper → HAS_AUTHOR → Author[name=X]
            if constraint_type == "person_name":
                # 生成作者名称
                author_name = self.value_generator.generate_value(
                    constraint_id=constraint_id,
                    filter_attribute="name",
                    constraint_type="person_name",
                    target_node=NodeType.AUTHOR
                )
                
                if not author_name or author_name == "unknown":
                    return None
                
                traversal_chain = [
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                        "node_filter": {"name": {"=": author_name}}
                    }
                ]
                requires_backtrack = True  # 回溯到Paper
                filter_condition = {"name": author_name}
                description = f"作者名称: {author_name}"
            
            # author_order: Paper → HAS_AUTHOR[order=X] → Author
            elif constraint_type == "author_order":
                # 生成作者顺序 (1=first, -1=last, 2=second, etc.)
                order = random.choice([1, 1, 1, 2, -1])  # 偏向第一作者
                
                traversal_chain = [
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                        "edge_filter": {"author_order": order}
                    }
                ]
                requires_backtrack = True  # 回溯到Paper
                filter_condition = {"author_order": order}
                description = f"作者顺序: 第{order}作者" if order > 0 else "作者顺序: 最后作者"
            
            # institution_affiliation: Paper → HAS_AUTHOR → Author → AFFILIATED_WITH → Institution[name=X]
            elif constraint_type == "institution_affiliation":
                # 生成机构名称
                institution_name = self.value_generator.generate_value(
                    constraint_id=constraint_id,
                    filter_attribute="name",
                    constraint_type="institution_affiliation",
                    target_node=NodeType.INSTITUTION
                )
                
                if not institution_name or institution_name == "unknown":
                    return None
                
                traversal_chain = [
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                    },
                    {
                        "edge_type": "AFFILIATED_WITH",
                        "target_node": "Institution",
                        "node_filter": {"name": {"=": institution_name}}
                    }
                ]
                requires_backtrack = True  # 回溯到Paper
                filter_condition = {"institution_name": institution_name}
                description = f"机构隶属: {institution_name}"
            
            # coauthor: Paper A → HAS_AUTHOR → Author X → HAS_AUTHOR(reverse) → Paper B → HAS_AUTHOR → Author Y[name=Z]
            # This is a 5-hop traversal to find papers whose authors have a specific coauthor
            elif constraint_type == "coauthor":
                # 生成合作者名称
                coauthor_name = self.value_generator.generate_value(
                    constraint_id=constraint_id,
                    filter_attribute="name",
                    constraint_type="coauthor",
                    target_node=NodeType.AUTHOR
                )
                
                if not coauthor_name or coauthor_name == "unknown":
                    return None
                
                traversal_chain = [
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                        "description": "Get authors of the paper"
                    },
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Paper",
                        "direction": "reverse",
                        "description": "Get other papers by these authors"
                    },
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                        "node_filter": {"name": {"=": coauthor_name}},
                        "description": f"Filter for papers with coauthor {coauthor_name}"
                    },
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Paper",
                        "direction": "reverse",
                        "description": "Get papers by this coauthor"
                    },
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                        "description": "Get all authors of these papers"
                    }
                ]
                requires_backtrack = True  # 回溯到Paper
                filter_condition = {"coauthor_name": coauthor_name}
                description = f"合作者: {coauthor_name}"
            
            # cited_by_author: Paper A → CITES(reverse) → Paper B → HAS_AUTHOR → Author[name=X]
            # 找到被特定作者引用的论文（反向+2跳）
            elif constraint_type == "cited_by_author":
                # 生成引用作者名称
                citing_author_name = self.value_generator.generate_value(
                    constraint_id=constraint_id,
                    filter_attribute="name",
                    constraint_type="cited_by_author",
                    target_node=NodeType.AUTHOR
                )
                
                if not citing_author_name or citing_author_name == "unknown":
                    return None
                
                traversal_chain = [
                    {
                        "edge_type": "CITES",
                        "target_node": "Paper",
                        "direction": "reverse",
                        "description": "Get papers that cite this paper"
                    },
                    {
                        "edge_type": "HAS_AUTHOR",
                        "target_node": "Author",
                        "node_filter": {"name": {"=": citing_author_name}},
                        "description": f"Filter for citing papers by {citing_author_name}"
                    }
                ]
                requires_backtrack = True  # 回溯到Paper
                filter_condition = {"cited_by_author": citing_author_name}
                description = f"被引作者: {citing_author_name}"
            
            # publication_venue: Paper → PUBLISHED_IN → Venue[name=X]
            # 找到发表在特定期刊/会议的论文（2跳）
            elif constraint_type == "publication_venue":
                # 生成期刊/会议名称
                venue_name = self.value_generator.generate_value(
                    constraint_id=constraint_id,
                    filter_attribute="name",
                    constraint_type="publication_venue",
                    target_node=NodeType.VENUE
                )
                
                if not venue_name or venue_name == "unknown":
                    return None
                
                traversal_chain = [
                    {
                        "edge_type": "PUBLISHED_IN",
                        "target_node": "Venue",
                        "node_filter": {"name": {"=": venue_name}},
                        "description": f"Filter for papers published in {venue_name}"
                    }
                ]
                requires_backtrack = True  # 回溯到Paper
                filter_condition = {"venue_name": venue_name}
                description = f"发表期刊: {venue_name}"
            
            if not traversal_chain:
                return None
            
            # 创建多跳约束对象
            constraint = Constraint(
                constraint_id=constraint_id,
                constraint_type=constraint_type,
                target_node=NodeType.PAPER,  # 最终目标是Paper节点
                action=ActionType.MULTI_HOP_TRAVERSE,
                filter_condition=filter_condition,
                description=description,
                traversal_chain=traversal_chain,
                requires_backtrack=requires_backtrack
            )
            
            return constraint
            
        except Exception as e:
            logger.warning(f"Failed to instantiate multi-hop constraint {constraint_id}: {e}")
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
