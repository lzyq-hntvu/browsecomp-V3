"""
推理链构建器

构建和格式化推理链文档。
"""

from typing import Dict, Any, List
from datetime import datetime

from browsecomp_v3.core.models import ReasoningChain, TraversalStep


class ReasoningChainBuilder:
    """推理链构建器"""

    def __init__(self):
        """初始化推理链构建器"""
        pass

    def build(self, steps: List[TraversalStep], template_id: str) -> ReasoningChain:
        """
        构建推理链

        Args:
            steps: 遍历步骤列表
            template_id: 模板ID

        Returns:
            推理链对象
        """
        return ReasoningChain(
            template_id=template_id,
            start_node="",
            steps=steps,
            total_hops=len(steps)
        )

    def format_markdown(self, reasoning_chain: ReasoningChain) -> str:
        """
        格式化为Markdown

        Args:
            reasoning_chain: 推理链对象

        Returns:
            Markdown格式的推理链
        """
        lines = [
            f"## 推理链 (模板 {reasoning_chain.template_id})",
            "",
            f"**总跳数**: {reasoning_chain.total_hops}",
            "",
            "### 推理步骤",
            ""
        ]

        for step in reasoning_chain.steps:
            action_desc = {
                "filter_current_node": "过滤",
                "traverse_edge": "遍历",
                "traverse_and_count": "计数"
            }.get(step.action.value, step.action.value)

            lines.append(f"{step.step_id}. **[{action_desc}]** {step.description or 'N/A'}")
            if step.filter_condition:
                lines.append(f"   - 条件: {step.filter_condition}")
            lines.append(f"   - 结果数: {step.result_count}")
            lines.append("")

        return "\n".join(lines)

    def format_json(self, reasoning_chain: ReasoningChain) -> Dict[str, Any]:
        """
        格式化为JSON

        Args:
            reasoning_chain: 推理链对象

        Returns:
            JSON格式的推理链
        """
        return {
            "template_id": reasoning_chain.template_id,
            "start_node_type": reasoning_chain.start_node,
            "total_hops": reasoning_chain.total_hops,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action.value,
                    "target_node": s.target_node.value if s.target_node else None,
                    "edge_type": s.edge_type.value if s.edge_type else None,
                    "filter_condition": str(s.filter_condition) if s.filter_condition else None,
                    "result_count": s.result_count,
                    "description": s.description
                }
                for s in reasoning_chain.steps
            ]
        }
