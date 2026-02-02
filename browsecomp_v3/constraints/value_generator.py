"""
约束值生成器

根据知识图谱的实际数据生成约束的具体值。
"""

import random
import re
from typing import Any, List, Optional, Dict
from datetime import datetime

from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.core.models import NodeType, EdgeType


class ConstraintValueGenerator:
    """约束值生成器"""

    def __init__(self, kg_loader: Optional[KnowledgeGraphLoader] = None):
        """
        初始化值生成器

        Args:
            kg_loader: 知识图谱加载器
        """
        self.kg_loader = kg_loader or KnowledgeGraphLoader()
        self.kg = self.kg_loader.load()
        self._sample_cache: Dict[str, List[Any]] = {}

    def generate_value(
        self,
        constraint_id: str,
        filter_attribute: str,
        constraint_type: str,
        target_node: Optional[NodeType] = None
    ) -> Any:
        """
        为指定约束生成具体值

        Args:
            constraint_id: 约束ID
            filter_attribute: 过滤属性名
            constraint_type: 约束类型
            target_node: 目标节点类型

        Returns:
            约束的具体值
        """
        # 时间约束
        if constraint_type == "temporal":
            return self._generate_temporal_value(filter_attribute)

        # 作者数量约束
        if constraint_type == "author_count":
            return self._generate_count_value("author_count")

        # 人名匹配约束
        if constraint_type == "person_name" or constraint_id == "C28":
            return self._generate_person_name_value()

        # 作者顺序约束
        if constraint_type == "author_order":
            return self._generate_author_order_value()

        # 机构相关约束
        if constraint_type in ["institution_affiliation", "institution_founding"]:
            return self._generate_institution_value(filter_attribute)

        # 引用约束
        if constraint_type == "citation":
            return self._generate_citation_value()

        # 标题格式约束
        if constraint_type == "title_format":
            return self._generate_title_value()

        # 技术实体约束
        if constraint_type == "technical_entity":
            return self._generate_entity_value()

        # 论文结构约束
        if constraint_type == "paper_structure":
            return self._generate_paper_structure_value(filter_attribute)

        # 研究主题约束
        if constraint_type == "research_topic":
            return self._generate_research_topic_value()

        # 方法技术约束
        if constraint_type == "method_technique":
            return self._generate_method_technique_value()

        # 地点位置约束
        if constraint_type == "location":
            return self._generate_location_value()

        # 职位头衔约束
        if constraint_type == "position_title":
            return self._generate_position_title_value()

        # 奖项荣誉约束
        if constraint_type == "award_honor":
            return self._generate_award_honor_value()

        # 出生信息约束
        if constraint_type == "birth_info":
            return self._generate_birth_info_value()

        # 编辑角色约束
        if constraint_type == "editorial_role":
            return self._generate_editorial_role_value()

        # 会议事件约束
        if constraint_type == "conference_event":
            return self._generate_conference_event_value()
        
        # Phase 3 约束：合作作者
        if constraint_type == "coauthor":
            return self._generate_person_name_value()  # 复用人名生成
        
        # Phase 3 约束：被引作者
        if constraint_type == "cited_by_author":
            return self._generate_person_name_value()  # 复用人名生成
        
        # Phase 3 约束：发表期刊
        if constraint_type == "publication_venue":
            return self._generate_venue_value()

        # 默认：返回一个合理的默认值
        return self._get_default_value(constraint_type)

    def _generate_temporal_value(self, attribute: str) -> Dict[str, Any]:
        """生成时间约束值"""
        # 获取所有有publication_year的论文
        years = []
        for node_id, node_data in self.kg_loader.get_all_nodes().items():
            if node_data.get("type") == "paper":
                pub_date = node_data.get("publication_date")
                if pub_date:
                    try:
                        year = int(pub_date[:4])
                        years.append(year)
                    except (ValueError, TypeError):
                        continue

        if not years:
            # 默认值
            return {"=": 2022}

        # 生成各种时间约束
        constraint_type = random.choice([
            "exact",      # 精确年份
            "range",      # 年份范围
            "before",     # 之前
            "after",      # 之后
        ])

        min_year, max_year = min(years), max(years)

        if constraint_type == "exact":
            year = random.choice(years)
            return {"=": year}

        elif constraint_type == "range":
            # 随机范围
            start = random.randint(min_year, max_year - 1)
            end = random.randint(start + 1, max_year)
            return {"between": [start, end]}

        elif constraint_type == "before":
            year = random.randint(min_year + 1, max_year)
            return {"<": year}

        elif constraint_type == "after":
            year = random.randint(min_year, max_year - 1)
            return {">": year}

    def _generate_count_value(self, attribute: str) -> Dict[str, int]:
        """生成计数约束值"""
        # 从实际数据采样
        if attribute == "author_count":
            counts = []
            for node_id, node_data in self.kg_loader.get_all_nodes().items():
                if node_data.get("type") == "paper":
                    # 通过HAS_AUTHOR边计数
                    count = 0
                    for neighbor in self.kg.neighbors(node_id):
                        edge_data = self.kg.get_edge_data(node_id, neighbor)
                        if edge_data and edge_data.get("edge_type") == "HAS_AUTHOR":
                            count += 1
                    if count > 0:
                        counts.append(count)

            if counts:
                # 选择一个常见的计数
                count = random.choice(counts)
                return {"=": count}

        return {"=": random.randint(1, 20)}

    def _generate_person_name_value(self) -> str:
        """生成人名约束值"""
        authors = self.kg_loader.get_nodes_by_type("Author")
        if authors:
            author_id = random.choice(authors)
            author_data = self.kg_loader.get_node(author_id)
            return author_data.get("name", "Unknown Author")
        return "John Doe"

    def _generate_author_order_value(self) -> int:
        """生成作者顺序约束值"""
        return random.choice([1, 2, 3])

    def _generate_institution_value(self, attribute: str) -> Any:
        """生成机构约束值"""
        institutions = self.kg_loader.get_nodes_by_type("Institution")
        if institutions:
            inst_id = random.choice(institutions)
            inst_data = self.kg_loader.get_node(inst_id)

            if attribute == "founded_year":
                # 从机构数据中获取成立年份
                # 如果没有，返回一个合理的范围
                return {"between": [1800, 2000]}
            else:
                return inst_data.get("name", "Unknown Institution")

        return "Stanford University"

    def _generate_citation_value(self) -> Dict[str, int]:
        """生成引用约束值"""
        # 从实际数据采样引用数
        citation_counts = []
        for node_id, node_data in self.kg_loader.get_all_nodes().items():
            if node_data.get("type") == "paper":
                count = node_data.get("citation_count")
                if count and count > 0:
                    citation_counts.append(count)

        if citation_counts:
            count = random.choice(citation_counts)
            return {">": count}

        return {">": 10}

    def _generate_title_value(self) -> Dict[str, str]:
        """生成标题约束值"""
        papers = self.kg_loader.get_nodes_by_type("Paper")
        if papers:
            paper_id = random.choice(papers)
            paper_data = self.kg_loader.get_node(paper_id)
            title = paper_data.get("title", "")

            # 提取标题的最后一个词
            words = title.split()
            if words:
                last_word = words[-1].rstrip(".")

                return {"ends_with": last_word}

        return {"ends_with": "problems"}

    def _generate_entity_value(self) -> str:
        """生成实体约束值"""
        entities = self.kg_loader.get_nodes_by_type("Entity")
        if entities and len(entities) > 10:
            # 随机选择一个实体
            entity_id = random.choice(entities[:100])  # 限制范围
            entity_data = self.kg_loader.get_node(entity_id)
            return entity_data.get("name", "silicon")

        return "silicon"

    def _sample_attribute_value(
        self,
        attribute: str,
        target_node: Optional[NodeType]
    ) -> Any:
        """
        从知识图谱采样属性值

        Args:
            attribute: 属性名
            target_node: 目标节点类型

        Returns:
            采样的属性值
        """
        cache_key = f"{target_node}_{attribute}" if target_node else attribute

        if cache_key not in self._sample_cache:
            values = []
            nodes = self.kg_loader.get_nodes_by_type(target_node.value) if target_node else []

            for node_id in nodes[:500]:  # 限制采样数量
                node_data = self.kg_loader.get_node(node_id)
                value = node_data.get(attribute)
                if value is not None:
                    values.append(value)

            self._sample_cache[cache_key] = values

        values = self._sample_cache[cache_key]
        if values:
            return random.choice(values)

        return None

    def _generate_paper_structure_value(self, attribute: str) -> Dict[str, Any]:
        """生成论文结构约束值"""
        # 生成常见的论文结构约束
        if attribute == "reference_count":
            # 从实际数据采样引用数
            counts = []
            for node_id, node_data in self.kg_loader.get_all_nodes().items():
                if node_data.get("type") == "paper":
                    # 通过CITES边计数
                    count = 0
                    for neighbor in self.kg.neighbors(node_id):
                        edge_data = self.kg.get_edge_data(node_id, neighbor)
                        if edge_data and edge_data.get("edge_type") == "CITES":
                            count += 1
                    if count > 0:
                        counts.append(count)

            if counts:
                return {">": random.choice(counts)}
            return {">": 10}

        elif attribute == "title_word_count":
            # 生成标题词数约束
            return {"=": random.randint(5, 15)}

        elif attribute == "author_count":
            return self._generate_count_value("author_count")

        else:
            # 默认返回存在性约束
            return {"exists": True}

    def _generate_research_topic_value(self) -> str:
        """生成研究主题约束值"""
        topics = ["machine learning", "deep learning", "computer vision", "natural language processing",
                  "quantum computing", "materials science", "nanotechnology", "climate change"]
        return random.choice(topics)

    def _generate_method_technique_value(self) -> str:
        """生成方法技术约束值"""
        techniques = ["neural networks", "reinforcement learning", "convolutional neural networks",
                      "transformer", "BERT", "GPT", "molecular dynamics", "density functional theory"]
        return random.choice(techniques)

    def _generate_location_value(self) -> str:
        """生成地点位置约束值"""
        locations = ["California", "New York", "Massachusetts", "Beijing", "Shanghai",
                     "Tokyo", "London", "Paris", "Berlin", "Singapore"]
        return random.choice(locations)

    def _generate_position_title_value(self) -> str:
        """生成职位头衔约束值"""
        positions = ["Professor", "Associate Professor", "Assistant Professor",
                     "Postdoctoral Researcher", "PhD Student", "Research Scientist"]
        return random.choice(positions)

    def _generate_award_honor_value(self) -> str:
        """生成奖项荣誉约束值"""
        awards = ["Nobel Prize", "Turing Award", "Fields Medal", "Best Paper Award",
                  "NSF CAREER Award", "IEEE Fellow", "ACM Fellow"]
        return random.choice(awards)

    def _generate_birth_info_value(self) -> Dict[str, Any]:
        """生成出生信息约束值"""
        return {"between": [1950, 1995]}

    def _generate_editorial_role_value(self) -> str:
        """生成编辑角色约束值"""
        roles = ["Editor-in-Chief", "Associate Editor", "Editorial Board Member",
                 "Reviewer", "Area Chair"]
        return random.choice(roles)

    def _generate_conference_event_value(self) -> str:
        """生成会议事件约束值"""
        events = ["NeurIPS", "ICML", "ACL", "CVPR", "ICCV", "AAAI", "IJCAI", "ICLR"]
        return random.choice(events)
    
    def _generate_venue_value(self) -> str:
        """
        生成期刊/会议名称约束值
        
        从知识图谱中提取真实的 Venue 名称
        """
        venues = []
        for node_id, node_data in self.kg.nodes(data=True):
            node_type = node_data.get("type", "").upper()
            if node_type == "VENUE":
                venue_name = node_data.get("name")
                if venue_name:
                    venues.append(venue_name)
        
        if venues:
            return random.choice(venues)
        else:
            # 如果知识图谱中没有 Venue，返回常见期刊名称
            default_venues = ["Nature", "Science", "Cell", "PNAS", "Nature Communications"]
            return random.choice(default_venues)

    def _get_default_value(self, constraint_type: str) -> Any:
        """获取未知约束类型的默认值"""
        # 对于无法识别的约束类型，返回一个合理的默认值
        if "count" in constraint_type:
            return {">": 1}
        elif "year" in constraint_type or "temporal" in constraint_type:
            return {"between": [2010, 2022]}
        else:
            # 返回字符串类型的默认值
            return "unknown"

