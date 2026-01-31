"""
问题生成器

将约束转换为自然语言问题。
"""

import random
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from browsecomp_v3.core.models import (
    ConstraintSet, ReasoningChain, GeneratedQuestion, Answer, Constraint
)
from browsecomp_v3.core.exceptions import QuestionGenerationException
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader


class QuestionGenerator:
    """问题生成器"""

    # 约束类型到问题短语的映射
    CONSTRAINT_PHRASES = {
        "temporal": [
            "{op}{year}年发表",
            "{year}年{op}的论文",
        ],
        "author_count": [
            "{count}位作者合著",
            "作者数量为{count}",
            "由{count}人合写",
        ],
        "person_name": [
            "作者是{name}",
            "{name}参与的",
            "包含作者{name}",
        ],
        "author_order": [
            "{order}作者是",
            "第{order}作者为",
        ],
        "institution_affiliation": [
            "来自{institution}",
            "{institution}的",
            "隶属于{institution}",
        ],
        "citation": [
            "引用数{op}{count}",
            "被引用{count}次",
        ],
        "title_format": [
            "标题{op}{value}",
            "标题中{op}{value}",
        ],
        "paper_structure": [
            "包含{count}条参考文献",
            "有{count}个图表",
        ],
        "research_topic": [
            "研究{topic}",
            "探讨{topic}",
            "关于{topic}",
        ],
        "technical_entity": [
            "涉及{entity}",
            "使用{entity}",
            "提及{entity}",
        ],
    }

    # 问题句式模板
    QUESTION_PATTERNS = [
        "{constraints}的论文标题是什么？",
        "请找出{constraints}的论文。",
        "{constraints}，这是哪篇论文？",
        "查找{constraints}的学术论文。",
        "哪篇论文{constraints}？",
        "请找出{constraints}的论文，并给出其标题。",
    ]

    # 按模板类型定制的句式
    TEMPLATE_SPECIFIC_PATTERNS = {
        "A": [  # Paper-Author-Institution
            "{constraints}的论文标题是什么？",
            "请找出{constraints}的学术论文。",
            "{constraints}，是哪篇论文？",
        ],
        "B": [  # Person-Academic-Path
            "{constraints}的研究者是谁？",
            "请找出{constraints}的学者。",
            "{constraints}，这是哪位作者？",
        ],
        "C": [  # Citation-Network
            "{constraints}的论文是哪篇？",
            "请找出{constraints}的文献。",
            "{constraints}，这指的是哪篇论文？",
        ],
        "D": [  # Collaboration-Network
            "{constraints}合著的论文有哪些？",
            "请找出{constraints}的合作论文。",
        ],
        "F": [  # Technical-Content
            "{constraints}的论文标题是什么？",
            "请找出{constraints}的研究论文。",
        ],
    }

    def __init__(self, kg_loader: Optional[KnowledgeGraphLoader] = None):
        """
        初始化问题生成器

        Args:
            kg_loader: 知识图谱加载器（用于获取实体名称）
        """
        self.kg_loader = kg_loader

    def generate(
        self,
        constraint_set: ConstraintSet,
        reasoning_chain: ReasoningChain,
        answer_entity_id: str,
        answer_text: str
    ) -> GeneratedQuestion:
        """
        生成问题

        Args:
            constraint_set: 约束集合
            reasoning_chain: 推理链
            answer_entity_id: 答案实体ID
            answer_text: 答案文本

        Returns:
            生成的问题对象
        """
        try:
            # 生成问题文本
            question_text = self._generate_question_text(constraint_set, reasoning_chain)

            # 创建问题对象
            question = GeneratedQuestion(
                question_id=self._generate_question_id(),
                question_text=question_text,
                answer=Answer(text=answer_text, entity_id=answer_entity_id),
                template_id=constraint_set.template_id,
                reasoning_chain=reasoning_chain,
                constraint_set=constraint_set,
                difficulty=self._calculate_difficulty(constraint_set, reasoning_chain),
                validity=True,
                generated_at=datetime.now().isoformat()
            )

            return question

        except Exception as e:
            raise QuestionGenerationException(f"Failed to generate question: {e}")

    def _generate_question_text(
        self,
        constraint_set: ConstraintSet,
        reasoning_chain: Optional[ReasoningChain] = None
    ) -> str:
        """
        生成问题文本

        Args:
            constraint_set: 约束集合
            reasoning_chain: 推理链

        Returns:
            问题文本
        """
        # 生成约束短语
        constraint_phrases = self._generate_constraint_phrases(constraint_set.constraints)

        if not constraint_phrases:
            return "请根据知识图谱查找相关信息。"

        # 组合约束短语
        if len(constraint_phrases) == 1:
            constraints_text = constraint_phrases[0]
        elif len(constraint_phrases) == 2:
            constraints_text = f"{constraint_phrases[0]}且{constraint_phrases[1]}"
        else:
            constraints_text = "，".join(constraint_phrases[:-1]) + f"，以及{constraint_phrases[-1]}"

        # 选择问题模板
        template_id = constraint_set.template_id
        if template_id in self.TEMPLATE_SPECIFIC_PATTERNS:
            pattern = random.choice(self.TEMPLATE_SPECIFIC_PATTERNS[template_id])
        else:
            pattern = random.choice(self.QUESTION_PATTERNS)

        # 填充模板
        question_text = pattern.format(constraints=constraints_text)

        return question_text

    def _generate_constraint_phrases(self, constraints: List[Constraint]) -> List[str]:
        """
        为每个约束生成自然语言短语

        Args:
            constraints: 约束列表

        Returns:
            约束短语列表
        """
        phrases = []

        for constraint in constraints:
            phrase = self._constraint_to_phrase(constraint)
            if phrase:
                phrases.append(phrase)

        return phrases

    def _constraint_to_phrase(self, constraint: Constraint) -> Optional[str]:
        """
        将单个约束转换为自然语言短语

        Args:
            constraint: 约束对象

        Returns:
            自然语言短语
        """
        constraint_type = constraint.constraint_type
        condition = constraint.filter_condition

        # 根据约束类型生成短语
        if constraint_type == "temporal":
            return self._temporal_to_phrase(condition)

        elif constraint_type == "author_count":
            return self._author_count_to_phrase(condition)

        elif constraint_type == "person_name":
            return self._person_name_to_phrase(condition)

        elif constraint_type == "author_order":
            return self._author_order_to_phrase(condition)

        elif constraint_type == "institution_affiliation":
            return self._institution_to_phrase(condition)

        elif constraint_type == "citation":
            return self._citation_to_phrase(condition)

        elif constraint_type == "title_format":
            return self._title_format_to_phrase(condition)

        elif constraint_type == "paper_structure":
            return self._paper_structure_to_phrase(condition)

        elif constraint_type == "research_topic":
            return self._research_topic_to_phrase(condition)

        elif constraint_type == "technical_entity":
            return self._technical_entity_to_phrase(condition)

        # 默认使用约束描述
        return constraint.description

    def _temporal_to_phrase(self, condition: Any) -> str:
        """时间约束转短语"""
        if isinstance(condition, dict):
            op = list(condition.keys())[0]
            value = condition[op]

            if op == "=":
                return f"{value}年发表"
            elif op == ">":
                return f"{value}年后发表"
            elif op == "<":
                return f"{value}年前发表"
            elif op == "between":
                return f"{value[0]}-{value[1]}年间发表"
            elif op == ">=":
                return f"{value}年及以后发表"
            elif op == "<=":
                return f"{value}年及以前发表"

        return f"时间约束"

    def _author_count_to_phrase(self, condition: Any) -> str:
        """作者数量约束转短语"""
        if isinstance(condition, dict):
            op = list(condition.keys())[0]
            value = condition[op]

            if op == "=":
                return f"{value}位作者合著"
            elif op == ">":
                return f"作者数大于{value}"
            elif op == "<":
                return f"作者数少于{value}"
            elif op == ">=":
                return f"至少{value}位作者"

        return "多作者论文"

    def _person_name_to_phrase(self, condition: Any) -> str:
        """人名约束转短语"""
        if isinstance(condition, str):
            return f"作者是{condition}"
        elif isinstance(condition, dict) and "contains" in condition:
            return f"作者名包含{condition['contains']}"

        return "指定作者"

    def _author_order_to_phrase(self, condition: Any) -> str:
        """作者顺序约束转短语"""
        if isinstance(condition, int):
            order_map = {1: "第一", 2: "第二", 3: "第三", -1: "最后"}
            order_text = order_map.get(condition, f"第{condition}")
            return f"{order_text}作者是"

        return "特定作者"

    def _institution_to_phrase(self, condition: Any) -> str:
        """机构约束转短语"""
        if isinstance(condition, str):
            return f"来自{condition}"

        return "某机构"

    def _citation_to_phrase(self, condition: Any) -> str:
        """引用约束转短语"""
        if isinstance(condition, dict):
            op = list(condition.keys())[0]
            value = condition[op]

            if op == ">":
                return f"引用数超过{value}"
            elif op == "<":
                return f"引用数少于{value}"
            elif op == "=":
                return f"引用数恰好{value}"

        return "特定引用数"

    def _title_format_to_phrase(self, condition: Any) -> str:
        """标题格式约束转短语"""
        if isinstance(condition, dict):
            if "ends_with" in condition:
                return f"标题以'{condition['ends_with']}'结尾"
            elif "starts_with" in condition:
                return f"标题以'{condition['starts_with']}'开头"
            elif "contains" in condition:
                return f"标题包含'{condition['contains']}'"

        return "特定标题格式"

    def _paper_structure_to_phrase(self, condition: Any) -> str:
        """论文结构约束转短语"""
        if isinstance(condition, dict):
            if "exists" in condition:
                return "有特定结构"

        return "特定结构论文"

    def _research_topic_to_phrase(self, condition: Any) -> str:
        """研究主题约束转短语"""
        if isinstance(condition, str):
            return f"研究{condition}"

        return "特定主题"

    def _technical_entity_to_phrase(self, condition: Any) -> str:
        """技术实体约束转短语"""
        if isinstance(condition, str):
            return f"涉及{condition}"

        return "特定技术"

    def _generate_question_id(self) -> str:
        """生成问题ID"""
        return f"Q{uuid.uuid4().hex[:8].upper()}"

    def _calculate_difficulty(
        self,
        constraint_set: ConstraintSet,
        reasoning_chain: ReasoningChain
    ) -> str:
        """
        计算问题难度

        Args:
            constraint_set: 约束集合
            reasoning_chain: 推理链

        Returns:
            难度等级 (easy/medium/hard)
        """
        num_constraints = len(constraint_set.constraints)
        num_hops = reasoning_chain.total_hops if reasoning_chain else 0

        # 综合约束数量和推理跳数
        score = num_constraints * 1 + num_hops * 2

        if score <= 5:
            return "easy"
        elif score <= 10:
            return "medium"
        else:
            return "hard"
