"""聊天相关请求/响应模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    mode: str = Field(default="auto", description="模式：auto/qa/plan/write/claude")
    conversation_id: Optional[int] = Field(default=None, description="会话ID，不传则新建")


class ChatSource(BaseModel):
    """检索来源"""
    folder: str
    file_name: str
    section: Optional[str] = None
    timestamp: Optional[str] = None


class ChatDoneEvent(BaseModel):
    """SSE done 事件数据"""
    answer: str
    sources: List[ChatSource] = []
    tokens_used: int = 0
    latency_ms: int = 0
    has_conflict: bool = False
    conflict_summary: Optional[str] = None


class WritePreviewRequest(BaseModel):
    """写入预览请求"""
    content: str = Field(..., min_length=1, description="要记录的内容")


class WritePreviewResponse(BaseModel):
    """写入预览响应"""
    formatted_content: str
    folder: str
    file_name: str
    is_new_file: bool


class WriteConfirmRequest(BaseModel):
    """确认写入请求"""
    formatted_content: str
    folder: str
    file_name: str
