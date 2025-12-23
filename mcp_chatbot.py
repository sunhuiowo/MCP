from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, Any, TypedDict
import asyncio
import nest_asyncio
import openai
import json
from contextlib import AsyncExitStack
nest_asyncio.apply()

load_dotenv()

class ToolDefinition(TypedDict):
    type: str
    function: Dict[str, Any]
    # name: str  # 修正：应该是 name 而不是 nam
    # description: str
    # input_schema: Dict[str, Any]

class MCP_ChatBot:

    def __init__(self):
        # Initialize session and client objects
        self.sessions = {}
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[ToolDefinition] = []
        self.available_prompts: List[str] = []
        self.tool_to_session: Dict[str, ClientSession] = {}
        self.openai_client = openai.OpenAI(
            base_url="http://127.0.0.1:11434/v1",
            api_key="None"
        )
        self.model = "qwen2.5:7b"

        
    async def process_query(self, query: str) -> str:
        """处理用户查询，支持多轮工具调用"""
        # 初始化消息历史
        messages = [{"role": "user", "content": query}]
        
        # 最大工具调用轮次，防止无限循环
        max_tool_rounds = 20
        current_round = 0
        
        while current_round < max_tool_rounds:
            current_round += 1
            
            # 1. 调用OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.available_tools,
            )
            
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
            # 2. 如果没有工具调用，直接返回结果
            if finish_reason != "tool_calls":
                print(f"AI最终回复: {message.content}")
                return message.content
            
            # 3. 有工具调用，处理每个工具
            print(f"\n[第 {current_round} 轮工具调用]")
            
            # 添加助手消息（包含工具调用信息）
            assistant_message = {"role": "assistant", "content": message.content}
            if hasattr(message, 'tool_calls') and message.tool_calls:
                assistant_message["tool_calls"] = message.tool_calls
            messages.append(assistant_message)
            
            # 处理每个工具调用
            for tool_call in message.tool_calls:
                tool_id = tool_call.id
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                print(f"调用工具: {tool_name}, 参数: {tool_args}")
                
                # 执行工具
                if tool_name in self.tool_to_session:
                    session = self.tool_to_session[tool_name]
                    tool_result = await session.call_tool(tool_name, tool_args)
                else:
                    tool_result = f"错误: 未找到工具 '{tool_name}'"
                
                print(f"工具结果: {tool_result}")
                
                # 添加工具结果到消息历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": str(tool_result.content)
                })
            
            # 4. 继续循环，让AI处理工具结果
            # 循环会继续，使用更新后的messages进行下一轮调用
        
        # 如果达到最大轮次，返回最后的消息
        return "已达到最大工具调用轮次，请简化您的请求。"
    



    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """连接到单个MCP服务器。"""
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            await session.initialize()
            #self.sessions.append(session)

            try:
                # List available tools for this session
                response = await session.list_tools()
                tools = response.tools
                print(f"\nConnected to {server_name} with tools:", [t.name for t in tools])
                for tool in tools:  # new
                    self.tool_to_session[tool.name] = session
                    self.available_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        },
                    })


                response_prompt = await session.list_prompts()
                if response_prompt and response_prompt.prompts:
                    print(f"\nConnected to {server_name} with prompts:", [p.name for p in response_prompt.prompts])
                    for prompt in response_prompt.prompts:
                        print(f"prompt: {prompt}")
                        print(f"Prompt: {prompt.name}")
                        self.sessions[prompt.name] = session
                        self.available_prompts.append({
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments
                        })
                response_resource = await session.list_resources()
                if response_resource and response_resource.resources:
                    print(f"\nConnected to {server_name} with resources:", [r.name for r in response_resource.resources])
                    for resource in response_resource.resources:
                        resource_uri = str(resource.uri)
                        self.sessions[resource_uri] = session
            except Exception as e:
                print(f"Error: {e}")

        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self):  # new
        """连接到所有配置的MCP服务器。"""
        try:
            with open("MCP_3/server_config.json", "r") as file:
                data = json.load(file)

            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise
                # Close the session


    async def get_resource(self, resource_uri):
        session = self.sessions.get(resource_uri)

        # Fallback for papers URIs - try any papers resource session
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.sessions.items():
                if uri.startswith("papers://"):
                    session = sess
                    break

        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return

        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource: {resource_uri}")
                print("Content:")
                print(result.contents[0].text)
            else:
                print("No content available.")
        except Exception as e:
            print(f"Error: {e}")

    async def list_prompts(self):
        """List all available prompts."""
        if not self.available_prompts:
            print("No prompts available.")
            return

        print("\nAvailable prompts:")
        for prompt in self.available_prompts:
            print(f"-- {prompt['name']}: {prompt['description']}")
            if prompt.get('arguments'):
                print(f"  Arguments:")
                for arg in prompt['arguments']:
                    arg_name = arg.name if hasattr(arg, 'name') else arg.get('name', '')
                    print(f"    - {arg_name}")


    async def execute_prompt(self, prompt_name, args):
        """Execute a prompt with the given arguments."""
        session = self.sessions.get(prompt_name)
        if not session:
            print(f"Prompt '{prompt_name}' not found.")
            return

        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content
                #print(f"Prompt content: {prompt_content}")

                # Extract text from content (handles different formats)
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, 'text'):
                    text = prompt_content.text
                else:
                    # Handle list of content items
                    text = " ".join(
                        item.text if hasattr(item, 'text') else str(item)
                        for item in prompt_content
                    )

                print(f"\nExecuting prompt '{prompt_name}'...")
                #print(f"Prompt text: {text}")
                await self.process_query(text)
        except Exception as e:
            print(f"Error: {e}")


    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        print("Use @folders to see available topics")
        print("Use @<topic> to search papers in that topic")
        print("Use /prompts to list available prompts")
        print("Use /prompt <name> <arg1=value1> to execute a prompt")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if not query:
                    continue
                if query.lower() == 'quit':
                    break

                # Check for @resource syntax first
                if query.startswith('@'):
                    # Remove @ sign
                    topic = query[1:]
                    if topic == "folders":
                        resource_uri = "papers://folders"
                    else:
                        resource_uri = f"papers://{topic}"
                    await self.get_resource(resource_uri)
                    continue

                # Check for /command syntax
                if query.startswith('/'):
                    parts = query.split()
                    command = parts[0].lower()
                    if command == '/prompts':
                        await self.list_prompts()
                    elif command == '/prompt':
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1> <arg2=value2> ...")
                            continue

                        prompt_name = parts[1]
                        args = {}
                        for arg in parts[2:]:
                            if '=' in arg:
                                key, value = arg.split('=', 1)
                                args[key] = value

                        await self.execute_prompt(prompt_name, args)
                    else:
                        print(f"Unknown command: {command}")
                    continue

                await self.process_query(query)

            except Exception as e:
                print(f"\nError: {str(e)}")


        async def cleaup(self):
            """使用AsyncExitStack干净地关闭所有资源。"""
            await self.exit_stack.aclose()



async def main():
    bot = MCP_ChatBot()
    try:
        await bot.connect_to_servers()
        await bot.chat_loop()
    except Exception as e:
        await bot.cleaup()
        print(f"Error connecting to servers: {e}")


if __name__ == "__main__":
    asyncio.run(main())