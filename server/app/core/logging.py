"""日志配置
使用 loguru 统一日志格式，输出到控制台和文件
"""
import sys
from loguru import logger
from app.config import settings


def setup_logging() -> None:
    """配置日志"""
    # 移除默认 handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        enqueue=True,  # 异步安全
    )

    # 文件输出（按大小轮转）
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )

    logger.info("日志系统初始化完成")
