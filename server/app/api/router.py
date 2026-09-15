"""API 路由聚合"""
from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.notes import router as notes_router
from app.api.vault import router as vault_router

api_router = APIRouter()

# 注册所有子路由
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(notes_router)
api_router.include_router(vault_router)
