from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from openai import OpenAI, OpenAIError
from sklearn.preprocessing import normalize

from .config import AppConfig
from .ingest import DocumentChunk, load_vector_store, vector_store_exists


@dataclass
class SearchResult:
    source: str
    location: str
    text: str
    score: float


@dataclass
class ToolResponse:
    answer: str
    tool_name: str
    results: list[SearchResult]
    log: list[str]
    code_language: str | None = None


def search_knowledge_base(question: str, config: AppConfig) -> list[SearchResult]:
    if not vector_store_exists():
        return []

    index, vectorizer, chunks = load_vector_store()
    query_matrix = vectorizer.transform([question])
    query_vector = normalize(query_matrix, norm="l2", axis=1).astype(np.float32).toarray()
    top_k = min(config.top_k, max(1, len(chunks)))
    scores, ids = index.search(query_vector, top_k)

    results: list[SearchResult] = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        chunk = chunks[int(idx)]
        results.append(
            SearchResult(
                source=chunk.source,
                location=chunk.location,
                text=chunk.text,
                score=float(score),
            )
        )
    return results


def format_context(results: list[SearchResult]) -> str:
    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        lines.append(
            f"[{index}] 来源：{result.source}；位置：{result.location}；相似度：{result.score:.3f}\n{result.text}"
        )
    return "\n\n".join(lines)


def format_chat_context(chat_context: list[dict[str, str]], limit: int = 6) -> str:
    recent = chat_context[-limit:]
    return "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in recent)


def build_citation_block(results: list[SearchResult]) -> str:
    if not results:
        return ""
    lines = ["\n\n引用依据："]
    for index, result in enumerate(results, start=1):
        snippet = result.text.replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:120] + "..."
        lines.append(f"[{index}] {result.source}，{result.location}，相似度 {result.score:.3f}：{snippet}")
    return "\n".join(lines)


def is_llm_error(answer: str) -> bool:
    return answer.startswith("模型接口调用失败") or answer.startswith("未配置 OPENAI_API_KEY")


def build_local_rag_answer(question: str, results: list[SearchResult], llm_error: str) -> str:
    lead = (
        "模型接口暂时不可用，下面先基于本地知识库检索结果给出兜底回答。\n\n"
        f"接口状态：{llm_error}\n\n"
    )
    if not results:
        return lead + "当前知识库中没有可用片段。"

    best = results[0]
    answer = (
        lead +
        f"针对问题“{question}”，当前最相关依据来自 `{best.source}` 的 `{best.location}`。\n\n"
        f"知识库原文要点：{best.text.strip()}\n\n"
        "说明：这是基于检索片段的本地兜底回答；配置可用 API Key 后，系统会生成更自然、结构更完整的智能回答。"
    )
    return answer + build_citation_block(results)


def call_llm(config: AppConfig, messages: list[dict[str, str]]) -> str:
    if not config.llm_ready:
        return "未配置 OPENAI_API_KEY。请复制 .env.example 为 .env，并填写 OpenAI 兼容 API 配置后重试。"
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
        )
        return response.choices[0].message.content or ""
    except OpenAIError as exc:
        return f"模型接口调用失败：{exc}。请检查 API Key、额度、BASE_URL 和模型名称配置。"


def rag_qa(question: str, chat_context: list[dict[str, str]], config: AppConfig) -> ToolResponse:
    log = ["工具选择：rag_qa", "开始检索本地知识库"]
    results = search_knowledge_base(question, config)
    relevant = [item for item in results if item.score >= config.min_similarity]
    log.append(f"检索完成：命中 {len(results)} 个片段，可靠片段 {len(relevant)} 个")

    if not relevant:
        return ToolResponse(
            answer="当前知识库中未找到与问题足够相关的可靠依据，因此不能给出带引用的回答。请补充相关资料后重建知识库，或换一种更贴近资料内容的问法。",
            tool_name="rag_qa",
            results=results,
            log=log,
        )

    messages = [
        {
            "role": "system",
            "content": (
                "你是面向计算机考研《数据结构》的智能答疑 Agent。"
                "只能基于给定知识库片段回答，必须给出清晰、准确、适合考研复习的解释。"
                "如果片段不足以支持结论，要明确说明不足，不得编造引用。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"当前会话上下文：\n{format_chat_context(chat_context)}\n\n"
                f"知识库片段：\n{format_context(relevant)}\n\n"
                f"用户问题：{question}\n\n"
                "请用中文回答，并在正文中用 [1]、[2] 标注依据。"
            ),
        },
    ]
    answer = call_llm(config, messages)
    if is_llm_error(answer):
        answer = build_local_rag_answer(question, relevant, answer)
    elif config.llm_ready:
        answer += build_citation_block(relevant)
    return ToolResponse(answer=answer, tool_name="rag_qa", results=relevant, log=log)
