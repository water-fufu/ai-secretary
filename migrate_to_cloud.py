"""
云端数据迁移脚本：通过 API 将秘书 1.0 的 Markdown 文件导入到云端 2.0

用法：
    python migrate_to_cloud.py --api-url "https://mishu-api-xxx.sh.run.tcloudbase.com"

功能：
    1. 遍历天书库目录下的所有 .md 文件
    2. 通过 POST /api/v1/notes 逐个创建笔记
    3. 全部导入后调用 POST /api/v1/vault/refresh 重建 FAISS 索引
"""
import argparse  # 命令行参数解析
import sys  # 系统模块，用于路径操作和退出
from pathlib import Path  # 路径处理

import httpx  # 异步 HTTP 客户端，用于调用云端 API


def scan_vault(vault_path: Path) -> list[dict]:
    """
    遍历天书库目录，返回所有 .md 文件的元信息

    Args:
        vault_path: 天书库根目录路径

    Returns:
        文件信息列表 [{folder, file_name, content, rel_path}]
    """
    # 需要忽略的目录名集合（Obsidian 配置、回收站、版本控制等）
    IGNORE_DIRS = {".obsidian", ".trash", ".git", "__pycache__", ".claude", "node_modules", ".backup"}
    results = []  # 存储所有扫描到的文件信息

    # 检查目录是否存在
    if not vault_path.exists():
        print(f"目录不存在: {vault_path}")
        return results

    # 递归遍历目录
    for root, dirs, files in vault_path.walk():
        # 过滤掉忽略目录（修改 dirs 就地过滤，影响后续递归）
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for fname in files:
            # 只处理 .md 文件
            if not fname.endswith(".md"):
                continue

            fpath = root / fname  # 完整文件路径
            rel_path = fpath.relative_to(vault_path)  # 相对于天书库根目录的路径
            # 文件夹名：如果在根目录则用"根目录"，否则用父目录名
            folder = str(rel_path.parent) if str(rel_path.parent) != "." else "根目录"

            # 读取文件内容（UTF-8 编码）
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  读取失败: {rel_path} — {e}")
                continue

            # 收集文件信息
            results.append({
                "folder": folder,
                "file_name": fname,
                "content": content,
                "rel_path": str(rel_path),
            })

    return results


async def migrate(api_url: str, vault_path: str) -> None:
    """
    执行云端数据迁移

    Args:
        api_url: 云端 API 基础地址（如 https://mishu-api-xxx.sh.run.tcloudbase.com）
        vault_path: 天书库目录路径
    """
    print("=" * 60)
    print("秘书 1.0 → 云端 2.0 数据迁移")
    print("=" * 60)

    # 1. 扫描天书库文件
    print(f"\n1. 扫描天书库: {vault_path}")
    files = scan_vault(Path(vault_path))
    print(f"   找到 {len(files)} 个笔记文件")

    if not files:
        print("\n没有找到可迁移的文件，退出")
        return

    # 2. 通过 API 逐个导入笔记
    print(f"\n2. 通过 API 导入笔记到: {api_url}")
    imported_count = 0  # 成功导入的笔记数
    skipped_count = 0  # 跳过的笔记数（已存在）
    failed_count = 0  # 导入失败的笔记数

    # 创建异步 HTTP 客户端，设置较长超时（大文件导入可能较慢）
    async with httpx.AsyncClient(base_url=api_url, timeout=60.0) as client:
        for file_info in files:
            # 构造创建笔记的请求体
            payload = {
                "folder": file_info["folder"],  # 文件夹名
                "file_name": file_info["file_name"],  # 文件名
                "content": file_info["content"],  # 文件内容
                "source": "import",  # 来源标记为导入
            }

            try:
                # 调用创建笔记接口
                response = await client.post("/api/v1/notes", json=payload)

                if response.status_code == 201:
                    # 201 = 创建成功
                    imported_count += 1
                    print(f"   导入成功: {file_info['rel_path']}")
                elif response.status_code == 400:
                    # 400 = 可能是重复笔记（folder + file_name 已存在）
                    skipped_count += 1
                    print(f"   跳过（已存在）: {file_info['rel_path']}")
                else:
                    # 其他错误
                    failed_count += 1
                    print(f"   导入失败 [{response.status_code}]: {file_info['rel_path']} — {response.text}")
            except Exception as e:
                # 网络异常等
                failed_count += 1
                print(f"   导入异常: {file_info['rel_path']} — {e}")

    # 3. 重建 FAISS 向量索引
    print(f"\n3. 重建 FAISS 向量索引...")
    try:
        async with httpx.AsyncClient(base_url=api_url, timeout=120.0) as client:
            # 调用索引重建接口（从数据库全量重建，可能较慢）
            response = await client.post("/api/v1/vault/refresh")
            if response.status_code == 200:
                result = response.json()
                print(f"   索引重建完成: {result.get('note_count', '?')} 篇笔记, {result.get('chunk_count', '?')} 个切片")
            else:
                print(f"   索引重建失败 [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"   索引重建异常: {e}")

    # 4. 输出统计结果
    print("\n" + "=" * 60)
    print("数据迁移完成！")
    print(f"   成功导入: {imported_count} 篇")
    print(f"   跳过（已存在）: {skipped_count} 篇")
    print(f"   失败: {failed_count} 篇")
    print("=" * 60)


def main():
    """命令行入口函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="秘书 1.0 → 云端 2.0 数据迁移工具（通过 API）")
    parser.add_argument(
        "--api-url",
        type=str,
        default="https://mishu-api-313736-9-1487983071.sh.run.tcloudbase.com",
        help="云端 API 基础地址",
    )
    parser.add_argument(
        "--vault-path",
        type=str,
        default=r"C:\AI\秘书\tian_shu_vault",
        help="天书库目录路径",
    )
    args = parser.parse_args()

    # 检查 httpx 是否已安装
    try:
        import httpx  # noqa: F401
    except ImportError:
        print("错误: 需要安装 httpx 库，请运行: pip install httpx")
        sys.exit(1)

    # 执行异步迁移
    import asyncio
    asyncio.run(migrate(args.api_url, args.vault_path))


if __name__ == "__main__":
    main()
