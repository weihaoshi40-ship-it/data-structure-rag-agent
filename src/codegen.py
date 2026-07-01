from __future__ import annotations

import re

from .config import AppConfig
from .rag import ToolResponse, call_llm, format_chat_context


def detect_language(question: str) -> str:
    lower = question.lower()
    if "c++" in lower or "cpp" in lower:
        return "cpp"
    if "python" in lower:
        return "python"
    if "java" in lower:
        return "java"
    if "c语言" in question or re.search(r"\bc\b", lower):
        return "c"
    return "cpp"


def code_gen(question: str, chat_context: list[dict[str, str]], config: AppConfig) -> ToolResponse:
    language = detect_language(question)
    log = ["工具选择：code_gen", f"识别目标语言：{language}", "准备生成数据结构代码"]
    messages = [
        {
            "role": "system",
            "content": (
                "你是计算机考研《数据结构》代码辅导 Agent。"
                "只回答数据结构、算法模板、考研常见代码题相关内容。"
                "输出必须包含：核心思路、完整代码、时间复杂度、空间复杂度、易错点。"
                "代码应简洁、可读，优先适合考试手写和理解。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"当前会话上下文：\n{format_chat_context(chat_context)}\n\n"
                f"用户问题：{question}\n\n"
                f"请使用 {language} 生成代码。"
            ),
        },
    ]
    answer = call_llm(config, messages)
    return ToolResponse(answer=answer, tool_name="code_gen", results=[], log=log, code_language=language)
