"""
检索模块（Hybrid RAG）
- 向量检索（稠密语义检索，FAISS + fastembed）
- BM25 检索（稀疏关键词检索，jieba 分词）
- RRF 融合（Reciprocal Rank Fusion）
- 向量检索失败时自动降级到纯 BM25
- 检索结果格式化
- 信息冲突检测
"""
import json
import re
from typing import List, Optional, Dict, Tuple

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.core.llm import get_llm
from app.rag.vector_store import get_vector_store
from app.rag.bm25_retriever import get_bm25_retriever, rebuild_bm25_index
from app.rag.prompts import CONFLICT_DETECT_PROMPT


# RRF 融合的常数 k（通常取 60，控制排名权重衰减）
_RRF_K = 60


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    """
    计算 RRF（Reciprocal Rank Fusion）分数

    Args:
        rank: 排名（从 0 开始）
        k: 衰减常数，默认 60

    Returns:
        RRF 分数 = 1 / (k + rank + 1)
    """
    return 1.0 / (k + rank + 1)


def _fuse_results(
    vector_results: List[Document],
    bm25_results: List[Dict],
    top_k: int,
) -> List[Document]:
    """
    RRF 融合向量检索和 BM25 检索结果

    Args:
        vector_results: 向量检索结果（Document 列表，metadata 含 chunk_id）
        bm25_results: BM25 检索结果（字典列表，含 chunk_id）
        top_k: 最终返回数量

    Returns:
        融合后的 Document 列表（按 RRF 分数降序）
    """
    # 用 chunk_id 作为融合键
    fused: Dict[int, Dict] = {}

    # 累加向量检索的 RRF 分数
    for rank, doc in enumerate(vector_results):
        chunk_id = doc.metadata.get("chunk_id")
        if chunk_id is None:
            continue
        if chunk_id not in fused:
            fused[chunk_id] = {"doc": doc, "score": 0.0, "vector_rank": rank}
        fused[chunk_id]["score"] += _rrf_score(rank) * settings.HYBRID_VECTOR_WEIGHT

    # 累加 BM25 检索的 RRF 分数
    for rank, item in enumerate(bm25_results):
        chunk_id = item.get("chunk_id")
        if chunk_id is None:
            continue
        if chunk_id in fused:
            # 已有向量结果，累加 BM25 分数
            fused[chunk_id]["score"] += _rrf_score(rank) * settings.HYBRID_BM25_WEIGHT
        else:
            # 只有 BM25 结果，构造 Document
            doc = Document(
                page_content=item.get("content", ""),
                metadata={
                    "chunk_id": chunk_id,
                    "note_id": item.get("note_id"),
                    "folder": item.get("folder", ""),
                    "file_name": item.get("file_name", ""),
                    "section": item.get("section", ""),
                    "chunk_index": item.get("chunk_index", 0),
                }
            )
            fused[chunk_id] = {
                "doc": doc,
                "score": _rrf_score(rank) * settings.HYBRID_BM25_WEIGHT,
                "vector_rank": None,
            }

    # 按融合分数降序排序，取 top_k
    sorted_items = sorted(fused.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    return [item["doc"] for item in sorted_items]


async def retrieve_chunks(
    query: str,
    top_k: int = None,
    folder_filter: str = None,
    db=None,
) -> Tuple[List[Document], str]:
    """
    Hybrid 检索：BM25 + 向量检索，RRF 融合

    Args:
        query: 查询文本
        top_k: 返回数量，默认使用配置
        folder_filter: 按文件夹过滤
        db: 数据库会话（用于 BM25 索引构建，可选）

    Returns:
        (检索结果列表, 检索模式说明)
        检索模式："hybrid" / "bm25_only" / "vector_only" / "empty"
    """
    if top_k is None:
        top_k = settings.TOP_K

    # ===== BM25 检索（始终尝试，零依赖） =====
    bm25_results = []
    bm25 = get_bm25_retriever()

    if not bm25.is_built and db is not None:
        # 索引未构建，尝试从数据库构建
        try:
            await rebuild_bm25_index(db)
        except Exception as e:
            print(f"  ⚠ BM25 索引构建失败: {e}")

    if bm25.is_built:
        try:
            bm25_results = bm25.search(query, top_k=max(top_k * 3, settings.BM25_TOP_K))
        except Exception as e:
            print(f"  ⚠ BM25 检索失败: {e}")
            bm25_results = []

    # ===== 向量检索（可能因模型未下载而失败） =====
    vector_results = []
    vector_available = False

    try:
        vs = get_vector_store()
        if vs is not None and vs.is_initialized:
            vector_results = vs.similarity_search(query, k=top_k * 3, folder_filter=folder_filter)
            vector_available = True
    except Exception as e:
        print(f"  ⚠ 向量检索失败（降级到 BM25）: {e}")
        vector_available = False

    # ===== 融合或降级 =====
    if settings.HYBRID_ENABLED and vector_available and bm25_results:
        # 双通道都可用 → RRF 融合
        fused = _fuse_results(vector_results, bm25_results, top_k)
        # 文件夹过滤
        if folder_filter:
            fused = [d for d in fused if d.metadata.get("folder") == folder_filter]
        return fused[:top_k], "hybrid"

    elif vector_available:
        # 只有向量检索
        if folder_filter:
            vector_results = [d for d in vector_results if d.metadata.get("folder") == folder_filter]
        return vector_results[:top_k], "vector_only"

    elif bm25_results:
        # 只有 BM25（向量模型未下载或检索失败）
        if folder_filter:
            bm25_results = [r for r in bm25_results if r.get("folder") == folder_filter]
        docs = [
            Document(
                page_content=r.get("content", ""),
                metadata={
                    "chunk_id": r.get("chunk_id"),
                    "note_id": r.get("note_id"),
                    "folder": r.get("folder", ""),
                    "file_name": r.get("file_name", ""),
                    "section": r.get("section", ""),
                    "chunk_index": r.get("chunk_index", 0),
                }
            )
            for r in bm25_results[:top_k]
        ]
        return docs, "bm25_only"

    else:
        # 双通道都不可用
        return [], "empty"


def format_retrieved_context(docs: List[Document]) -> str:
    """
    将检索结果格式化为 LLM 可理解的上下文文本

    Args:
        docs: 检索到的 Document 列表

    Returns:
        格式化后的上下文文本
    """
    if not docs:
        return "（天书库中暂无相关资料）"

    parts = []
    for i, doc in enumerate(docs, 1):
        folder = doc.metadata.get("folder", "未知")
        fname = doc.metadata.get("file_name", "未知")
        section = doc.metadata.get("section", "")
        ts = doc.metadata.get("timestamp", "未知")
        header = f"[片段{i}] 📁{folder}/{fname} | 📅{ts}"
        if section:
            header += f" | 📍{section}"
        parts.append(f"{header}\n{doc.page_content}")

    return "\n\n---\n\n".join(parts)


def detect_conflicts(docs: List[Document]) -> Optional[Dict]:
    """
    检测多个检索片段之间是否存在信息冲突

    Args:
        docs: 检索到的 Document 列表（至少 2 个才检测）

    Returns:
        冲突信息字典，无冲突返回 None
    """
    if len(docs) < 2:
        return None

    llm = get_llm()

    parts = []
    for i, d in enumerate(docs):
        folder = d.metadata.get("folder", "?")
        fname = d.metadata.get("file_name", "?")
        ts = d.metadata.get("timestamp", "?")
        parts.append(f"[片段{i+1}] 来源: {folder}/{fname} 时间: {ts}\n{d.page_content}")
    chunks_text = "\n\n---\n\n".join(parts)

    try:
        response = llm.invoke(CONFLICT_DETECT_PROMPT.format(chunks_text=chunks_text))
        raw = response.content.strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠ 冲突检测失败: {e}")
        return None


def get_sources_from_docs(docs: List[Document]) -> List[Dict]:
    """
    从检索结果中提取来源信息（用于 API 响应）

    Args:
        docs: 检索到的 Document 列表

    Returns:
        来源信息列表
    """
    sources = []
    for doc in docs:
        sources.append({
            "folder": doc.metadata.get("folder", "未知"),
            "file_name": doc.metadata.get("file_name", "未知"),
            "section": doc.metadata.get("section", ""),
            "timestamp": doc.metadata.get("timestamp", "未知"),
        })
    return sources
