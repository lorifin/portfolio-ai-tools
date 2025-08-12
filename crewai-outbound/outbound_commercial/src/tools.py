from __future__ import annotations
from crewai_tools import DirectoryReadTool, FileReadTool, SerperDevTool
from typing import Optional

def build_tools(instructions_dir: str, serper_api_key: Optional[str]):
    dir_tool = DirectoryReadTool(directory=instructions_dir)
    file_tool = FileReadTool()
    # Serper est optionnel
    search_tool = SerperDevTool() if serper_api_key else None
    tools = [dir_tool, file_tool] + ([search_tool] if search_tool else [])
    return tools, search_tool
