"""
FastAPI 应用入口
- lifespan：启动时初始化数据库、Redis、LLM、FAISS 索引
- 挂载 API 路由
- 配置 CORS、异常处理
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.router import api_router
from app.core.logging import setup_logging
from app.rag.vector_store import get_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动：初始化日志、数据库、Redis、LLM、FAISS 索引
    关闭：释放资源
    """
    # 启动时
    setup_logging()
    print(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    # 数据库初始化移到后台任务，不阻塞启动
    # 原因：CloudBase 健康检查有超时限制，数据库连接超时不应导致部署失败
    import asyncio

    async def _init_db_background():
        """后台初始化数据库，失败不影响服务启动"""
        try:
            await init_db()
            print("✅ 数据库初始化完成")
        except Exception as e:
            print(f"⚠ 数据库初始化失败（不影响服务启动）: {e}")
            print("  请检查 DATABASE_URL / PGHOST 配置，或使用 Alembic 迁移")

    asyncio.create_task(_init_db_background())

    # 初始化向量库（尝试加载，失败则标记需重建）
    # 注意：load() 在索引不存在时直接返回 False，不会触发模型下载
    try:
        vs = get_vector_store()
        if not vs.load():
            print("⚠ FAISS 索引不存在，首次写入时自动构建")
    except Exception as e:
        print(f"⚠ FAISS 初始化失败: {e}")

    # TODO: 初始化 Redis 连接池
    # TODO: 预热 LLM 客户端

    yield

    # 关闭时
    print("👋 应用关闭中...")
    # 保存 FAISS 索引
    try:
        vs = get_vector_store()
        vs.save()
    except Exception:
        pass


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="秘书 2.0 - 个人知识库 AI Agent 云端 API",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径：服务信息"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
