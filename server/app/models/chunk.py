"""切片表模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Chunk(Base):
    """
    切片表
    存储向量化后的文本块，关联笔记
    embedding 向量存在 FAISS 索引文件中，通过 chunk.id 与 FAISS 内部 id 对应
    """
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, comment="所属笔记ID")
    section = Column(String(256), nullable=True, comment="来自 h2 标题的章节名")
    content = Column(Text, nullable=False, comment="切片文本内容")
    chunk_index = Column(Integer, nullable=False, default=0, comment="在笔记中的顺序索引")
    timestamp = Column(String(32), nullable=True, comment="提取的时间戳")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # 关联笔记（多对一）
    note = relationship("Note", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk id={self.id} note_id={self.note_id} section={self.section}>"
