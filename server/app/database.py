"""
数据库连接管理
SQLAlchemy 2.0 异步引擎 + 异步 Session
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 异步引擎
# connect_timeout=5：连接超时 5 秒，避免数据库不可用时长时间阻塞启动
# pool_pre_ping=True：连接前检查连通性，自动剔除失效连接
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"timeout": 5},  # 连接超时 5 秒，防止启动阻塞
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类"""
    pass


async def get_db() -> AsyncSession:
    """
    依赖注入：获取数据库 Session
    使用 async with 确保 Session 自动关闭
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库（创建所有表）
    生产环境建议用 Alembic 迁移，这里仅用于开发快速启动
    """
    # 导入所有模型，确保 Base.metadata 能发现它们
    from app.models import note, chunk, conversation, message  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
