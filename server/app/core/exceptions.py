"""统一异常处理"""
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class AppException(Exception):
    """应用基础异常"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def app_exception_handler(request: Request, exc: AppException):
    """应用异常处理器"""
    logger.warning(f"应用异常: code={exc.code} message={exc.message}")
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


async def general_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.exception(f"未捕获异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )
