"""
单元测试：文档切片模块
"""
import pytest
from app.rag.splitter import split_markdown, extract_timestamp


class TestExtractTimestamp:
    """时间戳提取测试"""

    def test_extract_standard_format(self):
        """测试标准格式 YYYY-MM-DD HH:MM"""
        text = "创建时间: 2026-09-14 15:30\n一些内容"
        assert extract_timestamp(text) == "2026-09-14 15:30"

    def test_extract_date_only(self):
        """测试仅日期格式"""
        text = "2026-09-14\n一些内容"
        assert extract_timestamp(text) == "2026-09-14"

    def test_extract_slash_format(self):
        """测试斜杠格式"""
        text = "记录于 2026/09/14"
        assert extract_timestamp(text) == "2026/09/14"

    def test_extract_chinese_label(self):
        """测试中文标签"""
        text = "更新时间：2026-09-14 10:00"
        assert extract_timestamp(text) == "2026-09-14 10:00"

    def test_no_timestamp(self):
        """测试无时间戳"""
        text = "这是一段没有时间的内容"
        assert extract_timestamp(text) == "未知"


class TestSplitMarkdown:
    """Markdown 切片测试"""

    def test_split_by_h2(self):
        """测试按二级标题切片"""
        content = "# 标题\n\n## 第一节\n\n内容一\n\n## 第二节\n\n内容二"
        chunks = split_markdown(content)
        assert len(chunks) >= 2
        assert any("第一节" in c.metadata.get("section", "") for c in chunks)

    def test_preserve_metadata(self):
        """测试元数据保留"""
        content = "# 标题\n\n## 测试\n\n内容"
        metadata = {"folder": "测试", "file_name": "test.md"}
        chunks = split_markdown(content, metadata=metadata)
        assert all(c.metadata.get("folder") == "测试" for c in chunks)
        assert all(c.metadata.get("file_name") == "test.md" for c in chunks)

    def test_empty_content(self):
        """测试空内容返回空列表"""
        chunks = split_markdown("")
        assert len(chunks) == 0

    def test_chunk_index_assigned(self):
        """测试 chunk_index 分配"""
        content = "# 标题\n\n## A\n\n内容A\n\n## B\n\n内容B"
        chunks = split_markdown(content)
        indices = [c.metadata.get("chunk_index") for c in chunks]
        assert indices == list(range(len(chunks)))
