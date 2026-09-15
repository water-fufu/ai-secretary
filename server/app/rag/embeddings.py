"""
向量化模块
使用 fastembed（ONNX 运行时）加载 all-MiniLM-L6-v2 模型
不依赖 torch，镜像体积小，构建快
单例模式，避免重复加载模型
"""
from typing import List, Optional
from fastembed import TextEmbedding
from app.config import settings

# 全局嵌入模型单例
_embeddings: Optional[TextEmbedding] = None


def get_embeddings() -> TextEmbedding:
    """
    获取嵌入模型单例
    首次调用时下载并加载模型，后续调用复用
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = TextEmbedding(
            model_name=settings.EMBEDDING_MODEL,
        )
        print(f"✅ 嵌入模型已加载: {settings.EMBEDDING_MODEL}")
    return _embeddings


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    批量向量化文本

    Args:
        texts: 文本列表

    Returns:
        向量列表，每个向量是 384 维浮点数列表
    """
    model = get_embeddings()
    # fastembed 返回 numpy 数组迭代器，转成 list[list[float]]
    return [vec.tolist() for vec in model.embed(texts)]


def embed_query(text: str) -> List[float]:
    """
    向量化单个查询文本

    Args:
        text: 查询文本

    Returns:
        384 维向量
    """
    model = get_embeddings()
    result = list(model.embed([text]))
    return result[0].tolist()
