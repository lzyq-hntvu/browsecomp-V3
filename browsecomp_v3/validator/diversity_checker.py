"""
多样性检查器

检查生成问题的多样性。
"""

from typing import List, Dict, Any
from collections import Counter
from difflib import SequenceMatcher

from browsecomp_v3.core.models import GeneratedQuestion


class DiversityChecker:
    """多样性检查器"""

    def __init__(self, threshold: float = 0.8):
        """
        初始化多样性检查器

        Args:
            threshold: 相似度阈值
        """
        self.threshold = threshold

    def check_diversity(self, questions: List[GeneratedQuestion]) -> Dict[str, Any]:
        """
        检查问题多样性

        Args:
            questions: 问题列表

        Returns:
            多样性统计信息
        """
        if not questions:
            return {
                "total": 0,
                "duplicates": 0,
                "unique": 0,
                "diversity_rate": 0.0,
                "template_distribution": {},
                "constraint_stats": {
                    "min": 0,
                    "max": 0,
                    "avg": 0
                }
            }

        # 检查重复
        unique_questions = []
        duplicates = 0

        for q in questions:
            is_duplicate = False
            for existing in unique_questions:
                if self._similarity(q.question_text, existing.question_text) > self.threshold:
                    is_duplicate = True
                    break

            if is_duplicate:
                duplicates += 1
            else:
                unique_questions.append(q)

        # 统计模板分布
        template_distribution = Counter(q.template_id for q in unique_questions)

        # 统计约束分布
        constraint_counts = [len(q.constraint_set.constraints) for q in unique_questions]

        return {
            "total": len(questions),
            "duplicates": duplicates,
            "unique": len(unique_questions),
            "diversity_rate": len(unique_questions) / len(questions) if questions else 0,
            "template_distribution": dict(template_distribution),
            "constraint_stats": {
                "min": min(constraint_counts) if constraint_counts else 0,
                "max": max(constraint_counts) if constraint_counts else 0,
                "avg": sum(constraint_counts) / len(constraint_counts) if constraint_counts else 0
            }
        }

    def _similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        return SequenceMatcher(None, text1, text2).ratio()
