"""
天书写入服务
处理写入预览和确认写入
"""
import re
from datetime import datetime
from typing import Dict, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm
from app.rag.prompts import WRITE_FORMAT_PROMPT, WRITE_MATCH_PROMPT
from app.services.note_service import create_note_with_chunks
from sqlalchemy.ext.asyncio import AsyncSession


async def format_content_for_write(content: str) -> str:
    """
    将用户零散输入整理为规范的 Markdown 格式

    Args:
        content: 用户原始输入

    Returns:
        格式化后的 Markdown 内容
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt_text = WRITE_FORMAT_PROMPT.format(content=content, timestamp=timestamp)

    try:
        llm = get_llm()
        response = llm.invoke(prompt_text)
        return response.content.strip()
    except Exception as e:
        print(f"⚠ 内容格式化失败: {e}，使用原始内容")
        return f"> 记录时间: {timestamp}\n\n## 记录\n\n{content}"


async def match_write_target(
    formatted_content: str,
    vault_tree: str,
) -> Dict:
    """
    匹配写入的目标文件夹和笔记文件

    Args:
        formatted_content: 格式化后的内容
        vault_tree: 现有知识库目录树

    Returns:
        {folder, file_name, is_new_file}
    """
    summary = formatted_content[:500]
    prompt_text = WRITE_MATCH_PROMPT.format(vault_tree=vault_tree, summary=summary)

    try:
        llm = get_llm()
        response = llm.invoke(prompt_text)
        raw = response.content.strip()

        # 清理 markdown 代码块
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        import json
        return json.loads(raw)
    except Exception as e:
        print(f"⚠ 写入路径匹配失败: {e}，使用默认路径")
        return {
            "folder": "日常行政",
            "file_name": "工作日志.md",
            "is_new_file": False,
        }


async def write_preview(
    content: str,
    vault_tree: str,
) -> Tuple[str, Dict]:
    """
    写入预览：格式化内容 + 匹配路径

    Args:
        content: 用户原始输入
        vault_tree: 知识库目录树

    Returns:
        (预览文本, 待写入数据 {formatted_content, folder, file_name, is_new_file})
    """
    formatted = await format_content_for_write(content)
    match = await match_write_target(formatted, vault_tree)

    folder = match.get("folder", "日常行政")
    file_name = match.get("file_name", "工作日志.md")
    is_new = match.get("is_new_file", False)

    new_tag = "🆕 新建" if is_new else "📝 追加"
    preview = (
        f"**{new_tag} 天书写入预览**\n\n"
        f"📂 目标路径: `{folder}/{file_name}`\n\n"
        f"---\n{formatted}\n---\n\n"
        "⚠ 请确认以上内容无误，点击「确认写入」执行写入。"
    )

    pending = {
        "formatted_content": formatted,
        "folder": folder,
        "file_name": file_name,
        "is_new_file": is_new,
    }
    return preview, pending


async def confirm_write(
    db: AsyncSession,
    formatted_content: str,
    folder: str,
    file_name: str,
) -> Dict:
    """
    确认写入：执行实际的笔记创建或追加

    Args:
        db: 数据库 Session
        formatted_content: 格式化后的内容
        folder: 目标文件夹
        file_name: 目标文件名
        is_new_file: 是否新建文件

    Returns:
        写入结果
    """
    from sqlalchemy import select
    from app.models.note import Note

    # 路径安全校验
    for val, name in [(folder, "folder"), (file_name, "file_name")]:
        if ".." in val or "/" in val or "\\" in val:
            return {"success": False, "message": f"{name} 包含非法字符"}

    if not file_name.endswith(".md"):
        file_name += ".md"

    # 检查笔记是否存在
    existing = (await db.execute(
        select(Note).where(Note.folder == folder, Note.file_name == file_name)
    )).scalar_one_or_none()

    if existing:
        # 追加到现有笔记
        new_content = existing.content + f"\n\n---\n\n{formatted_content}\n"
        from app.services.note_service import update_note_with_chunks
        note = await update_note_with_chunks(db, existing.id, {"content": new_content})
        action = "追加"
    else:
        # 新建笔记
        note, _ = await create_note_with_chunks(
            db=db,
            folder=folder,
            file_name=file_name,
            content=formatted_content,
            source="ai_write",
        )
        action = "新建"

    return {
        "success": True,
        "message": f"✅ 已写入天书（{action}）",
        "folder": folder,
        "file_name": file_name,
        "note_id": note.id,
    }
