"""
BM25 关键词检索模块（Hybrid RAG 的稀疏检索通道）

与向量检索互补：
- 向量检索擅长语义相似（"汽车"≈"轿车"）
- BM25 擅长精确匹配（错误码、专业术语、版本号）
- 两者通过 RRF 算法融合，实现 Hybrid Search

特点：
- 零模型依赖，纯 CPU，毫秒级响应
- jieba 中文分词
- 单例模式，索引懒加载+缓存
"""
import re
from typing import List, Optional, Dict

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.config import settings


# 全局 BM25 索引单例
_bm25_instance: Optional["BM25Retriever"] = None


class BM25Retriever:
    """
    BM25 检索器

    维护一个 BM25Okapi 索引，从数据库切片构建，支持关键词检索。
    """

    def __init__(self):
        """初始化空检索器，需调用 build() 从数据库构建索引"""
        self._bm25: Optional[BM25Okapi] = None  # BM25 索引对象
        self._chunk_ids: List[int] = []          # 切片 ID 列表（与索引位置一一对应）
        self._chunk_map: Dict[int, dict] = {}    # chunk_id -> 切片元信息
        self._built = False                       # 索引是否已构建

    @property
    def is_built(self) -> bool:
        """索引是否已构建"""
        return self._built and self._bm25 is not None

    async def build(self, db: AsyncSession) -> int:
        """
        从数据库所有切片构建 BM25 索引

        Args:
            db: 数据库会话

        Returns:
            索引中的切片数量
        """
        # 从数据库读取所有切片
        result = await db.execute(
            select(Chunk).order_by(Chunk.id)
        )
        chunks = result.scalars().all()

        if not chunks:
            self._bm25 = None
            self._chunk_ids = []
            self._chunk_map = {}
            self._built = True
            print("⚠ BM25 索引为空（无切片数据）")
            return 0

        # 预先查询所有 Note，建立 note_id -> (folder, file_name) 映射
        from app.models.note import Note
        note_ids = list(set(c.note_id for c in chunks))
        notes_result = await db.execute(
            select(Note).where(Note.id.in_(note_ids))
        )
        notes = notes_result.scalars().all()
        note_map = {n.id: (n.folder, n.file_name) for n in notes}

        # 对每个切片内容做中文分词
        tokenized_corpus = []
        self._chunk_ids = []
        self._chunk_map = {}

        for chunk in chunks:
            # jieba 分词，过滤空白和标点
            tokens = self._tokenize(chunk.content or "")
            tokenized_corpus.append(tokens)
            self._chunk_ids.append(chunk.id)
            # 从 Note 映射中获取 folder 和 file_name
            folder, file_name = note_map.get(chunk.note_id, ("未知", "未知"))
            self._chunk_map[chunk.id] = {
                "id": chunk.id,
                "note_id": chunk.note_id,
                "content": chunk.content,
                "folder": folder,
                "file_name": file_name,
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
            }

        # 构建 BM25 索引
        self._bm25 = BM25Okapi(tokenized_corpus)
        self._built = True
        print(f"✅ BM25 索引构建完成: {len(chunks)} 个切片")
        return len(chunks)

    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """
        BM25 关键词检索

        Args:
            query: 查询文本
            top_k: 返回数量，默认使用配置

        Returns:
            检索结果列表，每项包含 chunk 信息和 bm25_score
            [{"chunk_id": int, "score": float, "content": str, ...}, ...]
        """
        if top_k is None:
            top_k = settings.BM25_TOP_K

        if not self.is_built or not self._bm25:
            return []

        # 对查询做分词
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # BM25 打分
        scores = self._bm25.get_scores(query_tokens)

        # 按分数降序排序，取 top_k
        ranked = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        # 构造结果
        results = []
        for idx in ranked:
            if scores[idx] <= 0:
                continue  # 跳过零分结果
            chunk_id = self._chunk_ids[idx]
            chunk_info = self._chunk_map.get(chunk_id, {})
            results.append({
                "chunk_id": chunk_id,
                "bm25_score": float(scores[idx]),
                **chunk_info,
            })

        return results

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        中文分词 + 清洗

        Args:
            text: 原始文本

        Returns:
            分词后的 token 列表
        """
        # 移除 markdown 标记和特殊字符，保留中英文和数字
        clean_text = re.sub(r'[#*`>\-\[\](){}|]', ' ', text)
        # jieba 精确模式分词
        tokens = jieba.lcut(clean_text)
        # 过滤空白、单字符标点
        return [t.strip() for t in tokens if t.strip() and len(t.strip()) > 0]


def get_bm25_retriever() -> BM25Retriever:
    """
    获取 BM25 检索器单例

    Returns:
        BM25Retriever 单例（索引可能尚未构建，需调用 build()）
    """
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Retriever()
    return _bm25_instance


async def rebuild_bm25_index(db: AsyncSession) -> int:
    """
    重建 BM25 索引（全量）

    Args:
        db: 数据库会话

    Returns:
        索引中的切片数量
    """
    retriever = get_bm25_retriever()
    return await retriever.build(db)
