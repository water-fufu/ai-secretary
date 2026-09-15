"""
LLM 客户端管理
DeepSeek API 单例，避免重复初始化
"""
from typing import Optional
from langchain_deepseek import ChatDeepSeek

from app.config import settings

# 全局 LLM 单例
_llm: Optional[ChatDeepSeek] = None


def get_llm() -> ChatDeepSeek:
    """
    获取 DeepSeek LLM 单例

    Returns:
        ChatDeepSeek 实例

    Raises:
        RuntimeError: 未配置 DEEPSEEK_API_KEY
    """
    global _llm
    if _llm is None:
        api_key = settings.DEEPSEEK_API_KEY
        if not api_key:
            raise RuntimeError(
                "未找到 DEEPSEEK_API_KEY 环境变量！\n"
                "请在 CloudBase 环境变量中配置 DEEPSEEK_API_KEY"
            )
        _llm = ChatDeepSeek(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=api_key,
        )
        print(f"✅ LLM 已初始化: {settings.LLM_MODEL}")
    return _llm
