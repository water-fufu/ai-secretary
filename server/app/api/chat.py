"""聊天接口（SSE 流式输出）"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest, WritePreviewRequest, WriteConfirmRequest
from app.services.chat_service import (
    run_qa_stream,
    run_plan_stream,
    run_claude_stream,
    detect_task_mode,
    sse_event,
)
from app.services.write_service import write_preview, confirm_write

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    通用聊天接口（SSE 流式输出）
    根据模式自动分发到对应链路
    """
    mode = detect_task_mode(request.message, request.mode)

    if mode == "plan":
        return StreamingResponse(
            run_plan_stream(request.message, db=db),
            media_type="text/event-stream",
        )
    elif mode == "claude":
        return StreamingResponse(
            run_claude_stream(request.message, db=db),
            media_type="text/event-stream",
        )
    else:
        # qa 和 write 模式都走问答链路（write 模式由前端调用 /write/preview）
        return StreamingResponse(
            run_qa_stream(request.message, db=db),
            media_type="text/event-stream",
        )


@router.post("/qa")
async def chat_qa(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """知识库问答（SSE 流式输出）"""
    return StreamingResponse(
        run_qa_stream(request.message, db=db),
        media_type="text/event-stream",
    )


@router.post("/plan")
async def chat_plan(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """生成工作计划（SSE 流式输出）"""
    return StreamingResponse(
        run_plan_stream(request.message, db=db),
        media_type="text/event-stream",
    )


@router.post("/claude")
async def chat_claude(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """生成 Claude 指令（SSE 流式输出）"""
    return StreamingResponse(
        run_claude_stream(request.message, db=db),
        media_type="text/event-stream",
    )


@router.post("/write/preview")
async def write_preview_endpoint(request: WritePreviewRequest, db: AsyncSession = Depends(get_db)):
    """
    写入预览
    返回格式化后的内容和建议的写入路径
    """
    # TODO: 获取知识库目录树
    vault_tree = "# 📚 天书库结构\n\n## 📁 日常行政\n  - 📝 工作日志.md\n## 📁 项目管理\n  - 📝 项目A.md\n  - 📝 项目B.md\n## 📁 技术栈笔记\n  - 📝 技术选型.md\n## 📁 联系人信息\n  - 📝 通讯录.md\n## 📁 待办事项\n  - 📝 任务清单.md"

    preview, pending = await write_preview(request.content, vault_tree)
    return {
        "preview": preview,
        "pending": pending,
    }


@router.post("/write/confirm")
async def write_confirm_endpoint(request: WriteConfirmRequest, db: AsyncSession = Depends(get_db)):
    """确认写入"""
    result = await confirm_write(
        db=db,
        formatted_content=request.formatted_content,
        folder=request.folder,
        file_name=request.file_name,
    )
    return result
