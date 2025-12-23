# MCP 操作流程

## 1. MCP系统概述

MCP (Model Context Protocol) 是一个用于构建能够与外部资源和工具交互的AI系统的框架。MCP_3项目实现了这一框架，包含以下核心组件：

- **聊天机器人** (`mcp_chatbot.py`): 提供交互式界面，处理用户查询并调用MCP工具
- **研究服务器** (`server.py`): 提供论文搜索、天气查询等工具
- **服务器配置** (`server_config.json`): 定义MCP服务器的连接参数

## 2. 组件间的交互流程

### 2.1 系统启动流程

```
1. 用户启动聊天机器人: python mcp_chatbot.py
2. 聊天机器人读取server_config.json配置
3. 聊天机器人连接到所有配置的MCP服务器
4. 服务器启动并初始化其工具、资源和提示词
5. 聊天机器人获取并注册所有服务器提供的工具
6. 聊天机器人进入聊天循环，等待用户输入
```

### 2.2 工具调用流程

```
1. 用户输入查询（例如："搜索关于few-shot学习的论文"）
2. 聊天机器人将查询发送给AI模型
3. AI模型分析查询，确定需要调用的工具
4. 聊天机器人接收AI模型的响应，包含工具调用信息
5. 聊天机器人根据工具名称找到对应的服务器会话
6. 聊天机器人向服务器发送工具调用请求
7. 服务器执行工具并返回结果
8. 聊天机器人将工具结果发送给AI模型
9. AI模型基于工具结果生成最终响应
10. 聊天机器人将最终响应返回给用户
```

## 3. 服务器操作流程

### 3.1 服务器启动

```python
# 创建FastMCP实例
mcp = FastMCP("research", port=8080)

# 定义工具
@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    # 工具实现
    pass

# 定义资源
@mcp.resource("papers://folders")
def get_available_folders() -> str:
    # 资源实现
    pass

# 定义提示词
@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    # 提示词实现
    pass

# 运行服务器
if __name__ == "__main__":
    mcp.run(transport='sse')
```

### 3.2 工具执行流程

1. 服务器接收工具调用请求
2. 根据工具名称找到对应的函数
3. 验证输入参数
4. 执行函数逻辑
5. 返回执行结果

### 3.3 资源访问流程

1. 服务器接收资源访问请求
2. 根据资源URI找到对应的函数
3. 验证输入参数
4. 执行函数逻辑
5. 返回资源内容

## 4. 客户端操作流程

### 4.1 客户端初始化

```python
# 读取服务器配置
with open("MCP_3/server_config.json", "r") as file:
    data = json.load(file)

# 连接到所有配置的服务器
servers = data.get("mcpServers", {})
for server_name, server_config in servers.items():
    await self.connect_to_server(server_name, server_config)
```

### 4.2 服务器连接流程

```python
async def connect_to_server(self, server_name: str, server_config: dict) -> None:
    # 创建服务器参数
    server_params = StdioServerParameters(**server_config)
    # 创建stdio客户端
    stdio_transport = await self.exit_stack.enter_async_context(
        stdio_client(server_params)
    )
    read, write = stdio_transport
    # 创建会话
    session = await self.exit_stack.enter_async_context(
        ClientSession(read, write)
    )
    # 初始化会话
    await session.initialize()
    # 列出可用工具
    response = await session.list_tools()
    # 注册工具
    for tool in tools:
        self.tool_to_session[tool.name] = session
        self.available_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            },
        })
```

### 4.3 用户查询处理流程

```python
async def process_query(self, query: str) -> str:
    # 初始化消息历史
    messages = [{"role": "user", "content": query}]
    # 最大工具调用轮次
    max_tool_rounds = 20
    current_round = 0
    
    while current_round < max_tool_rounds:
        current_round += 1
        # 调用AI模型
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.available_tools,
        )
        # 处理AI响应
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        # 如果没有工具调用，直接返回结果
        if finish_reason != "tool_calls":
            return message.content
        # 处理工具调用
        for tool_call in message.tool_calls:
            tool_id = tool_call.id
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            # 执行工具
            if tool_name in self.tool_to_session:
                session = self.tool_to_session[tool_name]
                tool_result = await session.call_tool(tool_name, tool_args)
            # 添加工具结果到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": str(tool_result.content)
            })
```

## 5. 典型使用场景

### 5.1 搜索论文

```
用户: 搜索关于few-shot学习的论文
聊天机器人: 调用search_papers工具搜索论文
服务器: 在arxiv上搜索few-shot学习的论文，保存到papers/few-shot/papers_info.json
聊天机器人: 将搜索结果发送给AI模型
AI模型: 生成关于搜索结果的总结
聊天机器人: 将总结返回给用户
```

### 5.2 访问论文资源

```
用户: @folders
聊天机器人: 访问papers://folders资源
服务器: 返回所有论文主题列表
聊天机器人: 将主题列表显示给用户

用户: @few-shot
聊天机器人: 访问papers://few-shot资源
服务器: 返回few-shot主题的所有论文详细信息
聊天机器人: 将论文详细信息显示给用户
```

### 5.3 使用提示词

```
用户: /prompt generate_search_prompt topic=machine learning num_papers=3
聊天机器人: 调用generate_search_prompt提示词
服务器: 返回生成的提示词内容
聊天机器人: 使用该提示词调用AI模型
AI模型: 根据提示词生成搜索策略和指令
AI模型: 确定需要调用search_papers工具
聊天机器人: 调用search_papers工具搜索机器学习论文
服务器: 返回搜索到的论文ID列表
聊天机器人: 将搜索结果发送给AI模型
AI模型: 调用extract_info工具获取每篇论文的详细信息
聊天机器人: 调用extract_info工具获取论文详情
服务器: 返回每篇论文的详细信息
聊天机器人: 将论文详情发送给AI模型
AI模型: 根据所有论文信息生成综合分析
聊天机器人: 将综合分析结果显示给用户
```

## 6. 配置管理

服务器配置文件`server_config.json`定义了所有MCP服务器的连接参数：

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

可以通过修改此文件添加或删除MCP服务器。

## 7. 错误处理

- **服务器连接错误**: 聊天机器人会捕获连接错误并显示错误信息
- **工具调用错误**: 聊天机器人会捕获工具调用错误并显示错误信息
- **资源访问错误**: 服务器会返回适当的错误信息
- **AI模型错误**: 聊天机器人会捕获AI模型错误并显示错误信息

## 8. 最佳实践

1. **服务器设计**: 
   - 为每个功能创建独立的工具
   - 为工具提供清晰的文档字符串
   - 使用适当的参数验证

2. **客户端设计**: 
   - 实现适当的错误处理
   - 限制工具调用的最大轮次
   - 提供友好的用户界面

3. **配置管理**: 
   - 使用JSON配置文件管理服务器连接
   - 定期更新服务器配置

4. **性能优化**: 
   - 使用异步编程提高性能
   - 限制工具调用的超时时间
   - 缓存频繁使用的结果
