"""笔记 CRUD 接口（P3 实现基础 CRUD）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.note import Note
from app.schemas.note import (
    NoteResponse,
    NoteCreateRequest,
    NoteUpdateRequest,
    NoteListResponse,
)

router = APIRouter(prefix="/notes", tags=["笔记管理"])


@router.get("", response_model=NoteListResponse)
async def list_notes(
    folder: str = Query(default=None, description="按文件夹筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取笔记列表（分页 + 文件夹筛选）"""
    # 构建查询
    query = select(Note).where(Note.is_archived == 0)
    count_query = select(func.count()).select_from(Note).where(Note.is_archived == 0)

    if folder:
        query = query.where(Note.folder == folder)
        count_query = count_query.where(Note.folder == folder)

    # 总数
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    query = query.order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    notes = result.scalars().all()

    return NoteListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[NoteResponse.model_validate(n) for n in notes],
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int, db: AsyncSession = Depends(get_db)):
    """获取笔记详情"""
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return NoteResponse.model_validate(note)


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(request: NoteCreateRequest, db: AsyncSession = Depends(get_db)):
    """创建笔记"""
    # 检查 folder + file_name 是否重复
    existing = await db.execute(
        select(Note).where(Note.folder == request.folder, Note.file_name == request.file_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该文件夹下已存在同名笔记")

    note = Note(
        folder=request.folder,
        file_name=request.file_name,
        title=request.title,
        content=request.content,
        source=request.source,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # TODO: P4 触发切片 + 向量化 + FAISS 索引更新
    return NoteResponse.model_validate(note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    request: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新笔记"""
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    # 更新非空字段
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(note, key, value)

    await db.commit()
    await db.refresh(note)

    # TODO: P4 触发重新切片 + 索引更新
    return NoteResponse.model_validate(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: int, db: AsyncSession = Depends(get_db)):
    """删除笔记（级联删除切片）"""
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    await db.delete(note)
    await db.commit()

    # TODO: P4 从 FAISS 索引中删除对应切片
    return None
