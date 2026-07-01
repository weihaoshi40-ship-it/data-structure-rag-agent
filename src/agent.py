from __future__ import annotations

import re

from .codegen import code_gen
from .config import AppConfig
from .exercise import exercise_gen
from .rag import ToolResponse, rag_qa


CODE_KEYWORDS = (
    "代码", "实现", "编程", "程序", "函数", "c++", "cpp", "python", "java",
    "递归实现", "非递归实现", "模板", "运行", "测试",
)

EXERCISE_KEYWORDS = (
    "练习题", "习题", "选择题", "填空题", "简答题", "出题", "生成题", "测试题", "题目生成",
    "quiz", "exercise",
)


def should_use_code_gen(question: str) -> bool:
    lower = question.lower()
    if any(keyword in lower for keyword in ("c++", "cpp", "python", "java")):
        return True
    if "复杂度" in question and any(keyword in question for keyword in ("代码", "实现", "程序", "函数")):
        return True
    return any(keyword in question for keyword in CODE_KEYWORDS)


def should_use_exercise_gen(question: str) -> bool:
    lower = question.lower()
    return any(keyword in question for keyword in EXERCISE_KEYWORDS) or any(
        keyword in lower for keyword in ("quiz", "exercise")
    )


def normalize_followup(question: str, chat_context: list[dict[str, str]]) -> str:
    if not chat_context:
        return question
    if not re.search(r"(它|该算法|这个|上述|前面|上一问)", question):
        return question
    recent_user = ""
    for item in reversed(chat_context):
        if item.get("role") == "user":
            recent_user = item.get("content", "")
            break
    if not recent_user:
        return question
    return f"上一轮问题是“{recent_user}”。当前追问：{question}"


def run_agent(question: str, chat_context: list[dict[str, str]], config: AppConfig) -> ToolResponse:
    normalized_question = normalize_followup(question.strip(), chat_context)
    if should_use_exercise_gen(normalized_question):
        response = exercise_gen(normalized_question, chat_context, config)
    elif should_use_code_gen(normalized_question):
        response = code_gen(normalized_question, chat_context, config)
    else:
        response = rag_qa(normalized_question, chat_context, config)
    if normalized_question != question:
        response.log.insert(0, "多轮上下文：已结合上一轮问题改写当前追问")
    return response
