# 面向计算机考研《数据结构》的 RAG 智能问答 Agent

这是一个基于 Streamlit 的课程考核项目，支持本地知识库检索增强问答、数据结构代码生成、基础多轮对话、工具调用日志、知识库上传和检索结果可视化。

## 运行步骤

1. 安装依赖：

```powershell
pip install -r requirements.txt
```

2. 复制环境变量文件：

```powershell
Copy-Item .env.example .env
```

3. 在 `.env` 中填写 OpenAI 兼容 API 配置：

```text
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

4. 将知识库资料放入 `materials/` 目录，支持 `.txt`、`.md`、`.pdf`。

5. 启动应用：

```powershell
streamlit run app.py
```

## 功能

- `rag_qa`：基于本地知识库检索并生成带引用依据的回答。
- `code_gen`：生成《数据结构》范围内代码，说明核心思路、时间复杂度、空间复杂度。
- Agent 自动判断问题类型并选择工具。
- 支持当前会话内多轮对话。
- 支持前端上传知识库文件并重建向量库。
- 支持展示工具调用日志和检索命中文档片段。
- `exercise_gen`：根据知识库内容生成选择题、填空题和简答题，并给出答案。
- 代码生成结果会在页面右侧“代码高亮”区域以语法高亮方式展示。

## 目录结构

```text
app.py
src/
  agent.py
  codegen.py
  config.py
  ingest.py
  rag.py
materials/
vector_store/
scripts/
tests/
说明文档.docx
```
