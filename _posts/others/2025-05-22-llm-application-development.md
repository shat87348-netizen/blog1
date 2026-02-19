---
layout: post
title: "30分钟搭建RAG智能问答系统：完整实战教程"
date: 2025-05-22
categories: [others]
tags: [LLM, RAG, LangChain, 向量数据库, 实战教程]
author: zhangshuming
---

# 30分钟搭建RAG智能问答系统：完整实战教程

本教程将带你从零开始，使用LangChain和Chroma构建一个完整的RAG（检索增强生成）智能问答系统。系统能够基于你的文档库回答问题，非常适合构建知识库助手、文档问答等应用。

## 项目目标

构建一个能够：
- 读取本地文档（Markdown、PDF、TXT等）
- 将文档向量化存储
- 根据用户问题检索相关文档
- 基于检索内容生成准确回答
- 提供Web界面交互

## 第一步：环境搭建（5分钟）

### 1. 创建项目

```bash
mkdir rag-qa-system
cd rag-qa-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

创建 `requirements.txt`：

```txt
langchain==0.1.0
langchain-openai==0.0.2
langchain-community==0.0.10
chromadb==0.4.22
pypdf==3.17.4
python-dotenv==1.0.0
fastapi==0.109.0
uvicorn==0.27.0
streamlit==1.31.0
```

安装：

```bash
pip install -r requirements.txt
```

### 3. 配置API密钥

创建 `.env` 文件：

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

## 第二步：构建知识库（10分钟）

### 1. 准备文档

创建 `documents` 目录，放入你的文档：

```bash
mkdir documents
# 放入一些 .md 或 .txt 文件
```

### 2. 创建文档加载和向量化脚本

创建 `build_knowledge_base.py`：

```python
import os
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# 配置
DOCUMENTS_DIR = "./documents"
CHROMA_DB_DIR = "./chroma_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def load_documents():
    """加载所有文档"""
    print("📚 开始加载文档...")
    
    # 加载Markdown和文本文件
    text_loader = DirectoryLoader(
        DOCUMENTS_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    
    txt_loader = DirectoryLoader(
        DOCUMENTS_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    
    # 加载PDF文件
    pdf_loader = DirectoryLoader(
        DOCUMENTS_DIR,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader
    )
    
    documents = []
    documents.extend(text_loader.load())
    documents.extend(txt_loader.load())
    documents.extend(pdf_loader.load())
    
    print(f"✅ 成功加载 {len(documents)} 个文档")
    return documents

def split_documents(documents):
    """分割文档为小块"""
    print("✂️ 开始分割文档...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    
    splits = text_splitter.split_documents(documents)
    print(f"✅ 文档分割为 {len(splits)} 个块")
    return splits

def create_vectorstore(splits):
    """创建向量数据库"""
    print("🔢 开始创建向量数据库...")
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # 如果已存在数据库，先删除
    if os.path.exists(CHROMA_DB_DIR):
        import shutil
        shutil.rmtree(CHROMA_DB_DIR)
    
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    
    print(f"✅ 向量数据库创建完成，保存在 {CHROMA_DB_DIR}")
    return vectorstore

if __name__ == "__main__":
    # 1. 加载文档
    documents = load_documents()
    
    if len(documents) == 0:
        print("❌ 未找到文档，请在 documents 目录下放置文档文件")
        exit(1)
    
    # 2. 分割文档
    splits = split_documents(documents)
    
    # 3. 创建向量数据库
    vectorstore = create_vectorstore(splits)
    
    print("\n🎉 知识库构建完成！")
```

### 3. 运行构建脚本

```bash
python build_knowledge_base.py
```

## 第三步：创建问答系统（10分钟）

### 1. 创建核心问答模块

创建 `qa_system.py`：

```python
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

class QASystem:
    def __init__(self, db_path="./chroma_db"):
        """初始化问答系统"""
        # 加载向量数据库
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = Chroma(
            persist_directory=db_path,
            embedding_function=embeddings
        )
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            streaming=True
        )
        
        # 创建自定义Prompt
        prompt_template = """基于以下上下文信息回答问题。如果你不知道答案，就说不知道，不要编造答案。

上下文信息：
{context}

问题：{question}

请用中文回答，答案要准确、简洁："""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # 创建检索链
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 3}  # 检索前3个最相关的文档块
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
    
    def ask(self, question: str):
        """回答问题"""
        result = self.qa_chain({"query": question})
        return {
            "answer": result["result"],
            "sources": [
                {
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "未知")
                }
                for doc in result["source_documents"]
            ]
        }

# 使用示例
if __name__ == "__main__":
    qa = QASystem()
    
    while True:
        question = input("\n请输入问题（输入'quit'退出）: ")
        if question.lower() == 'quit':
            break
        
        result = qa.ask(question)
        print(f"\n回答: {result['answer']}")
        print(f"\n参考来源:")
        for i, source in enumerate(result['sources'], 1):
            print(f"{i}. {source['source']}")
```

### 2. 测试问答系统

```bash
python qa_system.py
```

## 第四步：创建Web界面（5分钟）

### 1. 使用Streamlit创建界面

创建 `app.py`：

```python
import streamlit as st
from qa_system import QASystem
import os

# 页面配置
st.set_page_config(
    page_title="智能问答系统",
    page_icon="🤖",
    layout="wide"
)

# 初始化问答系统
@st.cache_resource
def init_qa_system():
    if not os.path.exists("./chroma_db"):
        st.error("❌ 未找到向量数据库，请先运行 build_knowledge_base.py")
        return None
    return QASystem()

qa_system = init_qa_system()

# 标题
st.title("🤖 智能问答系统")
st.markdown("基于RAG技术的文档问答系统")

# 侧边栏
with st.sidebar:
    st.header("📖 使用说明")
    st.markdown("""
    1. 在 `documents` 目录下放置你的文档
    2. 运行 `build_knowledge_base.py` 构建知识库
    3. 在此界面输入问题，获取答案
    """)
    
    st.header("⚙️ 设置")
    max_sources = st.slider("最大参考文档数", 1, 5, 3)

# 聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message:
            with st.expander("📚 参考来源"):
                for i, source in enumerate(message["sources"], 1):
                    st.markdown(f"**来源 {i}**: {source['source']}")
                    st.code(source['content'])

# 用户输入
if prompt := st.chat_input("请输入你的问题..."):
    if qa_system is None:
        st.error("系统未初始化，请检查配置")
    else:
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 获取回答
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                result = qa_system.ask(prompt)
                answer = result["answer"]
                sources = result["sources"][:max_sources]
            
            st.markdown(answer)
            
            # 显示来源
            with st.expander("📚 参考来源"):
                for i, source in enumerate(sources, 1):
                    st.markdown(f"**来源 {i}**: {source['source']}")
                    st.code(source['content'])
        
        # 添加助手消息
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })
```

### 2. 运行Web界面

```bash
streamlit run app.py
```

浏览器会自动打开，你可以开始使用问答系统了！

## 第五步：优化和扩展

### 1. 添加对话历史

修改 `qa_system.py`：

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain

class QASystem:
    def __init__(self, db_path="./chroma_db"):
        # ... 前面的代码 ...
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            return_source_documents=True
        )
```

### 2. 添加流式输出

```python
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

class StreamingCallbackHandler(StreamingStdOutCallbackHandler):
    def __init__(self, container):
        self.container = container
        self.text = ""
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

# 在Streamlit中使用
with st.chat_message("assistant"):
    callback = StreamingCallbackHandler(st.empty())
    # 配置LLM使用callback
```

### 3. 支持更多文档格式

```python
# 添加Word文档支持
from langchain_community.document_loaders import Docx2txtLoader

docx_loader = DirectoryLoader(
    DOCUMENTS_DIR,
    glob="**/*.docx",
    loader_cls=Docx2txtLoader
)
```

### 4. 添加文档上传功能

在 `app.py` 中添加：

```python
uploaded_file = st.file_uploader("上传文档", type=['md', 'txt', 'pdf'])
if uploaded_file:
    # 保存文件
    with open(f"documents/{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("文件上传成功！请重新构建知识库。")
```

## 常见问题解决

### 问题1：向量数据库未找到

```bash
# 确保先运行构建脚本
python build_knowledge_base.py
```

### 问题2：API调用失败

```python
# 检查 .env 文件中的API密钥
# 确保账户有足够的余额
```

### 问题3：文档加载失败

```python
# 检查文档编码
# PDF文件可能需要安装额外依赖
pip install pypdf
```

## 项目结构

```
rag-qa-system/
├── documents/              # 文档目录
│   ├── doc1.md
│   └── doc2.txt
├── chroma_db/              # 向量数据库（自动生成）
├── build_knowledge_base.py # 构建知识库
├── qa_system.py           # 问答系统核心
├── app.py                 # Streamlit界面
├── requirements.txt       # 依赖列表
├── .env                   # 环境变量
└── README.md              # 项目说明
```

## 部署到生产环境

### 使用Docker部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 使用FastAPI部署API

创建 `api.py`：

```python
from fastapi import FastAPI
from pydantic import BaseModel
from qa_system import QASystem

app = FastAPI()
qa = QASystem()

class Question(BaseModel):
    question: str

@app.post("/ask")
async def ask(question: Question):
    result = qa.ask(question.question)
    return result
```

## 总结

通过本教程，你已经掌握了：
- ✅ 使用LangChain构建RAG系统
- ✅ 使用Chroma存储向量数据
- ✅ 创建Web界面交互
- ✅ 优化和扩展功能

现在你可以基于这个系统，构建自己的知识库助手、文档问答、客服机器人等应用！

## 参考资源

- [LangChain RAG文档](https://python.langchain.com/docs/use_cases/question_answering/)
- [Chroma文档](https://docs.trychroma.com/)
- [完整代码仓库](https://github.com/langchain-ai/langchain/tree/master/templates)
