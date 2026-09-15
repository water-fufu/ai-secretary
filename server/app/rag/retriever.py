"""
检索模块
- 相似度检索
- 检索结果格式化
- 信息冲突检测
"""
import json
import re
from typing import List, Optional, Dict

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.core.llm import get_llm
from app.rag.vector_store import get_vector_store
from app.rag.prompts import CONFLICT_DETECT_PROMPT


def retrieve_chunks(
    query: str, top_k: int = None, folder_filter: str = None
) -> List[Document]:
    """
    从向量库检索相关片段

    Args:
        query: 查询文本
        top_k: 返回数量，默认使用配置
        folder_filter: 按文件夹过滤

    Returns:
        检索到的 Document 列表
    """
    if top_k is None:
        top_k = settings.TOP_K

    vs = get_vector_store()
    return vs.similarity_search(query, k=top_k, folder_filter=folder_filter)


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
        {
            "has_conflict": bool,
            "conflict_summary": str,
            "newest_entry": str
        }
    """
    if len(docs) < 2:
        return None

    llm = get_llm()

    # 构建片段文本
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

        # 清理可能的 markdown 代码块标记
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
