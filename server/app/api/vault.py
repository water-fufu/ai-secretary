"""知识库接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.note_service import rebuild_index_from_db, get_vault_stats
from app.rag.bm25_retriever import rebuild_bm25_index

router = APIRouter(prefix="/vault", tags=["知识库"])


@router.get("/overview")
async def vault_overview(db: AsyncSession = Depends(get_db)):
    """知识库概览（分区数、笔记数、切片数、最后更新时间）"""
    stats = await get_vault_stats(db)
    return stats


@router.post("/refresh")
async def vault_refresh(db: AsyncSession = Depends(get_db)):
    """重建知识库索引（向量索引 + BM25 索引全量重建）"""
    # 1. 重建向量索引（FAISS）
    result = await rebuild_index_from_db(db)
    # 2. 重建 BM25 关键词索引（Hybrid RAG 稀疏通道）
    bm25_count = await rebuild_bm25_index(db)
    return {
        "message": "索引重建完成",
        "chunk_count": result["chunk_count"],
        "note_count": result["note_count"],
        "bm25_chunk_count": bm25_count,
        "vector_index": "success" if result["chunk_count"] > 0 else "empty",
        "bm25_index": "success" if bm25_count > 0 else "empty",
    }
