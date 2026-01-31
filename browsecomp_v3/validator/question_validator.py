"""
问题验证器

验证生成问题的有效性。
"""

from typing import List, Optional
from difflib import SequenceMatcher

from browsecomp_v3.core.models import GeneratedQuestion
from browsecomp_v3.core.exceptions import ValidationException
from browsecomp_v3.core.config import get_config


class QuestionValidator:
    """问题验证器"""

    def __init__(self):
        """初始化验证器"""
        self.config = get_config()
        self._validated_questions: List[GeneratedQuestion] = []

    def validate(self, question: GeneratedQuestion, candidates: List[str]) -> bool:
        """
        验证问题

        Args:
            question: 生成的问题
            candidates: 候选答案列表

        Returns:
            是否有效
        """
        try:
            # 1. 唯一性验证
            if self.config.require_unique_answer:
                if len(candidates) != 1:
                    return False

            # 2. 约束数量验证
            if len(question.constraint_set.constraints) < self.config.min_constraint_count:
                return False

            # 3. 答案存在性验证
            if not question.answer.text:
                return False

            # 4. 多样性验证
            if self.config.check_diversity:
                if self._is_duplicate(question):
                    return False

            return True

        except Exception:
            return False

    def validate_batch(self, questions: List[GeneratedQuestion]) -> List[GeneratedQuestion]:
        """
        批量验证问题

        Args:
            questions: 问题列表

        Returns:
            有效的问题列表
        """
        valid_questions = []
        for q in questions:
            # 这里简化处理，实际需要候选结果
            if self.validate(q, candidates=["dummy"]):
                valid_questions.append(q)
                self._validated_questions.append(q)

        return valid_questions

    def _is_duplicate(self, question: GeneratedQuestion) -> bool:
        """检查是否重复"""
        for existing in self._validated_questions:
            similarity = self._calculate_similarity(
                question.question_text,
                existing.question_text
            )
            if similarity > (1 - self.config.diversity_threshold):
                return True
        return False

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        return SequenceMatcher(None, text1, text2).ratio()
