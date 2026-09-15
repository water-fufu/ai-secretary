"""
笔记业务服务
处理笔记的增删改查，以及对应的切片和向量索引更新
"""
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.chunk import Chunk
from app.rag.splitter import split_markdown
from app.rag.vector_store import get_vector_store


async def create_note_with_chunks(
    db: AsyncSession,
    folder: str,
    file_name: str,
    content: str,
    title: str = None,
    source: str = "manual",
) -> Tuple[Note, List[Chunk]]:
    """
    创建笔记并生成切片，更新向量索引

    Args:
        db: 数据库 Session
        folder: 文件夹
        file_name: 文件名
        content: Markdown 内容
        title: 标题
        source: 来源

    Returns:
        (笔记对象, 切片列表)
    """
    # 1. 创建笔记
    note = Note(
        folder=folder,
        file_name=file_name,
        title=title,
        content=content,
        source=source,
    )
    db.add(note)
    await db.flush()  # 获取 note.id

    # 2. 切片
    chunks = split_markdown(content, metadata={
        "folder": folder,
        "file_name": file_name,
        "note_id": note.id,
    })

    # 3. 保存切片到数据库
    db_chunks = []
    for i, chunk in enumerate(chunks):
        db_chunk = Chunk(
            note_id=note.id,
            section=chunk.metadata.get("section", ""),
            content=chunk.page_content,
            chunk_index=i,
            timestamp=chunk.metadata.get("timestamp", ""),
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)

    await db.commit()
    await db.refresh(note)
    for c in db_chunks:
        await db.refresh(c)

    # 4. 更新向量索引（异步执行，不阻塞响应）
    # TODO: 可以用后台任务执行，这里先同步
    try:
        vs = get_vector_store()
        # 为每个切片添加 chunk_id 到 metadata
        for chunk, db_chunk in zip(chunks, db_chunks):
            chunk.metadata["chunk_id"] = db_chunk.id
        vs.add_documents(chunks)
    except Exception as e:
        print(f"⚠ 向量索引更新失败: {e}")

    return note, db_chunks


async def update_note_with_chunks(
    db: AsyncSession,
    note_id: int,
    update_data: dict,
) -> Optional[Note]:
    """
    更新笔记并重新切片，更新向量索引

    Args:
        db: 数据库 Session
        note_id: 笔记 ID
        update_data: 更新字段

    Returns:
        更新后的笔记对象，不存在返回 None
    """
    note = await db.get(Note, note_id)
    if not note:
        return None

    # 更新字段
    for key, value in update_data.items():
        if value is not None:
            setattr(note, key, value)

    # 如果内容更新了，重新切片
    if "content" in update_data and update_data["content"] is not None:
        # 删除旧切片
        old_chunks = (await db.execute(
            select(Chunk).where(Chunk.note_id == note_id)
        )).scalars().all()
        old_chunk_ids = [c.id for c in old_chunks]
        for c in old_chunks:
            await db.delete(c)

        # 生成新切片
        new_chunks = split_markdown(note.content, metadata={
            "folder": note.folder,
            "file_name": note.file_name,
            "note_id": note.id,
        })
        for i, chunk in enumerate(new_chunks):
            db_chunk = Chunk(
                note_id=note.id,
                section=chunk.metadata.get("section", ""),
                content=chunk.page_content,
                chunk_index=i,
                timestamp=chunk.metadata.get("timestamp", ""),
            )
            db.add(db_chunk)
            await db.flush()
            chunk.metadata["chunk_id"] = db_chunk.id

        # 更新向量索引（简化：标记删除旧的，添加新的）
        try:
            vs = get_vector_store()
            vs.remove_by_chunk_ids(old_chunk_ids)
            vs.add_documents(new_chunks)
        except Exception as e:
            print(f"⚠ 向量索引更新失败: {e}")

    await db.commit()
    await db.refresh(note)
    return note


async def delete_note_with_chunks(db: AsyncSession, note_id: int) -> bool:
    """
    删除笔记及其切片，更新向量索引

    Args:
        db: 数据库 Session
        note_id: 笔记 ID

    Returns:
        是否删除成功
    """
    note = await db.get(Note, note_id)
    if not note:
        return False

    # 获取切片 ID 用于更新向量索引
    chunks = (await db.execute(
        select(Chunk).where(Chunk.note_id == note_id)
    )).scalars().all()
    chunk_ids = [c.id for c in chunks]

    # 删除笔记（级联删除切片）
    await db.delete(note)
    await db.commit()

    # 更新向量索引
    try:
        vs = get_vector_store()
        vs.remove_by_chunk_ids(chunk_ids)
    except Exception as e:
        print(f"⚠ 向量索引更新失败: {e}")

    return True


async def rebuild_index_from_db(db: AsyncSession) -> dict:
    """
    从数据库全量重建向量索引

    Args:
        db: 数据库 Session

    Returns:
        索引统计信息
    """
    # 从数据库读取所有切片
    chunks = (await db.execute(
        select(Chunk).order_by(Chunk.id)
    )).scalars().all()

    # 转换为 Document 格式
    from langchain_core.documents import Document
    documents = []
    for chunk in chunks:
        note = await db.get(Note, chunk.note_id)
        doc = Document(
            page_content=chunk.content,
            metadata={
                "chunk_id": chunk.id,
                "note_id": chunk.note_id,
                "folder": note.folder if note else "未知",
                "file_name": note.file_name if note else "未知",
                "section": chunk.section,
                "timestamp": chunk.timestamp,
            },
        )
        documents.append(doc)

    # 重建索引
    vs = get_vector_store()
    vs.rebuild(documents)

    return {
        "chunk_count": len(documents),
        "note_count": (await db.execute(select(func.count(Note.id)))).scalar() or 0,
    }


async def get_vault_stats(db: AsyncSession) -> dict:
    """
    获取知识库统计信息

    Args:
        db: 数据库 Session

    Returns:
        统计信息
    """
    note_count = (await db.execute(select(func.count(Note.id)))).scalar() or 0
    chunk_count = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0

    # 文件夹数量
    folders = (await db.execute(
        select(Note.folder).distinct()
    )).scalars().all()

    vs = get_vector_store()
    vs_stats = vs.get_stats()

    return {
        "folder_count": len(folders),
        "folders": folders,
        "file_count": note_count,
        "chunk_count": chunk_count,
        "vector_indexed": vs_stats["chunk_count"],
        "last_update": None,  # TODO: 从数据库获取
    }
