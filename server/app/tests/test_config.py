"""
单元测试：配置模块
"""
import pytest
from app.config import Settings


class TestSettings:
    """配置测试"""

    def test_default_values(self):
        """测试默认配置值"""
        settings = Settings()
        assert settings.APP_NAME == "秘书 2.0 API"
        assert settings.APP_VERSION == "2.0.0"
        assert settings.LLM_MODEL == "deepseek-chat"
        assert settings.TOP_K == 3
        # paraphrase-multilingual-MiniLM-L12-v2 多语言嵌入模型（支持中文，384 维，120MB）
        assert settings.EMBEDDING_MODEL == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def test_hybrid_rag_config(self):
        """测试 Hybrid RAG（BM25+向量）配置"""
        settings = Settings()
        assert settings.HYBRID_ENABLED is True
        assert 0 < settings.HYBRID_BM25_WEIGHT <= 1
        assert 0 < settings.HYBRID_VECTOR_WEIGHT <= 1
        assert settings.BM25_TOP_K > 0

    def test_cors_origins_type(self):
        """测试 CORS 配置类型"""
        settings = Settings()
        assert isinstance(settings.CORS_ORIGINS, list)
        assert "*" in settings.CORS_ORIGINS

    def test_cache_ttl_positive(self):
        """测试缓存 TTL 为正数"""
        settings = Settings()
        assert settings.CACHE_EXACT_TTL > 0
        assert settings.CACHE_SEMANTIC_TTL > 0
        assert 0 < settings.CACHE_SEMANTIC_THRESHOLD <= 1
