"""会话表模型"""
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class Conversation(Base):
    """
    会话表
    一次连续对话，包含多条消息
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    title = Column(String(256), nullable=False, default="新对话", comment="会话标题")
    mode = Column(String(32), nullable=False, default="auto", comment="默认模式：auto/qa/plan/write/claude")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联消息（一对多）
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation id={self.id} title={self.title}>"
