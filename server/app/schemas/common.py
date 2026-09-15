"""通用响应模型"""
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    database: str
    redis: str
