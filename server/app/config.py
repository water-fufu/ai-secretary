"""
应用配置管理
使用 Pydantic Settings 从环境变量读取配置
CloudBase 部署时通过环境变量注入

支持两种数据库配置方式：
1. 直接设置 DATABASE_URL（优先）
2. CloudBase 自动注入的 PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD（自动拼接）
"""
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Optional


class Settings(BaseSettings):
    """应用配置，所有值均可通过环境变量覆盖"""

    # ===== 应用信息 =====
    APP_NAME: str = "秘书 2.0 API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ===== 数据库 =====
    # 方式1：直接设置完整连接串（优先使用）
    DATABASE_URL: Optional[str] = None
    # 方式2：CloudBase 自动注入的分拆环境变量（自动拼接）
    PGHOST: Optional[str] = None
    PGPORT: Optional[str] = "5432"
    PGDATABASE: Optional[str] = None
    PGUSER: Optional[str] = None
    PGPASSWORD: Optional[str] = None

    # ===== Redis =====
    # 方式1：直接设置完整连接串（优先使用）
    REDIS_URL: Optional[str] = None
    # 方式2：分拆环境变量（自动拼接）
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[str] = "6379"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: Optional[str] = "0"

    # ===== LLM =====
    DEEPSEEK_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    # ===== RAG =====
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    TOP_K: int = 3
    # FAISS 索引持久化路径（CloudBase 存储卷挂载点）
    FAISS_INDEX_PATH: str = "/app/data/faiss"

    # ===== 缓存 =====
    CACHE_EXACT_TTL: int = 3600  # 精确缓存 TTL（秒）
    CACHE_SEMANTIC_TTL: int = 7200  # 语义缓存 TTL（秒）
    CACHE_SEMANTIC_THRESHOLD: float = 0.9  # 语义相似度阈值

    # ===== CORS =====
    CORS_ORIGINS: List[str] = ["*"]

    # ===== 限流 =====
    RATE_LIMIT_PER_MINUTE: int = 60

    @model_validator(mode="after")
    def assemble_database_url(self):
        """
        自动拼接数据库连接串
        如果 DATABASE_URL 已设置，直接使用；
        否则从 PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD 拼接
        """
        if self.DATABASE_URL is None and self.PGHOST is not None:
            # CloudBase 自动注入模式
            user = self.PGUSER or "postgres"
            password = self.PGPASSWORD or ""
            port = self.PGPORT or "5432"
            db = self.PGDATABASE or "postgres"
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{user}:{password}@{self.PGHOST}:{port}/{db}"
            )
        # 兜底默认值（本地开发用）
        if self.DATABASE_URL is None:
            self.DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/mishu"
        return self

    @model_validator(mode="after")
    def assemble_redis_url(self):
        """
        自动拼接 Redis 连接串
        如果 REDIS_URL 已设置，直接使用；
        否则从 REDIS_HOST/REDIS_PORT/REDIS_PASSWORD/REDIS_DB 拼接
        """
        if self.REDIS_URL is None and self.REDIS_HOST is not None:
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = (
                f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        # 兜底默认值（本地开发用）
        if self.REDIS_URL is None:
            self.REDIS_URL = "redis://localhost:6379/0"
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置单例
settings = Settings()
