#!/usr/bin/env python3
"""
秘书 —— Obsidian 知识库 AI Agent 系统
==============================================
基于 LangChain + FAISS + Gradio + DeepSeek API
实现：基础问答(含冲突检测) / 工作计划生成 / Claude指令生成 / 天书写入 四条核心链路

依赖安装:
    pip install langchain langchain-deepseek langchain-community langchain-text-splitters
    pip install langchain-huggingface faiss-cpu numpy gradio sentence-transformers python-dotenv

环境变量:
    DEEPSEEK_API_KEY    DeepSeek API 密钥（必填，可写入 .env 文件）

用法:
    python mishu.py
    首次运行自动创建 ./tian_shu_vault 目录及示例笔记文件。
"""

# ==================== 0. 前置：清除系统代理 ====================
# Windows 系统代理(127.0.0.1:7890)会拦截 HuggingFace / Torch 等库的网络请求
# 必须在任何网络库导入前清除，否则下载模型/配置时会超时
import os as _os
for _k in list(_os.environ.keys()):
    if 'proxy' in _k.lower():
        del _os.environ[_k]
_os.environ['HTTP_PROXY'] = ''
_os.environ['HTTPS_PROXY'] = ''
_os.environ['NO_PROXY'] = '*'
_os.environ['HF_HUB_OFFLINE'] = '1'  # 强制 HuggingFace Hub 离线模式，使用本地缓存

# ==================== 1. 导入模块 ====================
import os, re, shutil, time, json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_deepseek import ChatDeepSeek

import gradio as gr

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==================== 1. 全局配置 ====================
VAULT_ROOT = Path("./tian_shu_vault")
IGNORE_DIRS = {".obsidian", ".trash", ".git", "__pycache__", ".claude", "node_modules"}
BACKUP_DIR = Path("./tian_shu_vault/.backup")

MODEL_NAME = "deepseek-chat"
TEMPERATURE = 0.1
MAX_TOKENS = 2048
TOP_K = 3
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

HEAD_IMG = r"C:\AI\秘书\avatar.jpg"

MINT_CSS = """
/* ===== 全局薄荷绿覆盖 ===== */
:root {
    --mint: #88D8B0;
    --mint-hover: #70CF9F;
    --mint-bg: #F5FFFA;
    --mint-border: #C8F0DE;
    --mint-label: #E6F7F0;
}
button.primary, .primary, .gr-button-primary {
    background: var(--mint) !important;
    border-color: var(--mint) !important;
}
button.primary:hover, .gr-button-primary:hover {
    background: var(--mint-hover) !important;
    border-color: var(--mint-hover) !important;
}
button.secondary, .gr-button-secondary {
    border-color: var(--mint-border) !important; color: #333 !important;
}
textarea:focus, input:focus, .gr-text-input:focus, .gr-textbox textarea:focus {
    border-color: var(--mint) !important;
    box-shadow: 0 0 0 2px var(--mint-border) !important;
}
.gr-dropdown, select:focus { border-color: var(--mint) !important; }
.tab-nav button.selected, .tabs button.selected, button.selected {
    border-bottom-color: var(--mint) !important; color: var(--mint) !important;
}
.tab-nav button:hover, .tabs button:hover { color: var(--mint-hover) !important; }
a, a:visited { color: #5CB88D !important; }
a:hover { color: var(--mint-hover) !important; }
.bubble-wrap .user, .message.user, .gr-chatbot .user {
    background: var(--mint-label) !important;
    border-left-color: var(--mint) !important;
}
.gr-label, .label-wrap, .prose label, legend { color: #333 !important; }
.gr-box, .gr-form, .gr-panel { border-color: var(--mint-border) !important; }
* {
    --primary-300: var(--mint) !important;
    --primary-400: var(--mint) !important;
    --primary-500: var(--mint) !important;
    --primary-600: var(--mint-hover) !important;
    --input-border-focus: var(--mint) !important;
    --ring-color: var(--mint-border) !important;
    --color-accent: var(--mint) !important;
    --block-border-color: var(--mint-border) !important;
}
body, .gradio-container, .main, .wrap { background: var(--mint-bg) !important; }
"""

VAULT_STRUCTURE = {
    "项目管理": ["项目A.md", "项目B.md"],
    "日常行政": ["工作日志.md"],
    "技术栈笔记": ["技术选型.md"],
    "联系人信息": ["通讯录.md"],
    "待办事项": ["任务清单.md"],
}


TEMPLATE_CONTENT = """# {folder}

## {section}

> 创建时间: {timestamp}

### 概述
-

### 详情
-

"""

# ==================== 2. 全局状态 ====================
_llm = None
_embeddings = None
_vector_store = None
_all_chunks: List[Document] = []
_vault_stats: dict = {}
_pending_write: Optional[dict] = None


# ==================== 3. 工具函数 ====================

def extract_timestamp(text: str, file_path: Path) -> str:
    """从文本或文件中提取时间戳，提取不到则返回'未知'"""
    patterns = [
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}/\d{2}/\d{2})",
        r"创建时间[：:]\s*(\S+)",
        r"更新时间[：:]\s*(\S+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    try:
        mtime = os.path.getmtime(str(file_path))
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except Exception:
        return "未知"


def safe_read_file(file_path: Path) -> Optional[str]:
    """安全读取文件，失败返回 None"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"  ⚠ 读取失败: {file_path} — {e}")
        return None


def safe_write_file(file_path: Path, content: str, mode: str = "w") -> bool:
    """安全写入文件，失败返回 False"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  ⚠ 写入失败: {file_path} — {e}")
        return False


def _kill_port(port: int = 7860):
    """清理占用指定端口的旧进程（解决双击启动时端口冲突）"""
    import subprocess
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                subprocess.run(
                    ["taskkill", "/f", "/pid", pid],
                    capture_output=True,
                )
                print(f"  [清理] 已关闭端口 {port} 的旧进程 PID={pid}")
                time.sleep(0.5)
    except Exception:
        pass


# ==================== 4. LLM 实例管理 ====================

def get_llm() -> ChatDeepSeek:
    """获取 DeepSeek LLM 单例"""
    global _llm
    if _llm is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "❌ 未找到 DEEPSEEK_API_KEY 环境变量！\n"
                "   请执行: set DEEPSEEK_API_KEY=你的密钥  (Windows CMD)\n"
                "   或创建 .env 文件写入: DEEPSEEK_API_KEY=你的密钥"
            )
        _llm = ChatDeepSeek(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            api_key=api_key,
        )
    return _llm


def get_embeddings() -> HuggingFaceEmbeddings:
    """获取嵌入模型单例（优先使用本地缓存，避免下载）"""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"local_files_only": True},
        )
    return _embeddings


# ==================== 5. 天书库管理 ====================

def init_vault():
    """首次运行自动创建天书库目录及示例笔记"""
    if VAULT_ROOT.exists():
        return
    print("📂 首次运行：正在创建天书库目录结构...")
    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    for folder, files in VAULT_STRUCTURE.items():
        folder_path = VAULT_ROOT / folder
        folder_path.mkdir(exist_ok=True)
        for fname in files:
            fpath = folder_path / fname
            section = Path(fname).stem
            content = TEMPLATE_CONTENT.format(
                folder=folder, section=section, timestamp=timestamp
            )
            safe_write_file(fpath, content)
            print(f"  ✅ 已创建: {folder}/{fname}")
    print("📂 天书库初始化完成！\n")


def scan_vault() -> List[Dict]:
    """遍历天书库，返回所有 .md 文件的元信息列表"""
    results = []
    if not VAULT_ROOT.exists():
        return results
    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = Path(root) / fname
            rel_path = fpath.relative_to(VAULT_ROOT)
            folder = str(rel_path.parent) if str(rel_path.parent) != "." else "根目录"
            results.append({
                "path": fpath,
                "folder": folder,
                "file_name": fname,
                "rel_path": str(rel_path),
            })
    return results


def list_vault_structure() -> str:
    """生成天书库目录树文本"""
    if not VAULT_ROOT.exists():
        return "⚠ 天书库尚未初始化"
    lines = ["# 📚 天书库结构\n"]
    file_list = scan_vault()
    by_folder: Dict[str, List[Dict]] = {}
    for f in file_list:
        by_folder.setdefault(f["folder"], []).append(f)
    for folder in sorted(by_folder):
        lines.append(f"## 📁 {folder}")
        for fi in by_folder[folder]:
            lines.append(f"  - 📝 {fi['file_name']}")
    return "\n".join(lines)


# ==================== 6. 文档切片与向量库构建 ====================

def build_chunks(file_list: List[Dict]) -> List[Document]:
    """遍历 .md 文件，用 MarkdownHeaderTextSplitter 按二级标题切片"""
    headers_to_split = [
        ("#", "h1"),
        ("##", "h2"),
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split,
        strip_headers=False,
    )
    all_chunks = []
    for file_info in file_list:
        content = safe_read_file(file_info["path"])
        if content is None:
            continue
        try:
            chunks = splitter.split_text(content)
        except Exception as e:
            print(f"  ⚠ 切片失败 [{file_info['file_name']}]: {e}")
            continue
        for chunk in chunks:
            chunk.metadata.update({
                "folder": file_info["folder"],
                "file_name": file_info["file_name"],
                "file_path": file_info["rel_path"],
                "section": chunk.metadata.get("h2", chunk.metadata.get("h1", "未分类")),
                "timestamp": extract_timestamp(chunk.page_content, file_info["path"]),
            })
            all_chunks.append(chunk)
    return all_chunks


def build_vector_store(chunks: List[Document]) -> FAISS:
    """用切片列表构建 FAISS 向量库"""
    embeddings = get_embeddings()
    if not chunks:
        return FAISS.from_texts(["天书库为空"], embeddings)
    return FAISS.from_documents(chunks, embeddings)


def rebuild_index(verbose: bool = True) -> Dict:
    """完全重建向量索引"""
    global _vector_store, _all_chunks, _vault_stats
    if verbose:
        print("\n🔄 正在重建知识库索引...")
    file_list = scan_vault()
    _all_chunks = build_chunks(file_list)
    _vector_store = build_vector_store(_all_chunks)
    folders = set(c.metadata.get("folder", "") for c in _all_chunks)
    files_set = set(c.metadata.get("file_path", "") for c in _all_chunks)
    _vault_stats = {
        "folder_count": len(folders),
        "file_count": len(files_set),
        "chunk_count": len(_all_chunks),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if verbose:
        print(f"  ✅ 索引重建完成: {len(folders)} 个分区, {len(files_set)} 篇笔记, {len(_all_chunks)} 个切片")
        print(f"  📅 更新时间: {_vault_stats['last_update']}\n")
    return _vault_stats


def incremental_add_to_index(file_path: Path, folder: str, file_name: str, rel_path: str):
    """增量添加单篇笔记切片到向量库"""
    global _vector_store, _all_chunks
    content = safe_read_file(file_path)
    if content is None:
        return
    headers_to_split = [("#", "h1"), ("##", "h2")]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split,
        strip_headers=False,
    )
    try:
        new_chunks = splitter.split_text(content)
    except Exception as e:
        print(f"  ⚠ 增量切片失败: {e}")
        return
    for chunk in new_chunks:
        chunk.metadata.update({
            "folder": folder,
            "file_name": file_name,
            "file_path": rel_path,
            "section": chunk.metadata.get("h2", chunk.metadata.get("h1", "未分类")),
            "timestamp": extract_timestamp(chunk.page_content, file_path),
        })
    if new_chunks:
        _vector_store.add_documents(new_chunks)
        _all_chunks.extend(new_chunks)
        print(f"  ✅ 增量添加 {len(new_chunks)} 个切片 -> 索引")


# ==================== 7. 提示词模板 ====================

QA_SYSTEM_PROMPT = """你是用户的私人工作秘书，名为「秘书」。你必须严格且仅基于下面提供的参考资料回答用户问题。

核心规则（违者重罚）：
1. 资料中有答案 → 基于资料准确回答，不得添油加醋
2. 资料中无答案 → 明确回答「天书暂无相关记录」，严禁编造任何信息
3. 若资料间存在信息冲突 → 先以标准格式标注冲突，再采用时间最新的记录作答
4. 回答末尾必须标注信息来源：【来源：{分区名称} / {笔记名称}】

冲突标注格式（检测到冲突时必须使用）：
---
⚠ **信息冲突检测**
{冲突摘要}
---

参考资料：
{context}"""

QA_USER_PROMPT = "用户问题：{question}"

CONFLICT_DETECT_PROMPT = """你是信息一致性检查员。请比对以下来自天书知识库的多个片段，判断是否存在信息冲突（矛盾或不一致之处）。

检索片段：
{chunks_text}

请以严格JSON格式输出（不要包含markdown代码块标记）：
{{
    "has_conflict": true或false,
    "conflict_summary": "若冲突，用一句话概括冲突内容；若无冲突则留空",
    "newest_entry": "若冲突，指出时间最新的那条信息的关键内容；若无冲突则留空"
}}"""

PLAN_SYSTEM_PROMPT = """你是用户的私人工作秘书。请根据用户的任务描述和天书中检索到的相关信息，输出一份结构化的4步工作计划。

天书参考资料：
{context}

计划输出格式：
### 📋 任务目标
（一句话概括任务要达成的目标）

### 🔢 执行步骤
1. **步骤一**：...
2. **步骤二**：...
3. **步骤三**：...
4. **步骤四**：...

### ⚠ 注意事项
- ...

### 📦 所需资料
- ...

### 🎯 预期产出
- ...

若天书中无相关信息，请在计划中注明「天书暂无相关记录，以下为通用建议」。"""

PLAN_USER_PROMPT = "用户任务：{task}"

CLAUDE_INSTRUCT_PROMPT = """你是一个指令生成专家。请根据下面的工作计划，生成一份可直接复制投喂给 Claude 的完整执行指令。

工作计划：
{plan}

生成的指令必须包含以下结构：

---
## 🎭 角色设定
你是一个 [角色描述]

## 📖 任务背景
[背景说明]

## 📋 执行规则
1. ...
2. ...
3. ...

## 📤 输出格式
[期望的输出格式]
---

确保指令清晰完整，Claude 拿到后能独立执行，不需要额外解释。"""

WRITE_FORMAT_PROMPT = """你是用户的私人工作秘书。请将用户提供的零散信息，整理为规范的 Obsidian Markdown 格式。

要求：
1. 保留原始信息的所有关键内容，不添油加醋
2. 自动按主题分点，使用合适的二级标题（##）
3. 在内容开头添加标准化时间戳：> 记录时间: {timestamp}
4. 格式工整，适合存入 Obsidian 知识库

用户原始输入：
{content}

请输出整理后的 Markdown 内容（只输出内容，不要额外解释）："""

WRITE_INTENT_PROMPT = """判断用户输入是否意图将信息写入天书知识库。

用户输入：{message}

请以严格JSON格式输出（不要包含markdown代码块标记）：
{{
    "is_write_intent": true或false,
    "core_content": "提取的核心信息内容（若不是写入意图则留空）",
    "suggested_folder": "建议存放的文件夹名称（若不是写入意图则留空）",
    "suggested_title": "建议的笔记标题（若不是写入意图则留空）"
}}"""

WRITE_MATCH_PROMPT = """根据用户想记录的内容，在天书库现有结构中匹配最合适的写入位置。

现有文件夹和笔记：
{vault_tree}

待写入内容摘要：{summary}

请以严格JSON格式输出（不要包含markdown代码块标记）：
{{
    "folder": "目标文件夹名",
    "file_name": "目标笔记文件名（含.md后缀）",
    "is_new_file": true或false
}}"""

# ==================== 8. 检索函数 ====================

def retrieve_chunks(query: str, top_k: int = TOP_K, folder_filter: str = None) -> List[Document]:
    global _vector_store
    if _vector_store is None:
        return []
    try:
        if folder_filter:
            docs = _vector_store.similarity_search(
                query, k=top_k * 3, filter={"folder": folder_filter}
            )
            return docs[:top_k]
        else:
            return _vector_store.similarity_search(query, k=top_k)
    except Exception as e:
        print(f"  ⚠ 检索失败: {e}")
        return []


def format_retrieved_context(docs: List[Document]) -> str:
    if not docs:
        return "（天书库中暂无相关资料）"
    parts = []
    for i, doc in enumerate(docs, 1):
        folder = doc.metadata.get("folder", "未知")
        fname = doc.metadata.get("file_name", "未知")
        section = doc.metadata.get("section", "")
        ts = doc.metadata.get("timestamp", "未知")
        header = f"[片段{i}] 📁{folder}/{fname} | 📅{ts}"
        if section:
            header += f" | 📍{section}"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)

# ==================== 9. 冲突检测 ====================

def detect_conflicts(docs: List[Document]) -> Optional[dict]:
    """检测多个检索片段之间是否存在信息冲突"""
    if len(docs) < 2:
        return None
    llm = get_llm()
    parts = []
    for i, d in enumerate(docs):
        folder = d.metadata.get("folder", "?")
        fname = d.metadata.get("file_name", "?")
        ts = d.metadata.get("timestamp", "?")
        parts.append(
            f"[片段{i+1}] 来源: {folder}/{fname} 时间: {ts}\n{d.page_content}"
        )
    chunks_text = "\n\n---\n\n".join(parts)
    try:
        response = llm.invoke(CONFLICT_DETECT_PROMPT.format(chunks_text=chunks_text))
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠ 冲突检测失败: {e}")
        return None


# ==================== 10. 业务链路 ====================

# --- 10a. 链路1：基础问答链（含冲突检测） ---

def run_qa_chain(question: str, folder_filter: str = None) -> str:
    """基础问答：检索 -> 冲突检测 -> 生成回答"""
    docs = retrieve_chunks(question, top_k=TOP_K, folder_filter=folder_filter)
    if not docs:
        return ("⚠ 天书库中暂无相关资料，无法回答。请先录入相关信息。\n\n"
                "💡 提示：你可以切换到「写入天书」模式来添加新知识。")

    conflict_info = detect_conflicts(docs)
    context = format_retrieved_context(docs)

    if conflict_info and conflict_info.get("has_conflict"):
        summary = conflict_info.get("conflict_summary", "")
        newest = conflict_info.get("newest_entry", "")
        context = (
            f"⚠ 重要提示：以下资料存在信息冲突 — {summary}\n"
            f"请采用时间最新的记录（{newest}）作为主要依据。\n\n"
            + context
        )

    main_doc = docs[0]
    source_folder = main_doc.metadata.get("folder", "未知分区")
    source_file = main_doc.metadata.get("file_name", "未知笔记")

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", QA_SYSTEM_PROMPT),
        ("human", QA_USER_PROMPT),
    ])

    try:
        chain = qa_prompt | get_llm() | StrOutputParser()
        answer = chain.invoke({
            "context": context,
            "question": question,
            "分区名称": source_folder,
            "笔记名称": source_file,
        })
    except Exception as e:
        return f"❌ API 调用失败: {e}\n请检查 DeepSeek API 密钥和网络连接。"

    if "【来源：" not in answer:
        answer += f"\n\n【来源：{source_folder} / {source_file}】"

    if conflict_info and conflict_info.get("has_conflict"):
        summary = conflict_info.get("conflict_summary", "检测到信息不一致")
        conflict_header = (
            f"\n---\n⚠ **信息冲突检测**\n{summary}\n已采用最新记录作答。\n---\n"
        )
        answer = conflict_header + answer

    return answer


# --- 10b. 链路2：工作计划生成链 ---

def run_plan_chain(task: str) -> str:
    """生成结构化工作计划"""
    plan_prompt = ChatPromptTemplate.from_messages([
        ("system", PLAN_SYSTEM_PROMPT),
        ("human", PLAN_USER_PROMPT),
    ])
    context = format_retrieved_context(retrieve_chunks(task, top_k=TOP_K))
    try:
        chain = plan_prompt | get_llm() | StrOutputParser()
        return chain.invoke({"task": task, "context": context})
    except Exception as e:
        return f"❌ 计划生成失败: {e}"


# --- 10c. 链路3：Claude 指令生成链 ---

def run_claude_chain(plan_or_task: str) -> str:
    """基于任务或计划，生成 Claude 可执行指令"""
    try:
        if len(plan_or_task) < 100 and not plan_or_task.startswith("###"):
            plan = run_plan_chain(plan_or_task)
        else:
            plan = plan_or_task
        claude_prompt = ChatPromptTemplate.from_messages([
            ("human", CLAUDE_INSTRUCT_PROMPT),
        ])
        chain = claude_prompt | get_llm() | StrOutputParser()
        return chain.invoke({"plan": plan})
    except Exception as e:
        return f"❌ 指令生成失败: {e}"


# --- 10d. 链路4：天书写入链 ---

def run_write_format_chain(content: str) -> str:
    """将用户零散输入整理为规范的 Markdown"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt_text = WRITE_FORMAT_PROMPT.format(content=content, timestamp=timestamp)
    try:
        llm = get_llm()
        response = llm.invoke(prompt_text)
        return response.content.strip()
    except Exception:
        return f"> 记录时间: {timestamp}\n\n## 记录\n\n{content}"


def run_write_match_chain(formatted_content: str) -> Dict:
    """匹配写入的目标文件夹和笔记文件"""
    vault_tree = list_vault_structure()
    summary = formatted_content[:500]
    prompt_text = WRITE_MATCH_PROMPT.format(vault_tree=vault_tree, summary=summary)
    try:
        llm = get_llm()
        response = llm.invoke(prompt_text)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception:
        return {"folder": "日常行政", "file_name": "工作日志.md", "is_new_file": False}


def backup_file(file_path: Path) -> Optional[Path]:
    """备份原文件到临时目录"""
    if not file_path.exists():
        return None
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{file_path.stem}_{ts}.bak.md"
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"  ⚠ 备份失败: {e}")
        return None


def execute_write_to_vault(formatted_content: str, folder: str, file_name: str) -> str:
    """执行实际的天书文件写入操作（含路径遍历防护）"""
    # 路径遍历防护：禁止 folder / file_name 包含 .. 或路径分隔符
    for val, name in [(folder, "folder"), (file_name, "file_name")]:
        if ".." in val or "/" in val or "\\" in val:
            return f"❌ 写入失败：{name} 包含非法字符"
    if not file_name.endswith(".md"):
        return "❌ 写入失败：仅支持 .md 文件"

    folder_path = (VAULT_ROOT / folder).resolve()
    vault_real = VAULT_ROOT.resolve()
    if not str(folder_path).startswith(str(vault_real) + os.sep):
        return "❌ 写入失败：目标路径超出天书库范围"

    file_path = (folder_path / file_name).resolve()
    if not str(file_path).startswith(str(vault_real) + os.sep):
        return "❌ 写入失败：目标文件路径超出天书库范围"
    backup_path = backup_file(file_path)
    folder_path.mkdir(parents=True, exist_ok=True)
    append_content = f"\n\n---\n\n{formatted_content}\n"
    success = safe_write_file(file_path, append_content, mode="a")
    if not success:
        return f"❌ 写入失败：无法写入文件 {folder}/{file_name}"
    rel_path = str(Path(folder) / file_name)
    try:
        incremental_add_to_index(file_path, folder, file_name, rel_path)
    except Exception as e:
        print(f"  ⚠ 索引更新失败: {e}，可稍后手动刷新")
    global _vault_stats
    _vault_stats["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = f"✅ **已写入天书**\n📂 路径: `{folder}/{file_name}`\n📝 内容已追加到笔记末尾"
    if backup_path:
        result += f"\n💾 原文件已备份至: `{backup_path.name}`"
    result += "\n🔍 向量索引已更新（新增切片）"
    return result


def run_write_preview_chain(user_input: str) -> Tuple[str, Optional[Dict]]:
    """天书写入链路 - 预览阶段：规整内容 + 匹配路径"""
    if not user_input.strip():
        return "⚠ 请输入要记录的内容。", None
    formatted = run_write_format_chain(user_input)
    match = run_write_match_chain(formatted)
    folder = match.get("folder", "日常行政")
    file_name = match.get("file_name", "工作日志.md")
    is_new = match.get("is_new_file", False)
    new_tag = "🆕 新建" if is_new else "📝 追加"
    preview = (
        f"**{new_tag} 天书写入预览**\n\n"
        f"📂 目标路径: `{folder}/{file_name}`\n\n"
        f"---\n{formatted}\n---\n\n"
        "⚠ 请确认以上内容无误，点击「✅ 确认写入」按钮执行写入。"
    )
    pending = {
        "formatted_content": formatted,
        "folder": folder,
        "file_name": file_name,
    }
    return preview, pending


# ==================== 11. 意图识别 ====================

def detect_task_mode(message: str, selected_mode: str) -> str:
    """综合判断当前对话模式"""
    if selected_mode != "自动识别":
        return selected_mode
    plan_kw = ["做计划", "工作计划", "制定计划", "规划", "安排一下", "分步骤"]
    claude_kw = ["生成指令", "给Claude", "Claude指令", "投喂", "给claude"]
    write_kw = ["记下来", "保存", "写入天书", "帮我记", "添加记录", "存一下", "写到"]
    if any(kw in message for kw in claude_kw):
        return "生成Claude指令"
    if any(kw in message for kw in plan_kw):
        return "生成工作计划"
    if any(kw in message for kw in write_kw):
        return "写入天书"
    return "普通问答"


# ==================== 12. 聊天入口函数 ====================

def chat(message: str, history: List[Tuple[str, str]], mode: str, pending_state: Optional[Dict]):
    """核心聊天函数：根据模式和意图分发到对应链路"""
    global _pending_write
    if not message.strip():
        return history, pending_state

    actual_mode = detect_task_mode(message, mode)

    # 写入天书模式：生成预览，等待用户确认
    if actual_mode == "写入天书":
        preview, pending = run_write_preview_chain(message)
        history.append((message, preview))
        _pending_write = pending
        return history, pending

    # 其他模式：直接执行
    try:
        if actual_mode == "生成工作计划":
            answer = run_plan_chain(message)
        elif actual_mode == "生成Claude指令":
            answer = run_claude_chain(message)
        else:
            answer = run_qa_chain(message)
    except RuntimeError as e:
        answer = f"❌ 初始化失败: {e}"
    except Exception as e:
        answer = f"❌ 处理请求时出错: {e}"

    display_msg = f"[{actual_mode}]\n\n{answer}"
    history.append((message, display_msg))
    return history, None


def confirm_write(history: List[Tuple[str, str]], pending_state: Optional[Dict]):
    """确认写入按钮回调：执行实际的文件写入"""
    global _pending_write
    pending = pending_state or _pending_write
    if not pending:
        history.append(("系统", "⚠ 没有待确认的写入内容。请先在「写入天书」模式下输入内容。"))
        return history, None
    try:
        result = execute_write_to_vault(
            pending["formatted_content"],
            pending["folder"],
            pending["file_name"],
        )
    except Exception as e:
        result = f"❌ 写入失败: {e}"
    history.append(("✅ 确认写入", result))
    _pending_write = None
    return history, None


# ==================== 13. 天书概览数据 ====================

def get_overview_text():
    """生成天书概览页的展示文本"""
    tree = list_vault_structure()
    stats = _vault_stats
    if not stats:
        stats = {
            "folder_count": 0, "file_count": 0,
            "chunk_count": 0, "last_update": "尚未构建"
        }
    overview = (
        f"# 📊 向量库状态\n\n"
        f"| 指标 | 数值 |\n|------|------|\n"
        f"| 📁 分区数量 | {stats.get('folder_count', 0)} |\n"
        f"| 📝 笔记总数 | {stats.get('file_count', 0)} |\n"
        f"| 🧩 切片总数 | {stats.get('chunk_count', 0)} |\n"
        f"| 🕐 最后更新 | {stats.get('last_update', '未知')} |\n\n---\n\n{tree}"
    )
    return overview


def manual_refresh():
    """手动刷新知识库索引"""
    stats = rebuild_index(verbose=True)
    overview = get_overview_text()
    msg = f"✅ 知识库已刷新！共加载 {stats['chunk_count']} 个切片。"
    return overview, msg


# ==================== 14. Gradio 界面 ====================

def create_ui(avatar_data_uri: str = ""):
    """构建 Gradio Tab 界面（薄荷绿配色 + 咕嘎头像）"""
    with gr.Blocks(
        title="秘书 · Obsidian 知识库 Agent",
    ) as demo:
        gr.HTML(
            f'<div style="display:flex;align-items:center;gap:16px;padding:8px 0;">'
            f'<img src="{avatar_data_uri}" height="48" '
            f'style="height:48px;width:auto;border-radius:8px;vertical-align:middle;" alt="秘书头像">'
            f'<div>'
            f'<h1 style="margin:0;color:#333;font-size:1.6em;">秘书 · Obsidian 知识库 Agent</h1>'
            f'<p style="margin:4px 0 0;color:#666;">'
            f'DeepSeek API + LangChain + FAISS | 四条核心链路 | 冲突检测 | 薄荷绿配色'
            f'</p></div></div>'
        )
        pending_state = gr.State(None)

        with gr.Tabs():
            # ── 标签页1：秘书对话 ──
            with gr.TabItem("秘书对话"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(label="对话记录", height=500)
                        with gr.Row():
                            msg = gr.Textbox(
                                label="输入消息",
                                placeholder="在此输入问题或指令...",
                                scale=4,
                                show_label=False,
                            )
                            mode_dropdown = gr.Dropdown(
                                choices=[
                                    "自动识别", "普通问答", "生成工作计划",
                                    "生成Claude指令", "写入天书"
                                ],
                                value="自动识别",
                                label="模式",
                                scale=1,
                            )
                        with gr.Row():
                            confirm_btn = gr.Button(
                                "确认写入", variant="primary", size="sm"
                            )
                            clear_btn = gr.Button(
                                "清空对话", variant="secondary", size="sm"
                            )

                # 事件绑定
                msg.submit(
                    chat,
                    [msg, chatbot, mode_dropdown, pending_state],
                    [chatbot, pending_state],
                ).then(lambda: "", None, msg)

                confirm_btn.click(
                    confirm_write,
                    [chatbot, pending_state],
                    [chatbot, pending_state],
                )

                clear_btn.click(
                    lambda: ([], None), None, [chatbot, pending_state]
                )

            # ── 标签页2：天书概览 ──
            with gr.TabItem("天书概览"):
                overview_md = gr.Markdown(get_overview_text())
                with gr.Row():
                    refresh_btn = gr.Button(
                        "🔄 手动刷新知识库", variant="primary"
                    )
                    status_text = gr.Textbox(
                        label="操作状态", interactive=False, scale=2
                    )
                refresh_btn.click(
                    manual_refresh, None, [overview_md, status_text]
                )

    return demo


# ==================== 15. 启动入口 ====================

def main():
    """主启动流程：检查环境 -> 初始化天书库 -> 加载模型 -> 构建索引 -> 启动界面"""
    print("=" * 60)
    print("🤖 秘书 · Obsidian 知识库 Agent 系统")
    print("=" * 60)

    # 1. 验证 API Key
    try:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
            print(f"🔑 DeepSeek API Key: {masked}")
        else:
            print("⚠ 未检测到 DEEPSEEK_API_KEY 环境变量")
            print("  请设置环境变量或创建 .env 文件:\n    DEEPSEEK_API_KEY=你的密钥")
    except Exception:
        pass

    # 1.5. 校验头像文件
    if os.path.exists(HEAD_IMG):
        print(f"  ✅ 头像文件读取成功: {HEAD_IMG}")
    else:
        print(f"  ❌ 头像文件缺失，请检查: {HEAD_IMG}")

    # 2. 检查或创建天书库
    if not VAULT_ROOT.exists():
        init_vault()
    else:
        print(f"📂 天书库已存在: {VAULT_ROOT.absolute()}")

    # 3. 加载嵌入模型
    print("🧠 正在加载向量嵌入模型...")
    try:
        emb = get_embeddings()
        print(f"  ✅ 嵌入模型已就绪: {EMBEDDING_MODEL}")
    except Exception as e:
        print(f"  ⚠ 嵌入模型加载失败: {e}")
        print("  请确认已安装 sentence-transformers")
        return

    # 4. 构建向量索引
    try:
        stats = rebuild_index(verbose=True)
    except Exception as e:
        print(f"❌ 向量索引构建失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 将头像转为 base64 内嵌（绕过 Gradio 文件路由问题）
    import base64 as _b64
    avatar_uri = ""
    try:
        with open(HEAD_IMG, "rb") as _f:
            avatar_uri = f"data:image/jpeg;base64,{_b64.b64encode(_f.read()).decode()}"
        print(f"  ✅ 头像已内嵌 ({len(avatar_uri)} chars)")
    except Exception as _e:
        print(f"  ⚠ 头像加载失败: {_e}，将显示文字占位")

    # 6. 清理旧进程 + 启动 Gradio 界面
    print("🌐 正在启动 Gradio 界面...")
    _kill_port(7860)
    demo = create_ui(avatar_uri)
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
        show_error=True,
        allowed_paths=[r"C:\AI\秘书"],
        favicon_path=HEAD_IMG,
        css=MINT_CSS,
        theme=gr.themes.Soft(
            primary_hue=gr.themes.colors.emerald,
            secondary_hue=gr.themes.colors.emerald,
            neutral_hue="slate",
        ),
    )


if __name__ == "__main__":
    main()
