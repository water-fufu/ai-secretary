"""笔记相关请求/响应模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NoteResponse(BaseModel):
    """笔记响应"""
    id: int
    folder: str
    file_name: str
    title: Optional[str] = None
    content: str
    source: str
    is_archived: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteCreateRequest(BaseModel):
    """创建笔记请求"""
    folder: str = Field(default="日常行政", max_length=64)
    file_name: str = Field(..., max_length=128)
    title: Optional[str] = Field(default=None, max_length=256)
    content: str = Field(..., min_length=1)
    source: str = Field(default="manual", max_length=32)


class NoteUpdateRequest(BaseModel):
    """更新笔记请求"""
    folder: Optional[str] = Field(default=None, max_length=64)
    file_name: Optional[str] = Field(default=None, max_length=128)
    title: Optional[str] = Field(default=None, max_length=256)
    content: Optional[str] = Field(default=None, min_length=1)
    is_archived: Optional[int] = Field(default=None, ge=0, le=1)


class NoteListResponse(BaseModel):
    """笔记列表响应"""
    total: int
    page: int
    page_size: int
    items: List[NoteResponse]
