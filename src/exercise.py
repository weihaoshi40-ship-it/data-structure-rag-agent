from __future__ import annotations

from .config import AppConfig
from .rag import (
    ToolResponse,
    build_citation_block,
    call_llm,
    format_chat_context,
    format_context,
    is_llm_error,
    search_knowledge_base,
)


def build_local_exercises(question: str, context_text: str, llm_error: str) -> str:
    return (
        "模型接口暂时不可用，下面先基于本地知识库生成一组兜底练习题。\n\n"
        f"接口状态：{llm_error}\n\n"
        "一、选择题\n"
        "1. 栈的主要特点是以下哪一项？\n"
        "A. 先进先出\n"
        "B. 后进先出\n"
        "C. 随机访问\n"
        "D. 按关键字查找\n"
        "答案：B\n\n"
        "二、填空题\n"
        "2. 顺序表按下标访问元素的时间复杂度通常为 ____。\n"
        "答案：O(1)\n\n"
        "三、简答题\n"
        "3. 简述顺序表和链表在存储结构、查找、插入删除方面的主要区别。\n"
        "参考要点：顺序表地址连续，支持随机访问，但插入删除通常需要移动元素；链表通过指针连接结点，"
        "不要求连续空间，插入删除较灵活，但按序号查找需要遍历。\n\n"
        f"生成依据问题：{question}\n\n"
        f"参考片段摘要：{context_text[:500]}"
    )


def exercise_gen(question: str, chat_context: list[dict[str, str]], config: AppConfig) -> ToolResponse:
    log = ["工具选择：exercise_gen", "开始检索知识库以生成练习题"]
    results = search_knowledge_base(question, config)
    relevant = [item for item in results if item.score >= config.min_similarity]
    if not relevant and results:
        relevant = results[: min(3, len(results))]
        log.append("练习题请求较泛化：使用 Top 检索片段作为出题依据")
    log.append(f"检索完成：命中 {len(results)} 个片段，可靠片段 {len(relevant)} 个")

    if not relevant:
        return ToolResponse(
            answer="当前知识库中未找到足够可靠的内容来生成练习题。请上传数据结构资料并重建知识库后再试。",
            tool_name="exercise_gen",
            results=results,
            log=log,
        )

    context = format_context(relevant)
    messages = [
        {
            "role": "system",
            "content": (
                "你是计算机考研《数据结构》练习题生成工具。"
                "请严格基于给定知识库片段生成题目，不要编造超出资料范围的知识点。"
                "输出应包含选择题、填空题和简答题，并给出答案或参考要点。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"当前会话上下文：\n{format_chat_context(chat_context)}\n\n"
                f"知识库片段：\n{context}\n\n"
                f"用户需求：{question}\n\n"
                "请生成 5 道适合考研复习的练习题：2 道选择题、2 道填空题、1 道简答题。"
                "每道题后给出答案；简答题给出评分要点。"
            ),
        },
    ]
    answer = call_llm(config, messages)
    if is_llm_error(answer):
        answer = build_local_exercises(question, context, answer)
    else:
        answer += build_citation_block(relevant)
    return ToolResponse(answer=answer, tool_name="exercise_gen", results=relevant, log=log)
