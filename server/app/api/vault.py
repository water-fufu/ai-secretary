"""知识库接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.note_service import rebuild_index_from_db, get_vault_stats

router = APIRouter(prefix="/vault", tags=["知识库"])


@router.get("/overview")
async def vault_overview(db: AsyncSession = Depends(get_db)):
    """知识库概览（分区数、笔记数、切片数、最后更新时间）"""
    stats = await get_vault_stats(db)
    return stats


@router.post("/refresh")
async def vault_refresh(db: AsyncSession = Depends(get_db)):
    """重建知识库索引（从数据库全量重建）"""
    result = await rebuild_index_from_db(db)
    return {
        "message": "索引重建完成",
        "chunk_count": result["chunk_count"],
        "note_count": result["note_count"],
    }
