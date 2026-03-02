# server.py
import json
import logging
from collections.abc import Sequence
from typing import Any
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

load_dotenv()

from . import tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-obsidian")

api_key = os.getenv("OBSIDIAN_API_KEY")
if not api_key:
    raise ValueError(f"OBSIDIAN_API_KEY environment variable required. Working directory: {os.getcwd()}")

app = Server("mcp-obsidian")

tool_handlers = {}

def add_tool_handler(tool_class: tools.ToolHandler):
    global tool_handlers
    tool_handlers[tool_class.name] = tool_class

def get_tool_handler(name: str) -> tools.ToolHandler | None:
    return tool_handlers.get(name)

# Vault read
add_tool_handler(tools.ListFilesInDirToolHandler())
add_tool_handler(tools.ListFilesInVaultToolHandler())
add_tool_handler(tools.GetFileContentsToolHandler())
add_tool_handler(tools.GetDocumentMapToolHandler())
add_tool_handler(tools.BatchGetFileContentsToolHandler())

# Vault write
add_tool_handler(tools.AppendContentToolHandler())
add_tool_handler(tools.PatchContentToolHandler())
add_tool_handler(tools.PutContentToolHandler())
add_tool_handler(tools.DeleteFileToolHandler())

# Active file
add_tool_handler(tools.GetActiveFileToolHandler())
add_tool_handler(tools.PutActiveFileToolHandler())
add_tool_handler(tools.AppendActiveFileToolHandler())
add_tool_handler(tools.PatchActiveFileToolHandler())
add_tool_handler(tools.DeleteActiveFileToolHandler())

# Periodic notes
add_tool_handler(tools.PeriodicNotesToolHandler())
add_tool_handler(tools.CreatePeriodicNoteToolHandler())
add_tool_handler(tools.GetPeriodicNoteForDateToolHandler())
add_tool_handler(tools.RecentPeriodicNotesToolHandler())

# Commands
add_tool_handler(tools.ListCommandsToolHandler())
add_tool_handler(tools.ExecuteCommandToolHandler())

# Search
add_tool_handler(tools.SearchToolHandler())
add_tool_handler(tools.ComplexSearchToolHandler())

# Recent changes
add_tool_handler(tools.RecentChangesToolHandler())


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [th.get_tool_description() for th in tool_handlers.values()]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    if not isinstance(arguments, dict):
        raise RuntimeError("arguments must be dictionary")
    tool_handler = get_tool_handler(name)
    if not tool_handler:
        raise ValueError(f"Unknown tool: {name}")
    try:
        return tool_handler.run_tool(arguments)
    except Exception as e:
        logger.error(str(e))
        raise RuntimeError(f"Caught Exception. Error: {str(e)}")


async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
