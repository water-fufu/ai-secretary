"""
数据迁移脚本：从秘书 1.0 的 Markdown 文件导入到 2.0 数据库

用法：
    python -m app.migrate_from_v1 --vault-path "C:\\AI\\秘书\\tian_shu_vault"

功能：
    1. 遍历指定目录下的所有 .md 文件
    2. 将每篇笔记导入 MySQL notes 表
    3. 切片并导入 chunks 表
    4. 重建 FAISS 向量索引
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db, engine
from app.models.note import Note
from app.models.chunk import Chunk
from app.rag.splitter import split_markdown
from app.rag.vector_store import get_vector_store
from app.core.logging import setup_logging


def scan_vault(vault_path: Path) -> list[dict]:
    """
    遍历天书库目录，返回所有 .md 文件的元信息

    Args:
        vault_path: 天书库根目录路径

    Returns:
        文件信息列表 [{folder, file_name, content, rel_path}]
    """
    IGNORE_DIRS = {".obsidian", ".trash", ".git", "__pycache__", ".claude", "node_modules", ".backup"}
    results = []

    if not vault_path.exists():
        print(f"❌ 目录不存在: {vault_path}")
        return results

    for root, dirs, files in vault_path.walk():
        # 过滤忽略目录
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for fname in files:
            if not fname.endswith(".md"):
                continue

            fpath = root / fname
            rel_path = fpath.relative_to(vault_path)
            folder = str(rel_path.parent) if str(rel_path.parent) != "." else "根目录"

            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ⚠ 读取失败: {rel_path} — {e}")
                continue

            results.append({
                "folder": folder,
                "file_name": fname,
                "content": content,
                "rel_path": str(rel_path),
            })

    return results


async def migrate(vault_path: str) -> None:
    """
    执行数据迁移

    Args:
        vault_path: 天书库目录路径
    """
    setup_logging()
    print("=" * 60)
    print("📦 秘书 1.0 → 2.0 数据迁移")
    print("=" * 60)

    # 1. 初始化数据库
    print("\n1️⃣  初始化数据库...")
    await init_db()
    print("   ✅ 数据库初始化完成")

    # 2. 扫描文件
    print(f"\n2️⃣  扫描天书库: {vault_path}")
    files = scan_vault(Path(vault_path))
    print(f"   ✅ 找到 {len(files)} 个笔记文件")

    if not files:
        print("\n⚠ 没有找到可迁移的文件，退出")
        return

    # 3. 导入笔记和切片
    print("\n3️⃣  导入笔记和切片...")
    imported_count = 0
    skipped_count = 0
    all_chunks = []

    async with AsyncSessionLocal() as db:
        for file_info in files:
            # 检查是否已存在
            existing = (await db.execute(
                select(Note).where(
                    Note.folder == file_info["folder"],
                    Note.file_name == file_info["file_name"],
                )
            )).scalar_one_or_none()

            if existing:
                print(f"   ⏭  跳过（已存在）: {file_info['rel_path']}")
                skipped_count += 1
                continue

            # 创建笔记
            note = Note(
                folder=file_info["folder"],
                file_name=file_info["file_name"],
                content=file_info["content"],
                source="import",
            )
            db.add(note)
            await db.flush()  # 获取 note.id

            # 切片
            chunks = split_markdown(file_info["content"], metadata={
                "folder": file_info["folder"],
                "file_name": file_info["file_name"],
                "note_id": note.id,
            })

            # 保存切片到数据库
            for i, chunk in enumerate(chunks):
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
                all_chunks.append(chunk)

            imported_count += 1
            print(f"   ✅ 导入: {file_info['rel_path']} ({len(chunks)} 切片)")

        await db.commit()

    print(f"\n   📊 导入完成: {imported_count} 篇笔记, {len(all_chunks)} 个切片")
    if skipped_count > 0:
        print(f"   ⏭  跳过 {skipped_count} 篇已存在的笔记")

    # 4. 重建 FAISS 索引
    print("\n4️⃣  重建 FAISS 向量索引...")
    try:
        vs = get_vector_store()
        vs.rebuild(all_chunks)
        print("   ✅ 向量索引重建完成")
    except Exception as e:
        print(f"   ⚠ 向量索引重建失败: {e}")
        print("      可稍后通过 API /api/v1/vault/refresh 重建")

    # 5. 完成
    print("\n" + "=" * 60)
    print("🎉 数据迁移完成！")
    print(f"   导入笔记: {imported_count}")
    print(f"   导入切片: {len(all_chunks)}")
    print(f"   跳过笔记: {skipped_count}")
    print("=" * 60)

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="秘书 1.0 → 2.0 数据迁移工具")
    parser.add_argument(
        "--vault-path",
        type=str,
        default=r"C:\AI\秘书\tian_shu_vault",
        help="天书库目录路径（默认: C:\\AI\\秘书\\tian_shu_vault）",
    )
    args = parser.parse_args()

    asyncio.run(migrate(args.vault_path))


if __name__ == "__main__":
    main()
