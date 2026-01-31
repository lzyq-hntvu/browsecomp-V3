"""
答案提取器

从查询结果中提取并格式化答案。
"""

from typing import Any, Optional

from browsecomp_v3.core.models import Answer
from browsecomp_v3.core.exceptions import QuestionGenerationException


class AnswerExtractor:
    """答案提取器"""

    def __init__(self):
        """初始化答案提取器"""
        pass

    def extract(
        self,
        entity_id: str,
        entity_data: dict,
        kg_loader
    ) -> Answer:
        """
        提取答案

        Args:
            entity_id: 实体ID
            entity_data: 实体数据
            kg_loader: 知识图谱加载器

        Returns:
            答案对象
        """
        try:
            # 提取主要信息
            entity_type = entity_data.get("type")
            text = self._format_answer_text(entity_data)

            return Answer(
                text=text,
                entity_id=entity_id,
                entity_type=entity_type
            )

        except Exception as e:
            raise QuestionGenerationException(f"Failed to extract answer: {e}")

    def _format_answer_text(self, entity_data: dict) -> str:
        """格式化答案文本"""
        # 根据实体类型格式化
        entity_type = entity_data.get("type", "").lower()

        if entity_type == "paper":
            title = entity_data.get("title", "Unknown Title")
            return title
        elif entity_type == "author":
            name = entity_data.get("name", "Unknown Name")
            return name
        elif entity_type == "institution":
            name = entity_data.get("name", "Unknown Institution")
            return name
        else:
            # 默认返回名称或ID
            return entity_data.get("name", entity_data.get("id", ""))
