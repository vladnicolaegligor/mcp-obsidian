# tools.py
from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
from . import obsidian

api_key = os.getenv("OBSIDIAN_API_KEY", "")
obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")

if api_key == "":
    raise ValueError(f"OBSIDIAN_API_KEY environment variable required. Working directory: {os.getcwd()}")

TOOL_LIST_FILES_IN_VAULT = "obsidian_list_files_in_vault"
TOOL_LIST_FILES_IN_DIR = "obsidian_list_files_in_dir"

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()

# ── Vault read tools ───────────────────────────────────────────────────────

class ListFilesInVaultToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_VAULT)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories in the root directory of your Obsidian vault.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )

    def run_tool(self, args: dict):
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        files = api.list_files_in_vault()
        return [TextContent(type="text", text=json.dumps(files, indent=2))]


class ListFilesInDirToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_DIR)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories that exist in a specific Obsidian directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Path to list files from (relative to your vault root). Note that empty directories will not be returned."
                    },
                },
                "required": ["dirpath"]
            }
        )

    def run_tool(self, args: dict):
        if "dirpath" not in args:
            raise RuntimeError("dirpath argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        files = api.list_files_in_dir(args["dirpath"])
        return [TextContent(type="text", text=json.dumps(files, indent=2))]


class GetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the content of a single file in your vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the relevant file (relative to your vault root).", "format": "path"},
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict):
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_file_contents(args["filepath"])
        return [TextContent(type="text", text=json.dumps(content, indent=2))]


class GetDocumentMapToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_document_map")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Inspect all available PATCH targets in a file: headings, block references, and frontmatter fields. "
                "Use this before calling obsidian_patch_content to discover valid targets and their exact names."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file (relative to vault root).", "format": "path"},
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict):
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        result = api.get_document_map(args["filepath"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class BatchGetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_batch_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the contents of multiple files in your vault, concatenated with headers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepaths": {
                        "type": "array",
                        "items": {"type": "string", "description": "Path to a file (relative to your vault root)", "format": "path"},
                        "description": "List of file paths to read"
                    },
                },
                "required": ["filepaths"]
            }
        )

    def run_tool(self, args: dict):
        if "filepaths" not in args:
            raise RuntimeError("filepaths argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_batch_file_contents(args["filepaths"])
        return [TextContent(type="text", text=content)]

# ── Vault write tools ──────────────────────────────────────────────────────

class AppendContentToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_append_content")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Append content to a new or existing file in the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file (relative to vault root)", "format": "path"},
                    "content": {"type": "string", "description": "Content to append to the file"}
                },
                "required": ["filepath", "content"]
            }
        )

    def run_tool(self, args: dict):
        if "filepath" not in args or "content" not in args:
            raise RuntimeError("filepath and content arguments required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.append_content(args["filepath"], args["content"])
        return [TextContent(type="text", text=f"Successfully appended content to {args['filepath']}")]


class PatchContentToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_patch_content")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Insert content into an existing note relative to a heading, block reference, or frontmatter field.\n\n"
                "HEADING targets: use the heading text without '#', delimit nested headings with '::'. "
                "Example: 'My Section' or 'Parent::Child'. "
                "Use obsidian_get_document_map first to discover valid heading names.\n\n"
                "BLOCK targets: use the block reference ID without '^', e.g. '2d9b4a'.\n\n"
                "FRONTMATTER targets: use the field name, e.g. 'tags' or 'status'. "
                "For array fields (e.g. tags), set content_type to 'application/json' and provide a JSON array string.\n\n"
                "Set create_if_missing=true to create new frontmatter keys or headings that don't yet exist."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file (relative to vault root)", "format": "path"},
                    "operation": {"type": "string", "description": "Operation to perform", "enum": ["append", "prepend", "replace"]},
                    "target_type": {"type": "string", "description": "Type of target to patch", "enum": ["heading", "block", "frontmatter"]},
                    "target": {"type": "string", "description": "Target identifier. For headings: text without '#', nested with '::'. For blocks: ID without '^'. For frontmatter: field name."},
                    "content": {"type": "string", "description": "Content to insert. For JSON content_type, must be valid JSON (e.g. '[\"tag1\",\"tag2\"]')."},
                    "content_type": {
                        "type": "string",
                        "description": "Content-Type for the patch body. Use 'application/json' for frontmatter array fields.",
                        "enum": ["text/markdown", "application/json"],
                        "default": "text/markdown"
                    },
                    "create_if_missing": {
                        "type": "boolean",
                        "description": "Create the target if it does not exist (e.g. new frontmatter key or heading). Default false.",
                        "default": False
                    },
                    "apply_if_preexists": {
                        "type": "boolean",
                        "description": "Apply the patch even if content already exists in the target. Default true.",
                        "default": True
                    },
                    "trim_whitespace": {
                        "type": "boolean",
                        "description": "Trim whitespace from the target before applying the patch. Default false.",
                        "default": False
                    },
                },
                "required": ["filepath", "operation", "target_type", "target", "content"]
            }
        )

    def run_tool(self, args: dict):
        if not all(k in args for k in ["filepath", "operation", "target_type", "target", "content"]):
            raise RuntimeError("filepath, operation, target_type, target and content arguments required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.patch_content(
            filepath=args["filepath"],
            operation=args["operation"],
            target_type=args["target_type"],
            target=args["target"],
            content=args["content"],
            create_if_missing=args.get("create_if_missing", False),
            apply_if_preexists=args.get("apply_if_preexists", True),
            trim_whitespace=args.get("trim_whitespace", False),
            content_type=args.get("content_type", "text/markdown"),
        )
        return [TextContent(type="text", text=f"Successfully patched content in {args['filepath']}")]


class PutContentToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_put_content")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Create a new file in your vault or overwrite the full content of an existing one.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the relevant file (relative to your vault root)", "format": "path"},
                    "content": {"type": "string", "description": "Content of the file you would like to upload"}
                },
                "required": ["filepath", "content"]
            }
        )

    def run_tool(self, args: dict):
        if "filepath" not in args or "content" not in args:
            raise RuntimeError("filepath and content arguments required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.put_content(args["filepath"], args["content"])
        return [TextContent(type="text", text=f"Successfully uploaded content to {args['filepath']}")]


class DeleteFileToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_delete_file")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Delete a file or directory from the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file or directory to delete (relative to vault root)", "format": "path"},
                    "confirm": {"type": "boolean", "description": "Confirmation to delete the file (must be true)", "default": False}
                },
                "required": ["filepath", "confirm"]
            }
        )

    def run_tool(self, args: dict):
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")
        if not args.get("confirm", False):
            raise RuntimeError("confirm must be set to true to delete a file")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.delete_file(args["filepath"])
        return [TextContent(type="text", text=f"Successfully deleted {args['filepath']}")]

# ── Active file tools ──────────────────────────────────────────────────────

class GetActiveFileToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_active_file")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get the content of the currently open file in Obsidian.",
            inputSchema={
                "type": "object",
                "properties": {
                    "metadata": {
                        "type": "boolean",
                        "description": "If true, returns JSON with frontmatter, tags, stat and content. If false (default), returns raw markdown.",
                        "default": False
                    }
                },
                "required": []
            }
        )

    def run_tool(self, args: dict):
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        result = api.get_active_file(metadata=args.get("metadata", False))
        if isinstance(result, dict):
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        return [TextContent(type="text", text=result)]


class PutActiveFileToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_put_active_file")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Replace the entire content of the currently open file in Obsidian.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "New content for the file"}
                },
                "required": ["content"]
            }
        )

    def run_tool(self, args: dict):
        if "content" not in args:
            raise RuntimeError("content argument required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.put_active_file(args["content"])
        return [TextContent(type="text", text="Successfully replaced active file content")]


class AppendActiveFileToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_append_active_file")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Append content to the currently open file in Obsidian.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to append"}
                },
                "required": ["content"]
            }
        )

    def run_tool(self, args: dict):
        if "content" not in args:
            raise RuntimeError("content argument required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.append_active_file(args["content"])
        return [TextContent(type="text", text="Successfully appended to active file")]


class PatchActiveFileToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_patch_active_file")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "PATCH the currently open file in Obsidian. Same targeting rules as obsidian_patch_content: "
                "heading text without '#', block IDs without '^', frontmatter field names. "
                "Nested headings delimited by '::'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["append", "prepend", "replace"]},
                    "target_type": {"type": "string", "enum": ["heading", "block", "frontmatter"]},
                    "target": {"type": "string", "description": "Target identifier"},
                    "content": {"type": "string", "description": "Content to insert"},
                    "content_type": {"type": "string", "enum": ["text/markdown", "application/json"], "default": "text/markdown"},
                    "create_if_missing": {"type": "boolean", "default": False},
                    "apply_if_preexists": {"type": "boolean", "default": True},
                    "trim_whitespace": {"type": "boolean", "default": False},
                },
                "required": ["operation", "target_type", "target", "content"]
            }
        )

    def run_tool(self, args: dict):
        if not all(k in args for k in ["operation", "target_type", "target", "content"]):
            raise RuntimeError("operation, target_type, target and content arguments required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.patch_active_file(
            operation=args["operation"],
            target_type=args["target_type"],
            target=args["target"],
            content=args["content"],
            create_if_missing=args.get("create_if_missing", False),
            apply_if_preexists=args.get("apply_if_preexists", True),
            trim_whitespace=args.get("trim_whitespace", False),
            content_type=args.get("content_type", "text/markdown"),
        )
        return [TextContent(type="text", text="Successfully patched active file")]


class DeleteActiveFileToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_delete_active_file")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Delete the currently open file in Obsidian.",
            inputSchema={
                "type": "object",
                "properties": {
                    "confirm": {"type": "boolean", "description": "Must be true to confirm deletion", "default": False}
                },
                "required": ["confirm"]
            }
        )

    def run_tool(self, args: dict):
        if not args.get("confirm", False):
            raise RuntimeError("confirm must be set to true to delete the active file")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.delete_active_file()
        return [TextContent(type="text", text="Successfully deleted the active file")]

# ── Periodic note tools ────────────────────────────────────────────────────

class PeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get current periodic note for the specified period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]},
                    "type": {"type": "string", "default": "content", "enum": ["content", "metadata"]}
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict):
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_periodic_note(args["period"], args.get("type", "content"))
        return [TextContent(type="text", text=content)]


class CreatePeriodicNoteToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_create_periodic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Create the current periodic note for the specified period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]}
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict):
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.create_periodic_note(args["period"])
        return [TextContent(type="text", text=f"Successfully created {args['period']} periodic note")]


class GetPeriodicNoteForDateToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_note_for_date")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get a periodic note for a specific date. Date format depends on period type (e.g. '2025-01-15' for daily, '2025-W03' for weekly, '2025-01' for monthly).",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]},
                    "date": {"type": "string", "description": "Date string in appropriate format for the period"},
                    "type": {"type": "string", "default": "content", "enum": ["content", "metadata"]}
                },
                "required": ["period", "date"]
            }
        )

    def run_tool(self, args: dict):
        if "period" not in args or "date" not in args:
            raise RuntimeError("period and date arguments required")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_periodic_note_for_date(args["period"], args["date"], args.get("type", "content"))
        return [TextContent(type="text", text=content)]


class RecentPeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_periodic_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get most recent periodic notes for the specified period type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]},
                    "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                    "include_content": {"type": "boolean", "default": False}
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict):
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_periodic_notes(args["period"], args.get("limit", 5), args.get("include_content", False))
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

# ── Commands tools ─────────────────────────────────────────────────────────

class ListCommandsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_list_commands")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="List all available Obsidian commands that can be executed via the API.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        )

    def run_tool(self, args: dict):
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        commands = api.list_commands()
        return [TextContent(type="text", text=json.dumps(commands, indent=2))]


class ExecuteCommandToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_execute_command")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Execute an Obsidian command by its ID. Use obsidian_list_commands to discover available command IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {"type": "string", "description": "The ID of the command to execute (e.g. 'editor:toggle-bold')"}
                },
                "required": ["command_id"]
            }
        )

    def run_tool(self, args: dict):
        if "command_id" not in args:
            raise RuntimeError("command_id argument missing")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        api.execute_command(args["command_id"])
        return [TextContent(type="text", text=f"Successfully executed command: {args['command_id']}")]

# ── Search tools ───────────────────────────────────────────────────────────

class SearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_simple_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Simple search for documents matching a specified text query across all files in the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for in the vault."},
                    "context_length": {"type": "integer", "description": "How much context to return around the matching string (default: 100)", "default": 100}
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict):
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.search(args["query"], args.get("context_length", 100))
        formatted = []
        for result in results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                formatted_matches.append({'context': context, 'match_position': {'start': match_pos.get('start', 0), 'end': match_pos.get('end', 0)}})
            formatted.append({'filename': result.get('filename', ''), 'score': result.get('score', 0), 'matches': formatted_matches})
        return [TextContent(type="text", text=json.dumps(formatted, indent=2))]


class ComplexSearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_complex_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Complex search for documents using a JsonLogic query. "
                "Supports 'glob' and 'regexp' operators on {'var': 'path'}. "
                "NOTE: {'var': 'content'} is NOT supported by the underlying API — use obsidian_simple_search for content matching instead.\n\n"
                "Examples:\n"
                "1. All markdown files: {\"glob\": [\"*.md\", {\"var\": \"path\"}]}\n"
                "2. Markdown files in Work folder: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*Work.*\", {\"var\": \"path\"}]}]}"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "description": "JsonLogic query. Only {\"var\": \"path\"} is supported as a variable — content-based JsonLogic is not supported."
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict):
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.search_json(args["query"])
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

# ── Recent changes tool ────────────────────────────────────────────────────

class RecentChangesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_changes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Get recently modified markdown files in the vault, sorted by modification time (newest first). "
                "Returns path, modification time, size, and tags for each file."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of files to return (default: 10)", "default": 10, "minimum": 1, "maximum": 100},
                    "days": {"type": "integer", "description": "Only include files modified within this many days (default: 90)", "minimum": 1, "default": 90}
                }
            }
        )

    def run_tool(self, args: dict):
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
        days = args.get("days", 90)
        if not isinstance(days, int) or days < 1:
            raise RuntimeError(f"Invalid days: {days}. Must be a positive integer")
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_changes(limit, days)
        return [TextContent(type="text", text=json.dumps(results, indent=2))]
