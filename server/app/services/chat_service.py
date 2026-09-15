"""
聊天业务服务
实现四条核心链路：问答、工作计划、Claude指令、天书写入
支持 SSE 流式输出
"""
import json
import time
from typing import AsyncGenerator, Dict, Optional, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.core.llm import get_llm
from app.rag.retriever import (
    retrieve_chunks,
    format_retrieved_context,
    detect_conflicts,
    get_sources_from_docs,
)
from app.rag.prompts import (
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT,
    CLAUDE_INSTRUCT_PROMPT,
)


def sse_event(event: str, data: Dict) -> str:
    """
    构建 SSE 事件格式

    Args:
        event: 事件类型（status/sources/conflict/token/done/error）
        data: 事件数据

    Returns:
        SSE 格式字符串
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_qa_stream(question: str, folder_filter: str = None, db=None) -> AsyncGenerator[str, None]:
    """
    知识库问答链路（SSE 流式输出）
    流程：检索（Hybrid: BM25+向量） -> 冲突检测 -> 流式生成回答

    Args:
        question: 用户问题
        folder_filter: 文件夹过滤
        db: 数据库会话（用于 BM25 索引构建）

    Yields:
        SSE 事件字符串
    """
    start_time = time.time()

    # 1. Hybrid 检索（BM25 + 向量，RRF 融合；向量不可用时自动降级 BM25）
    yield sse_event("status", {"stage": "retrieving", "message": "正在检索知识库..."})
    docs, retrieve_mode = await retrieve_chunks(
        question, top_k=settings.TOP_K, folder_filter=folder_filter, db=db
    )

    if not docs:
        yield sse_event("status", {"stage": "no_result", "message": "天书库中暂无相关资料"})
        yield sse_event("done", {
            "answer": "⚠ 天书库中暂无相关资料，无法回答。请先录入相关信息。",
            "sources": [],
            "tokens_used": 0,
            "latency_ms": int((time.time() - start_time) * 1000),
        })
        return

    # 2. 发送检索来源
    sources = get_sources_from_docs(docs)
    yield sse_event("sources", {"count": len(docs), "sources": sources})

    # 3. 冲突检测
    yield sse_event("status", {"stage": "conflict_check", "message": "正在检测信息一致性..."})
    conflict_info = detect_conflicts(docs)
    context = format_retrieved_context(docs)

    if conflict_info and conflict_info.get("has_conflict"):
        summary = conflict_info.get("conflict_summary", "")
        newest = conflict_info.get("newest_entry", "")
        yield sse_event("conflict", {
            "has_conflict": True,
            "summary": summary,
            "newest": newest,
        })
        context = (
            f"⚠ 重要提示：以下资料存在信息冲突 — {summary}\n"
            f"请采用时间最新的记录（{newest}）作为主要依据。\n\n"
            + context
        )

    # 4. 流式生成回答
    yield sse_event("status", {"stage": "generating", "message": "正在生成回答..."})
    main_doc = docs[0]
    source_folder = main_doc.metadata.get("folder", "未知分区")
    source_file = main_doc.metadata.get("file_name", "未知笔记")

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", QA_SYSTEM_PROMPT),
        ("human", QA_USER_PROMPT),
    ])

    llm = get_llm()
    chain = qa_prompt | llm | StrOutputParser()

    full_answer = ""
    try:
        async for chunk in chain.astream({
            "context": context,
            "question": question,
            "分区名称": source_folder,
            "笔记名称": source_file,
        }):
            full_answer += chunk
            yield sse_event("token", {"content": chunk})
    except Exception as e:
        yield sse_event("error", {"code": "LLM_ERROR", "message": str(e)})
        return

    # 确保回答末尾有来源标注
    if "【来源：" not in full_answer:
        source_note = f"\n\n【来源：{source_folder} / {source_file}】"
        full_answer += source_note
        yield sse_event("token", {"content": source_note})

    # 5. 完成事件
    yield sse_event("done", {
        "answer": full_answer,
        "sources": sources,
        "tokens_used": 0,  # DeepSeek API 暂未返回 token 统计
        "latency_ms": int((time.time() - start_time) * 1000),
        "has_conflict": bool(conflict_info and conflict_info.get("has_conflict")),
        "conflict_summary": conflict_info.get("conflict_summary") if conflict_info else None,
    })


async def run_plan_stream(task: str, db=None) -> AsyncGenerator[str, None]:
    """
    工作计划生成链路（SSE 流式输出）

    Args:
        task: 任务描述
        db: 数据库会话（用于 BM25 索引构建）

    Yields:
        SSE 事件字符串
    """
    start_time = time.time()

    yield sse_event("status", {"stage": "retrieving", "message": "正在检索相关资料..."})
    docs, retrieve_mode = await retrieve_chunks(task, top_k=settings.TOP_K, db=db)
    context = format_retrieved_context(docs)
    sources = get_sources_from_docs(docs)

    if sources:
        yield sse_event("sources", {"count": len(docs), "sources": sources})

    yield sse_event("status", {"stage": "generating", "message": "正在生成工作计划..."})

    plan_prompt = ChatPromptTemplate.from_messages([
        ("system", PLAN_SYSTEM_PROMPT),
        ("human", PLAN_USER_PROMPT),
    ])

    llm = get_llm()
    chain = plan_prompt | llm | StrOutputParser()

    full_plan = ""
    try:
        async for chunk in chain.astream({"task": task, "context": context}):
            full_plan += chunk
            yield sse_event("token", {"content": chunk})
    except Exception as e:
        yield sse_event("error", {"code": "LLM_ERROR", "message": str(e)})
        return

    yield sse_event("done", {
        "answer": full_plan,
        "sources": sources,
        "latency_ms": int((time.time() - start_time) * 1000),
    })


async def run_claude_stream(plan_or_task: str, db=None) -> AsyncGenerator[str, None]:
    """
    Claude 指令生成链路（SSE 流式输出）

    Args:
        plan_or_task: 工作计划或任务描述
        db: 数据库会话（用于 BM25 索引构建）

    Yields:
        SSE 事件字符串
    """
    start_time = time.time()

    # 如果输入较短，先生成工作计划
    if len(plan_or_task) < 100 and not plan_or_task.startswith("###"):
        yield sse_event("status", {"stage": "planning", "message": "正在生成工作计划..."})
        # 同步获取计划（非流式，因为需要完整计划才能生成指令）
        docs, retrieve_mode = await retrieve_chunks(plan_or_task, top_k=settings.TOP_K, db=db)
        context = format_retrieved_context(docs)
        plan_prompt = ChatPromptTemplate.from_messages([
            ("system", PLAN_SYSTEM_PROMPT),
            ("human", PLAN_USER_PROMPT),
        ])
        llm = get_llm()
        plan = (plan_prompt | llm | StrOutputParser()).invoke({
            "task": plan_or_task, "context": context
        })
    else:
        plan = plan_or_task

    yield sse_event("status", {"stage": "generating", "message": "正在生成 Claude 指令..."})

    claude_prompt = ChatPromptTemplate.from_messages([
        ("human", CLAUDE_INSTRUCT_PROMPT),
    ])

    llm = get_llm()
    chain = claude_prompt | llm | StrOutputParser()

    full_instruct = ""
    try:
        async for chunk in chain.astream({"plan": plan}):
            full_instruct += chunk
            yield sse_event("token", {"content": chunk})
    except Exception as e:
        yield sse_event("error", {"code": "LLM_ERROR", "message": str(e)})
        return

    yield sse_event("done", {
        "answer": full_instruct,
        "sources": [],
        "latency_ms": int((time.time() - start_time) * 1000),
    })


def detect_task_mode(message: str, selected_mode: str = "auto") -> str:
    """
    综合判断当前对话模式

    Args:
        message: 用户消息
        selected_mode: 用户选择的模式

    Returns:
        实际模式：qa/plan/write/claude
    """
    if selected_mode != "auto":
        return selected_mode

    plan_kw = ["做计划", "工作计划", "制定计划", "规划", "安排一下", "分步骤"]
    claude_kw = ["生成指令", "给Claude", "Claude指令", "投喂", "给claude"]
    write_kw = ["记下来", "保存", "写入天书", "帮我记", "添加记录", "存一下", "写到"]

    if any(kw in message for kw in claude_kw):
        return "claude"
    if any(kw in message for kw in plan_kw):
        return "plan"
    if any(kw in message for kw in write_kw):
        return "write"
    return "qa"
