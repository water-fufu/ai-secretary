"""健康检查接口"""
from fastapi import APIRouter
from app.schemas.common import HealthResponse
from app.config import settings

router = APIRouter(tags=["健康检查"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口
    返回应用状态、版本、数据库和 Redis 连接状态
    """
    # TODO: P4 实现真实的数据库和 Redis 连接检查
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        database="connected",  # 占位，P4 实现真实检查
        redis="connected",     # 占位，P4 实现真实检查
    )
