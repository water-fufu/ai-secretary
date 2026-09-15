"""
Redis 缓存管理
两层缓存架构：
1. 精确缓存：问题完全相同时命中（SHA-256 哈希）
2. 语义缓存：问题语义相似时命中（向量相似度 > 阈值）
"""
import hashlib
import json
from typing import Optional
from redis.asyncio import Redis

from app.config import settings


class CacheManager:
    """
    缓存管理器
    支持精确缓存和语义缓存
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[Redis] = None

    async def init(self) -> None:
        """初始化 Redis 连接"""
        self._redis = Redis.from_url(
            self.redis_url,
            decode_responses=True,
            encoding="utf-8",
        )
        # 测试连接
        await self._redis.ping()
        print("✅ Redis 缓存已连接")

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis 未初始化，请先调用 init()")
        return self._redis

    # ===== 精确缓存 =====

    def _exact_key(self, question: str) -> str:
        """生成精确缓存的 key"""
        normalized = question.strip().lower()
        return f"cache:exact:{hashlib.sha256(normalized.encode()).hexdigest()}"

    async def get_exact(self, question: str) -> Optional[dict]:
        """
        获取精确缓存

        Args:
            question: 用户问题

        Returns:
            缓存的回答数据，未命中返回 None
        """
        key = self._exact_key(question)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_exact(self, question: str, answer_data: dict) -> None:
        """
        设置精确缓存

        Args:
            question: 用户问题
            answer_data: 回答数据（包含 answer, sources 等）
        """
        key = self._exact_key(question)
        await self.redis.setex(
            key,
            settings.CACHE_EXACT_TTL,
            json.dumps(answer_data, ensure_ascii=False),
        )

    # ===== 语义缓存 =====
    # 语义缓存需要向量相似度搜索，简化实现：
    # 将问题 embedding 存 Redis，新问题先算 embedding，再遍历缓存做相似度
    # 生产环境建议用 RedisVL 或专门的向量数据库

    def _semantic_key(self, embedding_id: str) -> str:
        return f"cache:semantic:{embedding_id}"

    async def get_semantic(
        self,
        question_embedding: list[float],
        threshold: float = None,
    ) -> Optional[dict]:
        """
        获取语义缓存（简化实现）

        Args:
            question_embedding: 问题向量
            threshold: 相似度阈值

        Returns:
            缓存的回答数据，未命中返回 None
        """
        if threshold is None:
            threshold = settings.CACHE_SEMANTIC_THRESHOLD

        # 简化实现：遍历所有语义缓存 key，计算余弦相似度
        # 生产环境应使用 RedisVL 的向量搜索
        keys = await self.redis.keys("cache:semantic:*")
        for key in keys:
            data = await self.redis.get(key)
            if not data:
                continue
            cached = json.loads(data)
            cached_embedding = cached.get("embedding", [])
            similarity = self._cosine_similarity(question_embedding, cached_embedding)
            if similarity >= threshold:
                return cached.get("answer_data")
        return None

    async def set_semantic(
        self,
        question: str,
        question_embedding: list[float],
        answer_data: dict,
    ) -> None:
        """
        设置语义缓存

        Args:
            question: 用户问题
            question_embedding: 问题向量
            answer_data: 回答数据
        """
        embedding_id = hashlib.sha256(question.encode()).hexdigest()[:16]
        key = self._semantic_key(embedding_id)
        await self.redis.setex(
            key,
            settings.CACHE_SEMANTIC_TTL,
            json.dumps({
                "question": question,
                "embedding": question_embedding,
                "answer_data": answer_data,
            }, ensure_ascii=False),
        )

    # ===== 工具方法 =====

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """计算余弦相似度"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    async def clear_all(self) -> None:
        """清空所有缓存"""
        await self.redis.delete(*await self.redis.keys("cache:*"))


# 全局缓存管理器单例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
