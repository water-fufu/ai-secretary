"""
FAISS 向量库持久化管理
- 启动时从磁盘加载索引（load_local）
- 写入后保存到磁盘（save_local）
- 维护 chunk.id 与 FAISS 内部 id 的映射
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings
from app.rag.embeddings import get_embeddings


class VectorStoreManager:
    """
    FAISS 向量库管理器
    负责索引的加载、保存、添加、删除、检索
    """

    def __init__(self, index_path: str = None):
        """
        初始化向量库管理器

        Args:
            index_path: 索引文件存储目录，默认使用配置中的路径
        """
        self.index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self.index_path.mkdir(parents=True, exist_ok=True)

        self.index_file = self.index_path / "index.faiss"
        self.meta_file = self.index_path / "index_meta.json"

        # chunk.id -> FAISS 内部 id 的映射
        self._id_map: Dict[int, int] = {}
        # FAISS 内部 id -> chunk.id 的反向映射
        self._reverse_id_map: Dict[int, int] = {}

        self._vector_store: Optional[FAISS] = None

    @property
    def is_initialized(self) -> bool:
        """向量索引是否已初始化（可用于检索）"""
        return self._vector_store is not None

    def load(self) -> bool:
        """
        从磁盘加载索引

        Returns:
            True 表示加载成功，False 表示索引不存在需重建
        """
        if not self.index_file.exists():
            print("⚠ FAISS 索引文件不存在，需要重建")
            return False

        try:
            embeddings = get_embeddings()
            self._vector_store = FAISS.load_local(
                str(self.index_path),
                embeddings,
                allow_dangerous_deserialization=True,
            )

            # 加载 id 映射
            if self.meta_file.exists():
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self._id_map = {int(k): v for k, v in meta.get("id_map", {}).items()}
                self._reverse_id_map = {int(k): v for k, v in meta.get("reverse_id_map", {}).items()}

            print(f"✅ FAISS 索引已加载: {len(self._id_map)} 个切片")
            return True
        except Exception as e:
            print(f"⚠ FAISS 索引加载失败: {e}，需要重建")
            return False

    def save(self) -> None:
        """保存索引到磁盘"""
        if self._vector_store is None:
            return

        try:
            self._vector_store.save_local(str(self.index_path))

            # 保存 id 映射
            meta = {
                "id_map": {str(k): v for k, v in self._id_map.items()},
                "reverse_id_map": {str(k): v for k, v in self._reverse_id_map.items()},
                "version": "2.0",
            }
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            print(f"💾 FAISS 索引已保存: {len(self._id_map)} 个切片")
        except Exception as e:
            print(f"⚠ FAISS 索引保存失败: {e}")

    def rebuild(self, documents: List[Document]) -> None:
        """
        全量重建索引

        Args:
            documents: 带 metadata 的 Document 列表，metadata 中必须包含 chunk_id
        """
        if not documents:
            # 空文档：不创建索引，避免触发 embedding 模型下载
            # 首次写入笔记时会自动创建索引
            print("⚠ 无切片数据，跳过索引重建")
            self._vector_store = None
            self._id_map = {}
            self._reverse_id_map = {}
            return

        embeddings = get_embeddings()
        self._vector_store = FAISS.from_documents(documents, embeddings)

        # 重建 id 映射（FAISS 内部 id 从 0 开始，按添加顺序）
        self._id_map = {}
        self._reverse_id_map = {}
        for i, doc in enumerate(documents):
            chunk_id = doc.metadata.get("chunk_id", i)
            self._id_map[chunk_id] = i
            self._reverse_id_map[i] = chunk_id

        self.save()
        print(f"🔄 FAISS 索引已重建: {len(documents)} 个切片")

    def add_documents(self, documents: List[Document]) -> List[int]:
        """
        增量添加文档到索引

        Args:
            documents: 带 metadata 的 Document 列表

        Returns:
            新增的 chunk.id 列表
        """
        if self._vector_store is None:
            self.rebuild(documents)
            return [d.metadata.get("chunk_id") for d in documents]

        # FAISS 内部 id 从当前数量开始
        start_id = len(self._id_map)
        added_chunk_ids = []

        for i, doc in enumerate(documents):
            faiss_id = start_id + i
            chunk_id = doc.metadata.get("chunk_id", faiss_id)
            self._id_map[chunk_id] = faiss_id
            self._reverse_id_map[faiss_id] = chunk_id
            added_chunk_ids.append(chunk_id)

        self._vector_store.add_documents(documents)
        self.save()
        return added_chunk_ids

    def remove_by_chunk_ids(self, chunk_ids: List[int]) -> None:
        """
        按 chunk.id 删除索引中的向量
        注意：FAISS 删除后内部 id 会变化，这里采用"标记删除+重建"的简化策略
        实际生产环境可使用 FAISS IDMap 等更高效的方式

        Args:
            chunk_ids: 要删除的 chunk.id 列表
        """
        if not chunk_ids or self._vector_store is None:
            return

        # 从映射中移除
        for cid in chunk_ids:
            if cid in self._id_map:
                del self._id_map[cid]

        # 重建反向映射
        self._reverse_id_map = {v: k for k, v in self._id_map.items()}

        # 简化处理：保存映射（实际向量删除需要全量重建，这里标记后下次重建时生效）
        self.save()
        print(f"🗑 已标记删除 {len(chunk_ids)} 个切片（下次重建时生效）")

    def similarity_search(
        self, query: str, k: int = 3, folder_filter: str = None
    ) -> List[Document]:
        """
        相似度检索

        Args:
            query: 查询文本
            k: 返回结果数量
            folder_filter: 按文件夹过滤

        Returns:
            最相关的 Document 列表
        """
        if self._vector_store is None:
            return []

        try:
            if folder_filter:
                # 先多检索一些，再按 folder 过滤
                docs = self._vector_store.similarity_search(
                    query, k=k * 3, filter={"folder": folder_filter}
                )
                return docs[:k]
            else:
                return self._vector_store.similarity_search(query, k=k)
        except Exception as e:
            print(f"⚠ 检索失败: {e}")
            return []

    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "chunk_count": len(self._id_map),
            "index_path": str(self.index_path),
            "has_index": self._vector_store is not None,
        }


# 全局向量库管理器单例
_vector_store_manager: Optional[VectorStoreManager] = None


def get_vector_store() -> VectorStoreManager:
    """获取向量库管理器单例"""
    global _vector_store_manager
    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager()
    return _vector_store_manager
