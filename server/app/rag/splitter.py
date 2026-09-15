"""
文档切片模块
使用 MarkdownHeaderTextSplitter 按标题层级切分，保留语义完整性
"""
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from langchain_core.documents import Document
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter


def extract_timestamp(text: str) -> str:
    """
    从文本中提取时间戳
    支持多种格式：YYYY-MM-DD HH:MM, YYYY-MM-DD, YYYY/MM/DD, 创建时间/更新时间
    提取不到返回 '未知'
    """
    patterns = [
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}/\d{2}/\d{2})",
        r"创建时间[：:]\s*(\S+)",
        r"更新时间[：:]\s*(\S+)",
        r"记录时间[：:]\s*(\S+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "未知"


def split_markdown(content: str, metadata: Optional[Dict] = None) -> List[Document]:
    """
    将 Markdown 内容按标题层级切片

    Args:
        content: Markdown 文本内容
        metadata: 附加到每个切片的元数据（folder, file_name, file_path 等）

    Returns:
        切片后的 Document 列表，每个切片带有标题元数据
    """
    # 按 # 和 ## 标题切分，保留标题信息
    headers_to_split = [
        ("#", "h1"),
        ("##", "h2"),
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split,
        strip_headers=False,
    )

    try:
        chunks = splitter.split_text(content)
    except Exception as e:
        print(f"  ⚠ 切片失败: {e}")
        # 切片失败时返回整个文档作为一个切片
        return [Document(page_content=content, metadata=metadata or {})]

    # 为每个切片添加元数据
    result = []
    for i, chunk in enumerate(chunks):
        chunk_metadata = dict(metadata or {})
        chunk_metadata.update({
            "section": chunk.metadata.get("h2", chunk.metadata.get("h1", "未分类")),
            "timestamp": extract_timestamp(chunk.page_content),
            "chunk_index": i,
        })
        chunk.metadata = chunk_metadata
        result.append(chunk)

    return result
