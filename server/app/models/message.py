"""消息表模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.database import Base


class Message(Base):
    """
    消息表
    会话中的每条消息（用户提问或 AI 回答）
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="所属会话ID")
    role = Column(String(16), nullable=False, comment="角色：user/assistant/system")
    content = Column(Text, nullable=False, comment="消息内容")
    mode = Column(String(32), nullable=True, comment="处理该消息时的模式")
    sources = Column(JSON, nullable=True, comment="检索来源（数组）")
    has_conflict = Column(Integer, nullable=False, default=0, comment="是否检测到冲突：0否1是")
    conflict_summary = Column(String(512), nullable=True, comment="冲突摘要")
    tokens_used = Column(Integer, nullable=False, default=0, comment="消耗 token 数")
    latency_ms = Column(Integer, nullable=False, default=0, comment="响应延迟（毫秒）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # 关联会话（多对一）
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message id={self.id} conversation_id={self.conversation_id} role={self.role}>"
