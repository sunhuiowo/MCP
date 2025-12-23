"""
MCP.server 的 Docstring
1.创建 fastmcp 的实例
2.创建函数，添加文档
3.@mcp.tool()
4.运行服务器
"""

import os
import json
import arxiv
from typing import List, Dict, Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research")
PAPER_DIR = "papers"

@mcp.tool()
def get_weather(city: str):
    """获取指定城市的天气信息。

    参数:
    city (str): 城市名称。

    返回:
    str: 天气信息。
    """
    return f"{city} 的天气是晴天。18度。"

@mcp.tool()
def add(a: int, b: int) -> int:
    """将两个整数相加并返回结果。

    参数:
    a (int): 第1个整数。
    b (int): 第2个整数。

    返回:
    int: 两个整数的和。
    """
    return a + b

@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    基于话题topic和它的存储信息在arxiv上搜索相关论文。
    参数:
        topic (str): 搜索的论文话题。
        max_results (int, optional): 最多返回的论文数量。默认为5。

    返回:
        List[str]: 搜索到的论文的IDs列表。
    """

    # 使用arxiv查找论文
    client = arxiv.Client()

    # 搜索与查询话题最相关的文章
    search = arxiv.Search(
        query=topic,
        max_results=max_results, 
        sort_by=arxiv.SortCriterion.Relevance,
    )
    papers = client.results(search)

    # 为此话题创建目录
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)

    file_paths = os.path.join(path, "papers_info.json")

    # 尝试加载现有论文信息
    try:
        with open(file_paths, "r") as f:
            papers_info = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # 处理每篇论文并添加到paper_info
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            "title": paper.title,
            "summary": paper.summary,
            "authors": [author.name for author in paper.authors],
            "published": str(paper.published.date()),
            "pdf_url": paper.pdf_url,
       }
        papers_info[paper.get_short_id()] = paper_info
    # 将更新的paper_info保存到json文件
    with open(file_paths, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)

    print(f"结果已保存到 {file_paths}")

    return paper_ids  

#print(search_papers("machine learning"))


@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    在所有话题目录中搜索特定论文的信息。

    参数:
        paper_id: 要查找的论文ID

    返回:
        如果找到则返回包含论文信息的JSON字符串，否则返回错误信息
    """
    
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                    if paper_id in papers_info:
                        return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue

    return f"There's no saved information related to paper {paper_id}."


@mcp.resource("papers://folders")
def get_available_folders() -> str:
    """
    列出papers目录中所有可用的主题文件夹。

    此资源提供所有可用主题文件夹的简单列表。
    """
    folders = []

    # 获取所有主题目录
    if os.path.exists(PAPER_DIR):
        for topic_dir in os.listdir(PAPER_DIR):
            topic_path = os.path.join(PAPER_DIR, topic_dir)
            if os.path.isdir(topic_path):
                papers_file = os.path.join(topic_path, "papers_info.json")
                if os.path.exists(papers_file):
                    folders.append(topic_dir)

    # 创建一个简单的markdown列表
    content = "# Available Topics\n\n"
    if folders:
        for folder in folders:
            content += f"- {folder}'\n"
        content += f"\nUse @{folder} to access papers in that topic.\n"
    else:
        content += "No topics found.\n"

    return content

@mcp.resource("papers://{topic}")
def get_topic_papers(topic: str) -> str:
    """
    获取特定主题的论文详细信息。

    参数:
        topic: 要检索论文的研究主题
    """
    import os
    import json
    
    topic_dir = topic.lower().replace(" ", "_")
    papers_file = os.path.join(PAPER_DIR, topic_dir, "papers_info.json")

    if not os.path.exists(papers_file):
        return f"# No papers found for topic: {topic}\n\nTry searching for papers on this topic first."
    try:
        with open(papers_file, 'r') as f:
            papers_data = json.load(f)

        # Create markdown content with paper details
        content = f"# Papers on {topic.replace('_', ' ').title()}\n\n"
        content += f"Total papers: {len(papers_data)}\n\n"

        for paper_id, paper_info in papers_data.items():
            content += f"## {paper_info['title']}\n"
            content += f"- **Paper ID**: {paper_id}\n"
            content += f"- **Authors**: {', '.join(paper_info['authors'])}\n"
            content += f"- **Published**: {paper_info['published']}\n"
            content += f"- **PDF URL**: [{paper_info['pdf_url']}]({paper_info['pdf_url']})\n\n"
            content += f"### Summary\n{paper_info['summary'][:500]}...\n\n"
            content += "---\n\n"

        return content
    except json.JSONDecodeError:
        return f"# Error reading papers data for {topic}\n\nThe papers data file is corrupted."
    except FileNotFoundError:
        return f"# Error: Papers data file not found for {topic}\n\nFile path: {papers_file}"

@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """生成一个提示词，用于让Claude查找和讨论特定主题的学术论文。"""
    return f"""Search for {num_papers} academic papers about '{topic}' using the search_papers tool.

Follow these instructions:
1. First, search for papers using search_papers(topic='{topic}', max_results={num_papers})
2. For each paper found, extract and organize the following information:
   - Paper title
   - Authors
   - Publication date
   - Brief summary of the key findings
   - Main contributions or innovations
   - Methodologies used
   - Relevance to the topic '{topic}'

3. Provide a comprehensive summary that includes:
   - Overview of the current state of research in '{topic}'
   - Common themes and trends across the papers
   - Key research gaps or areas for future investigation
   - Most impactful or influential papers in this area

4. Organize your findings in a clear, structured format with headings and bullet points for easy readability.

Please present both detailed information about each paper and a high-level synthesis of the research landscape in {topic}."""

if __name__ == "__main__":
    mcp.run(transport='stdio')
