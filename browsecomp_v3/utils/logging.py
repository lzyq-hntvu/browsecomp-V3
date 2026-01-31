"""
日志配置模块

提供结构化的日志系统，支持控制台和文件输出。
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: Optional[Path] = None,
    verbose: bool = False
) -> logging.Logger:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件名（不含路径）
        log_dir: 日志文件目录
        verbose: 是否在控制台显示详细信息

    Returns:
        配置好的 logger 实例
    """
    # 创建根 logger
    logger = logging.getLogger("browsecomp_v3")

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, log_level.upper()))
    logger.propagate = False  # 避免传播到父 logger

    # 控制台 handler（使用 Rich）
    console_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=verbose,
        markup=True,
        show_time=False,
        show_path=verbose
    )
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = logging.Formatter(
        "%(message)s",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件 handler（可选）
    if log_file:
        log_path = Path(log_dir) / log_file if log_dir else Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger

    Args:
        name: logger 名称（通常使用 __name__）

    Returns:
        logger 实例
    """
    return logging.getLogger(f"browsecomp_v3.{name}")
