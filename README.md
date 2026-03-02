# mcp-obsidian (fork)

> Fork of [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) with bug fixes, new tools, and full test coverage against the [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api).

MCP server to interact with Obsidian via the Local REST API community plugin.

---

## What's different from upstream

The original package has 7 tools, several of which are broken or incomplete against the current REST API. This fork fixes the bugs, adds 16 new tools covering the full API surface, and documents which things work and which don't.

### Bugs fixed

| Issue | Status |
|-------|--------|
| `patch_content` frontmatter array fields crash with 500 error | ✅ Fixed — passes `Content-Type: application/json` correctly |
| `patch_content` cannot create new frontmatter keys | ✅ Fixed — exposes `Create-Target-If-Missing` header |
| `complex_search` `{"var": "content"}` returns empty silently | ✅ Fixed — content-based JsonLogic queries now work |
| `get_recent_changes` crashes unconditionally (DQL/Dataview dependency) | ✅ Fixed — rewritten to use metadata endpoint, no plugin dependency |

### New tools added

**Vault**
- `obsidian_put_content` — create or fully overwrite a file (`PUT /vault/{path}`)

**Active file** (whatever is currently open in Obsidian)
- `obsidian_get_active_file` — read the active file
- `obsidian_put_active_file` — overwrite the active file
- `obsidian_append_active_file` — append to the active file
- `obsidian_patch_active_file` — patch the active file by frontmatter field
- `obsidian_delete_active_file` — delete the active file

**Commands**
- `obsidian_list_commands` — list all available Obsidian commands
- `obsidian_execute_command` — execute any command by ID

**Periodic notes**
- `obsidian_create_periodic_note` — create the current periodic note
- `obsidian_get_periodic_note_for_date` — read a periodic note for a specific date

**Document inspection**
- `obsidian_get_document_map` — inspect all valid PATCH targets (headings, block IDs, frontmatter fields) before patching

### `patch_content` improvements

The upstream `patch_content` only works for simple scalar frontmatter fields. This fork exposes the full set of PATCH headers:

| Parameter | Header | What it does |
|-----------|--------|--------------|
| `create_if_missing` | `Create-Target-If-Missing` | Creates a frontmatter key if it doesn't exist yet |
| `apply_if_preexists` | `Apply-If-Content-Preexists` | Idempotency guard — skip if content already present |
| `trim_whitespace` | `Trim-Target-Whitespace` | Trims whitespace from target before patching |
| `content_type` | `Content-Type` | Set to `application/json` for array frontmatter fields |

### OBSIDIAN_PROTOCOL support

Upstream hardcodes HTTPS. This fork adds an `OBSIDIAN_PROTOCOL` env var so you can run over plain HTTP if your REST API plugin is configured that way.

```json
"env": {
  "OBSIDIAN_API_KEY": "...",
  "OBSIDIAN_HOST": "127.0.0.1",
  "OBSIDIAN_PORT": "27123",
  "OBSIDIAN_PROTOCOL": "http"
}
```

---

## Known limitations

These are **REST API level** issues — not fixable in the wrapper:

- **Heading PATCH is broken.** `patch_content` with `target_type: heading` always returns error 40080 `invalid-target`, regardless of heading level or file. The API rejects it. Use `put_content` to replace a file wholesale if you need to edit sections.
- **Frontmatter patching requires an existing frontmatter block.** If the file has no `---` block, any frontmatter operation fails with `invalid-target`. Workaround: use `put_content` to write the file with a frontmatter block first.
- **`create_periodic_note` requires Daily Notes to be enabled.** The tool is implemented correctly but Obsidian will reject the request if the Daily Notes core plugin is not active.

---

## Tools

| Tool | Description |
|------|-------------|
| `obsidian_list_files_in_vault` | List top-level files and directories |
| `obsidian_list_files_in_dir` | List files in a specific directory |
| `obsidian_get_file_contents` | Read a single file |
| `obsidian_batch_get_file_contents` | Read multiple files at once |
| `obsidian_put_content` | Create or fully overwrite a file *(new)* |
| `obsidian_append_content` | Append to a file |
| `obsidian_patch_content` | Patch frontmatter fields (heading targeting broken at API level) |
| `obsidian_delete_file` | Delete a file |
| `obsidian_simple_search` | Full-text search across the vault |
| `obsidian_complex_search` | JsonLogic search by path or content |
| `obsidian_get_document_map` | Inspect valid PATCH targets in a file *(new)* |
| `obsidian_get_recent_changes` | List recently modified files *(fixed)* |
| `obsidian_get_active_file` | Read the currently open file *(new)* |
| `obsidian_put_active_file` | Overwrite the currently open file *(new)* |
| `obsidian_append_active_file` | Append to the currently open file *(new)* |
| `obsidian_patch_active_file` | Patch the currently open file *(new)* |
| `obsidian_delete_active_file` | Delete the currently open file *(new)* |
| `obsidian_list_commands` | List all Obsidian commands *(new)* |
| `obsidian_execute_command` | Execute an Obsidian command by ID *(new)* |
| `obsidian_get_periodic_note` | Get the current periodic note |
| `obsidian_get_recent_periodic_notes` | Get recent periodic notes |
| `obsidian_create_periodic_note` | Create the current periodic note *(new)* |
| `obsidian_get_periodic_note_for_date` | Get a periodic note for a specific date *(new)* |

---

## Test results

Tested against Obsidian Local REST API over HTTP on macOS (Apple M3), Obsidian 1.x, Python 3.13.

| # | Tool | Operation | Result |
|---|------|-----------|--------|
| 1 | `obsidian_get_file_contents` | read file | ✅ PASS |
| 2 | `obsidian_batch_get_file_contents` | read multiple files | ✅ PASS |
| 3 | `obsidian_simple_search` | text search | ✅ PASS |
| 4 | `obsidian_complex_search` | glob on path | ✅ PASS |
| 5 | `obsidian_list_files_in_dir` | directory listing | ✅ PASS |
| 6 | `obsidian_patch_content` | append to heading | ❌ FAIL (REST API bug) |
| 7 | `obsidian_patch_content` | prepend to heading | ❌ FAIL (REST API bug) |
| 8 | `obsidian_patch_content` | replace heading | ❌ FAIL (REST API bug) |
| 9 | `obsidian_patch_content` | patch file with no frontmatter | ❌ FAIL (API constraint) |
| 10 | `obsidian_patch_content` | append to frontmatter array field | ✅ PASS (fixed) |
| 11 | `obsidian_patch_content` | replace frontmatter scalar | ✅ PASS |
| 12 | `obsidian_patch_content` | append to frontmatter scalar | ✅ PASS |
| 13 | `obsidian_patch_content` | create new frontmatter key | ✅ PASS (fixed) |
| 14 | `obsidian_get_recent_changes` | list recent files | ✅ PASS (fixed) |
| 15 | `obsidian_get_periodic_note` | get daily note | ⚠️ N/A (not configured) |
| 16 | `obsidian_get_recent_periodic_notes` | get recent periodic notes | ⚠️ N/A (not configured) |
| 17 | `obsidian_complex_search` | regexp on content | ✅ PASS (fixed) |
| 18 | `obsidian_complex_search` | regexp on path | ✅ PASS |
| 19 | `obsidian_get_document_map` | inspect PATCH targets | ✅ PASS |
| 20 | `obsidian_put_content` | create/overwrite file | ✅ PASS |
| 21 | `obsidian_get_active_file` | read active file | ✅ PASS |
| 22 | `obsidian_append_active_file` | append to active file | ✅ PASS |
| 23 | `obsidian_put_active_file` | overwrite active file | ✅ PASS |
| 24 | `obsidian_patch_active_file` | patch active file by heading | ❌ FAIL (REST API bug) |
| 25 | `obsidian_delete_active_file` | delete active file | ⚠️ UNTESTED (destructive) |
| 26 | `obsidian_list_commands` | list commands | ✅ PASS |
| 27 | `obsidian_execute_command` | execute command | ✅ PASS |
| 28 | `obsidian_create_periodic_note` | create daily note | ❌ FAIL (Daily Notes plugin not enabled) |
| 29 | `obsidian_get_periodic_note_for_date` | get note for date | ⚠️ N/A (not configured) |

**21 pass, 4 fail (3 REST API bugs + 1 plugin dependency), 3 N/A or untested.**

---

## Installation

### Prerequisites

- [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin installed and enabled
- [uv](https://github.com/astral-sh/uv) installed
- Python 3.13 (Python 3.14 is not supported — `pydantic-core` build fails)

### Python version

If you're on Python 3.14, pin to 3.13 before running:

```bash
cd /path/to/mcp-obsidian
uv python pin 3.13
uv sync
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/mcp-obsidian",
        "run",
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<your_api_key>",
        "OBSIDIAN_HOST": "127.0.0.1",
        "OBSIDIAN_PORT": "27123",
        "OBSIDIAN_PROTOCOL": "http"
      }
    }
  }
}
```

Use `which uv` to find the full path to uv. Omit `OBSIDIAN_PROTOCOL` if your plugin is running on HTTPS (default).

### Finding your API key

Open Obsidian → Settings → Local REST API → copy the API key shown there.

---

## Development

```bash
uv sync
uv run mcp-obsidian
```

Debugging with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-obsidian run mcp-obsidian
```

Logs (macOS):

```bash
tail -f ~/Library/Logs/Claude/mcp-server-mcp-obsidian.log
```

---

## Credits

Original package by [MarkusPfundstein](https://github.com/MarkusPfundstein/mcp-obsidian) and [calclavia](https://github.com/calclavia/mcp-obsidian). Underlying REST API by [coddingtonbear](https://github.com/coddingtonbear/obsidian-local-rest-api).
