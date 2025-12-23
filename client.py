from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio

# 创建标准输入输出连接的服务器参数
server_params = StdioServerParameters(
    command="uv",  # 可执行文件
    args=["run", "server.py"],  # 可选命令行参数
    env=None,  # 可选环境变量
)

async def run():
    # 启动服务器作为子进程
    # read 是客户端用于从服务器读取消息的流
    # write 是客户端用于向服务器写入消息的流
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接（与服务器的1:1连接）
            await session.initialize()

            # 列出可用工具
            tools = await session.list_tools()

            # 这里将调用chat_loop
            # ...

            # 调用工具：这将在process_query方法中执行
            result = await session.call_tool("tool-name", arguments={"arg1": "value"})

if __name__ == "__main__":
    asyncio.run(run())