"""
模板加载器

从文件加载推理链模板定义。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from browsecomp_v3.core.exceptions import TemplateNotFoundException
from browsecomp_v3.core.config import get_config


class TemplateLoader:
    """模板加载器"""

    # 7个推理链模板定义
    TEMPLATES = {
        "A": {
            "name": "Paper-Author-Institution Chain",
            "description": "解决通过论文特征（发表时间、标题词数、引用数、章节结构）查找作者及其所属机构的查询",
            "start_node": "Paper",
            "frequency": 0.30,
            "applicable_constraints": [
                "C01",  # temporal
                "C02",  # author_count
                "C13",  # paper_structure
                "C03",  # institution_affiliation
                "C22",  # author_order
                "C28",  # person_name
            ],
            "base_reasoning_path": [
                "Paper -> filter_current_node",
                "Paper -> HAS_AUTHOR -> Author",
                "Author -> AFFILIATED_WITH -> Institution",
            ],
        },
        "B": {
            "name": "Person-Academic-Path Chain",
            "description": "通过人物的学术背景、教育经历、获奖记录、职业时间线来识别特定研究者身份",
            "start_node": "Author",
            "frequency": 0.22,
            "applicable_constraints": [
                "C04",  # education_degree
                "C07",  # award_honor
                "C17",  # position_title
                "C18",  # birth_info
                "C24",  # editorial_role
            ],
            "base_reasoning_path": [
                "Author -> filter_current_node",
                "Author -> HAS_AUTHOR(reverse) -> Paper",
                "Author -> AFFILIATED_WITH -> Institution",
            ],
        },
        "C": {
            "name": "Citation-Network Chain",
            "description": "通过引用关系、参考文献列表、共同引用模式来查找目标论文",
            "start_node": "Paper",
            "frequency": 0.15,
            "applicable_constraints": [
                "C01",  # temporal
                "C08",  # citation
                "C13",  # paper_structure
                "C19",  # title_format
            ],
            "base_reasoning_path": [
                "Paper -> filter_current_node",
                "Paper -> CITES -> Paper",
                "Paper -> CITES(reverse) -> Paper",
            ],
        },
        "D": {
            "name": "Collaboration-Network Chain",
            "description": "通过多篇论文之间的共同作者关系、作者排列顺序变化来识别特定论文",
            "start_node": "Paper",
            "frequency": 0.10,
            "applicable_constraints": [
                "C01",  # temporal
                "C02",  # author_count
                "C09",  # coauthor
                "C22",  # author_order
                "C23",  # publication_history
            ],
            "base_reasoning_path": [
                "Paper -> filter_current_node",
                "Paper -> HAS_AUTHOR -> Author",
                "Author -> HAS_AUTHOR(reverse) -> Paper",
            ],
        },
        "E": {
            "name": "Event-Participation Chain",
            "description": "通过会议演讲、研讨会参与、机构历史特征等事件来查找相关论文或人物",
            "start_node": "Author",
            "frequency": 0.16,
            "applicable_constraints": [
                "C03",  # institution_affiliation
                "C06",  # institution_founding
                "C16",  # conference_event
                "C21",  # location
            ],
            "base_reasoning_path": [
                "Author -> filter_current_node",
                "Author -> AFFILIATED_WITH -> Institution",
                "Paper -> MENTIONS -> Entity(event)",
            ],
        },
        "F": {
            "name": "Technical-Content Chain",
            "description": "通过具体技术规格、实验数据、方法学特征、材料属性等来找论文",
            "start_node": "Paper",
            "frequency": 0.05,
            "applicable_constraints": [
                "C10",  # research_topic
                "C11",  # method_technique
                "C12",  # data_sample
                "C20",  # technical_entity
                "C25",  # measurement_value
            ],
            "base_reasoning_path": [
                "Paper -> filter_current_node",
                "Paper -> MENTIONS -> Entity",
                "Entity -> filter_by_type",
            ],
        },
        "G": {
            "name": "Acknowledgment-Relation Chain",
            "description": "通过论文致谢部分的人际关系、感谢对象来查找特定信息",
            "start_node": "Paper",
            "frequency": 0.02,
            "applicable_constraints": [
                "C01",  # temporal
                "C14",  # acknowledgment
                "C28",  # person_name
                "C29",  # advisor
            ],
            "base_reasoning_path": [
                "Paper -> filter_current_node",
                "Paper -> MENTIONS -> Entity(acknowledged_person)",
                "Paper -> HAS_AUTHOR -> Author",
            ],
        },
    }

    def __init__(self, template_dir: Optional[Path] = None):
        """
        初始化模板加载器

        Args:
            template_dir: 模板文件目录
        """
        self.config = get_config()
        self.template_dir = template_dir or self.config.template_dir

    def get_template(self, template_id: str) -> Dict[str, Any]:
        """
        获取指定模板

        Args:
            template_id: 模板ID (A-G)

        Returns:
            模板定义字典

        Raises:
            TemplateNotFoundException: 模板不存在
        """
        if template_id not in self.TEMPLATES:
            raise TemplateNotFoundException(f"Template '{template_id}' not found")
        return self.TEMPLATES[template_id].copy()

    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模板"""
        return {k: v.copy() for k, v in self.TEMPLATES.items()}

    def get_template_frequency(self, template_id: str) -> float:
        """获取模板频率权重"""
        template = self.get_template(template_id)
        return template.get("frequency", 0.0)

    def get_applicable_constraints(self, template_id: str) -> list:
        """获取模板适用的约束类型"""
        template = self.get_template(template_id)
        return template.get("applicable_constraints", [])

    def get_start_node_type(self, template_id: str) -> str:
        """获取模板的起始节点类型"""
        template = self.get_template(template_id)
        return template.get("start_node", "Paper")
