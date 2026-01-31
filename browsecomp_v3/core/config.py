"""
Browsecomp-V3 配置管理

管理系统的所有配置参数。
"""

import os
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Config:
    """系统配置"""

    # 项目路径
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = field(default=None)
    output_dir: Path = field(default=None)
    log_dir: Path = field(default=None)

    # 知识图谱配置
    kg_path: Optional[str] = None
    kg_format: str = "json"  # json/graphml

    # 模板配置
    template_dir: Path = field(default=None)
    template_file: str = "推理链模板.md"
    constraint_mapping_file: str = "constraint_to_graph_mapping.json"

    # 生成配置
    default_min_constraints: int = 3
    default_max_constraints: int = 6
    default_batch_size: int = 50
    max_generation_retries: int = 10

    # 验证配置
    require_unique_answer: bool = False  # 允许多个候选，随机选择一个
    min_constraint_count: int = 1  # 最少1个约束即可
    check_diversity: bool = True
    diversity_threshold: float = 0.8  # Jaccard相似度阈值

    # 约束生成配置
    valid_constraint_types: list = None  # 有效约束类型白名单，None使用默认值

    # 输出配置
    output_format: str = "json"  # json/markdown/both
    include_reasoning_chain: bool = True
    pretty_print: bool = True

    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    verbose: bool = False

    # 性能配置
    cache_enabled: bool = True
    cache_size: int = 1000
    max_workers: int = 4

    def __post_init__(self):
        """初始化路径配置"""
        if self.data_dir is None:
            self.data_dir = self.project_root / "data"
        if self.output_dir is None:
            self.output_dir = self.project_root / "output"
        if self.log_dir is None:
            self.log_dir = self.output_dir / "logs"
        if self.template_dir is None:
            self.template_dir = self.project_root / "data" / "templates"

        # 创建必要的目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        config = cls()

        # 知识图谱路径 - 默认使用QandA项目路径
        config.kg_path = os.getenv(
            "BROWSECOMP_KG_PATH",
            "/home/huyuming/projects/QandA/output/knowledge_graph_expanded.json"
        )

        # 模板文件路径
        if not os.path.exists(config.template_dir / config.constraint_mapping_file):
            # 如果本地不存在，使用browsecomp-V2的文件
            config.template_dir = Path("/home/huyuming/browsecomp-V2/deliverables")

        # 日志级别
        config.log_level = os.getenv("BROWSECOMP_LOG_LEVEL", "INFO")
        config.verbose = os.getenv("BROWSECOMP_VERBOSE", "false").lower() == "true"

        # 生成配置
        if batch_size := os.getenv("BROWSECOMP_BATCH_SIZE"):
            config.default_batch_size = int(batch_size)

        return config

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """从字典加载配置"""
        return cls(**{
            k: v for k, v in config_dict.items()
            if k in cls.__dataclass_fields__
        })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "kg_path": self.kg_path,
            "kg_format": self.kg_format,
            "template_file": self.template_file,
            "constraint_mapping_file": self.constraint_mapping_file,
            "default_min_constraints": self.default_min_constraints,
            "default_max_constraints": self.default_max_constraints,
            "default_batch_size": self.default_batch_size,
            "require_unique_answer": self.require_unique_answer,
            "output_format": self.output_format,
            "log_level": self.log_level,
        }


# 全局配置实例
_global_config: Optional[Config] = None
_lock = threading.Lock()


def get_config() -> Config:
    """
    获取全局配置实例（线程安全）

    使用双重检查锁定（double-checked locking）模式确保线程安全。
    """
    global _global_config
    if _global_config is None:
        with _lock:
            # 双重检查：另一个线程可能已经在等待锁时初始化了配置
            if _global_config is None:
                _global_config = Config.from_env()
    return _global_config


def set_config(config: Config):
    """
    设置全局配置（线程安全）

    Args:
        config: 配置对象
    """
    global _global_config
    with _lock:
        _global_config = config
