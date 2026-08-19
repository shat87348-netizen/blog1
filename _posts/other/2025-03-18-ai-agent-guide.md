---
layout: post
title: "从零开始构建AI Agent：实战教程"
date: 2025-03-18
categories: [other]
permalink: /others/2025/03/18/ai-agent-guide.html
tags: [AI Agent, LangChain, 实战教程, Python]
author: zhangshuming
---

# 从零开始构建AI Agent：实战教程

本文将带你从零开始，使用LangChain构建一个能够搜索网络、执行代码、操作文件的AI Agent。我们将构建一个能够自主完成复杂任务的智能助手。

## 环境准备

### 1. 安装依赖

```bash
# 创建项目目录
mkdir ai-agent-project
cd ai-agent-project

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install langchain langchain-openai langchain-community
pip install duckduckgo-search  # 网络搜索工具
pip install python-dotenv  # 环境变量管理
```

### 2. 配置API密钥

创建 `.env` 文件：

```bash
OPENAI_API_KEY=your-api-key-here
```

在代码中加载：

```python
from dotenv import load_dotenv
load_dotenv()
```

## 实战项目：构建多功能AI Agent

### 步骤1：创建基础Agent

创建 `agent.py` 文件：

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
import os
from dotenv import load_dotenv

load_dotenv()

# 初始化LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# 创建搜索工具
search = DuckDuckGoSearchRun()

# 创建计算器工具
def calculator(expression: str) -> str:
    """执行数学计算"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"

calc_tool = Tool(
    name="Calculator",
    func=calculator,
    description="执行数学计算，输入数学表达式，返回计算结果"
)

# 创建文件读取工具
def read_file(file_path: str) -> str:
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败: {str(e)}"

read_tool = Tool(
    name="ReadFile",
    func=read_file,
    description="读取文件内容，输入文件路径"
)

# 创建文件写入工具
def write_file(file_path: str, content: str) -> str:
    """写入文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"文件 {file_path} 写入成功"
    except Exception as e:
        return f"写入文件失败: {str(e)}"

write_tool = Tool(
    name="WriteFile",
    func=write_file,
    description="写入文件，需要两个参数：文件路径和内容"
)

# 组合所有工具
tools = [search, calc_tool, read_tool, write_tool]

# 创建Prompt模板
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个智能助手，可以使用以下工具完成任务：
    - 网络搜索：获取实时信息
    - 计算器：执行数学计算
    - 文件操作：读取和写入文件
    
    请根据用户需求，选择合适的工具完成任务。如果任务需要多个步骤，请逐步执行。"""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 创建Agent
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 运行Agent
if __name__ == "__main__":
    result = agent_executor.invoke({
        "input": "搜索'Python异步编程'的最新信息，然后创建一个markdown文件总结要点"
    })
    print(result["output"])
```

### 步骤2：运行测试

```bash
python agent.py
```

你会看到Agent的思考过程：
1. 使用搜索工具查找信息
2. 分析搜索结果
3. 创建文件并写入内容

### 步骤3：增强Agent功能

添加更多实用工具：

```python
# 添加到 tools 列表

# 获取当前时间
from datetime import datetime
def get_time(query: str) -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

time_tool = Tool(
    name="GetTime",
    func=get_time,
    description="获取当前时间"
)

# 执行Python代码
import subprocess
import sys

def execute_python(code: str) -> str:
    """执行Python代码"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"执行错误: {result.stderr}"
    except Exception as e:
        return f"执行失败: {str(e)}"

python_tool = Tool(
    name="ExecutePython",
    func=execute_python,
    description="执行Python代码，返回执行结果"
)

# 更新工具列表
tools = [search, calc_tool, read_tool, write_tool, time_tool, python_tool]
```

### 步骤4：添加记忆功能

让Agent记住对话历史：

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    memory=memory
)

# 使用示例
result1 = agent_executor.invoke({"input": "我的名字是张三"})
result2 = agent_executor.invoke({"input": "我的名字是什么？"})  # Agent会记住
```

## 实战案例：数据分析Agent

创建一个专门用于数据分析的Agent：

```python
# data_analysis_agent.py
import pandas as pd
from langchain.tools import Tool

def analyze_csv(file_path: str, query: str) -> str:
    """分析CSV文件"""
    try:
        df = pd.read_csv(file_path)
        # 根据query执行分析
        if "统计" in query or "summary" in query.lower():
            return df.describe().to_string()
        elif "列" in query or "columns" in query.lower():
            return f"列名: {', '.join(df.columns.tolist())}"
        elif "行数" in query or "rows" in query.lower():
            return f"总行数: {len(df)}"
        else:
            return df.head(10).to_string()
    except Exception as e:
        return f"分析失败: {str(e)}"

analysis_tool = Tool(
    name="AnalyzeCSV",
    func=analyze_csv,
    description="分析CSV文件，支持统计、查看列名、行数等操作"
)

# 添加到工具列表
tools.append(analysis_tool)
```

## 常见问题解决

### 问题1：API调用失败

```python
# 添加重试机制
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def safe_invoke(agent_executor, input_text):
    return agent_executor.invoke({"input": input_text})
```

### 问题2：工具调用超时

```python
# 设置超时
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=10,  # 最大迭代次数
    max_execution_time=60  # 最大执行时间（秒）
)
```

### 问题3：成本控制

```python
# 使用更便宜的模型
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# 限制Token使用
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = agent_executor.invoke({"input": "..."})
    print(f"总Token: {cb.total_tokens}")
    print(f"总成本: ${cb.total_cost}")
```

## 部署到生产环境

### 使用FastAPI创建API服务

```python
# api.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AgentRequest(BaseModel):
    query: str
    conversation_id: str = None

@app.post("/agent/query")
async def query_agent(request: AgentRequest):
    result = agent_executor.invoke({"input": request.query})
    return {
        "output": result["output"],
        "intermediate_steps": result.get("intermediate_steps", [])
    }

# 运行: uvicorn api:app --reload
```

## 完整项目结构

```
ai-agent-project/
├── agent.py              # 主Agent文件
├── tools.py              # 自定义工具
├── api.py                # API服务
├── requirements.txt      # 依赖列表
├── .env                  # 环境变量
└── README.md             # 项目说明
```

## 下一步优化

1. **添加向量存储**：使用Chroma存储长期记忆
2. **多Agent协作**：使用CrewAI实现Agent团队
3. **Web界面**：使用Streamlit创建交互界面
4. **监控日志**：记录所有Agent操作

## 总结

通过本教程，你已经掌握了：
- ✅ 使用LangChain创建AI Agent
- ✅ 添加自定义工具
- ✅ 实现记忆功能
- ✅ 处理错误和优化性能
- ✅ 部署到生产环境

现在你可以根据具体需求，扩展Agent的功能，构建更强大的智能助手！

## 参考资源

- [LangChain Agents文档](https://python.langchain.com/docs/modules/agents/)
- [完整代码示例](https://github.com/langchain-ai/langchain/tree/master/templates)
