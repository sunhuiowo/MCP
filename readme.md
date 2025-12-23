# MCP_3 项目说明

## 项目概述

MCP_3是一个基于Model Context Protocol (MCP)的应用框架，用于构建能够与外部资源和工具交互的AI系统。该项目提供了论文搜索与管理、天气查询等功能，展示了MCP在实际应用中的使用方式。

## 目录结构

```
MCP_3/
├── papers/                  # 论文存储目录
│   ├── ai_courses_and_specializations/  # AI课程与专业化论文
│   └── few-shot/           # Few-shot学习论文
├── __init__.py             # 包初始化文件
├── client.py               # MCP客户端实现demo
├── mcp_chatbot.py          # MCP聊天机器人
├── mcp_summary.md          # MCP论文摘要
├── readme.md               # 项目说明文档
├── server.py               # 主MCP服务器
├── server_config.json      # MCP服务器配置
└── weather_server.py       # 天气服务MCP服务器
```

## 安装说明

1. 克隆或下载项目到本地
2. 安装必要的依赖：

```bash
pip install -r requirements.txt
```

## 配置说明

### server_config.json

配置文件定义了MCP服务器的连接参数：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "MCP_3"]
    },
    "research": {
      "command": "uv",
      "args": ["run", "MCP_3/server.py"]
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}
```

## 使用方法

### 启动服务器

#### 主服务器

```bash
uv run MCP_3/server.py
```

### 检查服务器

使用MCP检查器查看服务器提供的工具和资源：

```bash
# 本地检查服务器
npx @modelcontextprotocol/inspector uv run MCP_3/server.py

# 远程检查服务器
修改server.py启动命令后运行
npx @modelcontextprotocol/inspector
```

### 使用聊天机器人

启动MCP聊天机器人进行交互式操作：

```bash
uv run MCP_3/mcp_chatbot.py
```

#### 聊天机器人命令

- `@folders` - 查看可用的论文主题
- `@<topic>` - 搜索特定主题的论文
- `/prompts` - 列出可用的提示词
- `/prompt <name> <arg1=value1>` - 执行提示词
- `quit` - 退出聊天机器人

## 功能介绍

### 1. 论文搜索与管理

主服务器提供以下工具：

- `search_papers(topic, max_results)` - 搜索特定主题的论文
- `extract_info(paper_id)` - 提取特定论文的详细信息
- `get_weather(city)` - 获取指定城市的天气信息
- `add(a, b)` - 将两个整数相加

### 2. 资源与提示词

#### 资源

- `papers://folders` - 论文主题目录资源
- `papers://<topic>` - 特定主题的论文资源

#### 提示词

- `generate_search_prompt(topic, num_papers)` - 生成用于搜索和分析论文的提示词

## 示例

### 搜索论文

```
Query: search for paper on few-shot
```

### 搜索论文并保存摘要

```
Query: search for paper on few-shot，save the content in the file "mcp_summary.md"
```

### 获取天气信息

```
Query: Get weather forecast for New York
```

### 获取天气警报

```
Query: Get weather alerts for California
```

## 开发说明

### 添加新的MCP工具

在服务器文件中使用`@mcp.tool()`装饰器添加新工具：

```python
@mcp.tool()
def new_tool(param1, param2):
    """工具描述"""
    # 工具实现
    return result
```

### 添加新的MCP资源

在服务器文件中使用`@mcp.resource()`装饰器添加新资源：

```python
@mcp.resource(uri="resource://name")
def get_resource():
    """资源描述"""
    # 资源实现
    return resource_content
```

## 许可证

MIT License
