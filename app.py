from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from src.agent import run_agent
from src.config import MATERIALS_DIR, load_config, ensure_project_dirs
from src.ingest import build_vector_store, list_material_files, save_uploaded_files, vector_store_exists


st.set_page_config(
    page_title="数据结构 RAG 智能问答 Agent",
    page_icon="DS",
    layout="wide",
)


CUSTOM_CSS = """
<style>
:root {
  --ink: #17202a;
  --muted: #586575;
  --line: #d9e1e8;
  --panel: #f7f9fb;
  --accent: #0f766e;
  --accent-2: #b45309;
}
.stApp {
  background: linear-gradient(180deg, #fbfcfd 0%, #eef3f6 100%);
  color: var(--ink);
}
.main .block-container {
  max-width: 1200px;
  padding-top: 28px;
}
.app-title {
  border-bottom: 1px solid var(--line);
  padding-bottom: 14px;
  margin-bottom: 18px;
}
.app-title h1 {
  font-size: 30px;
  letter-spacing: 0;
  margin: 0 0 8px 0;
}
.app-title p {
  color: var(--muted);
  margin: 0;
  font-size: 15px;
}
.status-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #e8f5f3;
  color: var(--accent);
  border: 1px solid #b9ded8;
  font-size: 13px;
  margin-right: 6px;
}
.result-box {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.result-meta {
  color: var(--accent-2);
  font-size: 13px;
  margin-bottom: 6px;
  font-weight: 700;
}
.result-text {
  color: var(--ink);
  font-size: 14px;
  line-height: 1.65;
}
</style>
"""


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = None


def render_header() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="app-title">
          <h1>面向计算机考研《数据结构》的 RAG 智能问答 Agent</h1>
          <p>本地知识库检索增强问答、代码生成、多轮上下文、工具日志与检索可视化。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(config) -> None:
    st.sidebar.header("知识库")
    materials = list_material_files()
    st.sidebar.write(f"资料文件：{len(materials)} 个")
    st.sidebar.write("向量库状态：" + ("已构建" if vector_store_exists() else "未构建"))
    st.sidebar.write("模型状态：" + ("已配置" if config.llm_ready else "缺少 API Key"))

    uploaded = st.sidebar.file_uploader(
        "上传 .txt / .md / .pdf",
        type=["txt", "md", "pdf"],
        accept_multiple_files=True,
    )
    if uploaded and st.sidebar.button("保存上传文件并重建知识库", use_container_width=True):
        saved = save_uploaded_files(uploaded)
        count, message = build_vector_store(config)
        st.sidebar.success(f"已保存 {len(saved)} 个文件。{message}")
        st.rerun()

    if st.sidebar.button("重建本地知识库", use_container_width=True):
        count, message = build_vector_store(config)
        if count:
            st.sidebar.success(message)
        else:
            st.sidebar.warning(message)

    with st.sidebar.expander("已发现资料", expanded=False):
        if materials:
            for path in materials:
                st.write(f"- {path.relative_to(MATERIALS_DIR)}")
        else:
            st.write("请将资料放入 materials 目录，或在这里上传。")


def render_retrieval_results(response) -> None:
    if not response or not response.results:
        st.info("本轮没有可展示的检索命中，或知识库相关性不足。")
        return
    for index, item in enumerate(response.results, start=1):
        text = html.escape(item.text[:700])
        st.markdown(
            f"""
            <div class="result-box">
              <div class="result-meta">[{index}] {html.escape(item.source)} · {html.escape(item.location)} · 相似度 {item.score:.3f}</div>
              <div class="result-text">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    ensure_project_dirs()
    init_state()
    config = load_config()
    if not vector_store_exists() and list_material_files():
        build_vector_store(config)
    render_header()
    render_sidebar(config)

    left, right = st.columns([0.68, 0.32], gap="large")
    with left:
        st.subheader("对话")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        question = st.chat_input("请输入数据结构考研相关问题，例如：什么是栈？请用 C++ 实现单链表逆置。")
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Agent 正在选择工具并生成回答..."):
                    response = run_agent(question, st.session_state.messages[:-1], config)
                st.markdown(response.answer)
            st.session_state.messages.append({"role": "assistant", "content": response.answer})
            st.session_state.last_response = response
            st.rerun()

    with right:
        st.subheader("本轮工具日志")
        response = st.session_state.last_response
        if response:
            st.markdown(f"<span class='status-pill'>工具：{response.tool_name}</span>", unsafe_allow_html=True)
            if response.code_language:
                st.markdown(f"<span class='status-pill'>语言：{response.code_language}</span>", unsafe_allow_html=True)
            for line in response.log:
                st.write(f"- {line}")
        else:
            st.info("提问后这里会展示 Agent 工具调用过程。")

        st.subheader("检索结果")
        render_retrieval_results(response)

        if st.button("清空当前会话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()


if __name__ == "__main__":
    main()
