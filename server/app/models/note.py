"""笔记表模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class Note(Base):
    """
    笔记表
    存储每篇笔记的元数据和完整 Markdown 内容
    """
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    folder = Column(String(64), nullable=False, default="日常行政", comment="所属文件夹")
    file_name = Column(String(128), nullable=False, comment="文件名（含.md）")
    title = Column(String(256), nullable=True, comment="笔记标题")
    content = Column(Text, nullable=False, comment="完整 Markdown 内容")
    source = Column(String(32), nullable=False, default="manual", comment="来源：manual/import/ai_write")
    is_archived = Column(Integer, nullable=False, default=0, comment="是否归档：0否1是")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联切片（一对多）
    chunks = relationship("Chunk", back_populates="note", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Note id={self.id} folder={self.folder} file={self.file_name}>"
