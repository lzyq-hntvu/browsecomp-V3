"""
模板选择器

根据策略选择推理链模板。
"""

import random
from typing import Optional

from browsecomp_v3.templates.template_loader import TemplateLoader
from browsecomp_v3.core.exceptions import TemplateNotFoundException


class TemplateSelector:
    """模板选择器"""

    def __init__(self):
        """初始化模板选择器"""
        self.loader = TemplateLoader()

    def select(
        self,
        mode: str = "random",
        template_id: Optional[str] = None,
        exclude: Optional[list] = None
    ) -> str:
        """
        选择推理链模板

        Args:
            mode: 选择模式
                - "random": 随机选择，按模板频率加权
                - "uniform": 均匀随机选择
                - "specific": 指定模板ID
            template_id: 指定模板ID (mode="specific"时使用)
            exclude: 排除的模板ID列表

        Returns:
            选中的模板ID

        Raises:
            TemplateNotFoundException: 模板不存在
        """
        all_templates = self.loader.get_all_templates()

        # 过滤排除的模板
        if exclude:
            available_templates = {k: v for k, v in all_templates.items() if k not in exclude}
        else:
            available_templates = all_templates

        if not available_templates:
            raise TemplateNotFoundException("No available templates after exclusion")

        if mode == "specific":
            if template_id is None:
                raise ValueError("template_id must be provided when mode='specific'")
            if template_id not in available_templates:
                raise TemplateNotFoundException(f"Template '{template_id}' not found or excluded")
            return template_id

        elif mode == "random":
            # 按频率加权随机选择
            template_ids = list(available_templates.keys())
            weights = [available_templates[tid].get("frequency", 0.1) for tid in template_ids]
            return random.choices(template_ids, weights=weights, k=1)[0]

        elif mode == "uniform":
            # 均匀随机选择
            return random.choice(list(available_templates.keys()))

        else:
            raise ValueError(f"Unknown mode: {mode}")

    def get_template_info(self, template_id: str) -> dict:
        """获取模板信息"""
        return self.loader.get_template(template_id)
