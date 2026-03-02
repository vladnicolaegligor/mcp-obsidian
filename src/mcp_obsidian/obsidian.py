# obsidian.py
import requests
import urllib.parse
import json
import os
from datetime import datetime, timedelta
from typing import Any

class Obsidian():
    def __init__(
            self, 
            api_key: str,
            protocol: str = os.getenv('OBSIDIAN_PROTOCOL', 'https').lower(),
            host: str = str(os.getenv('OBSIDIAN_HOST', '127.0.0.1')),
            port: int = int(os.getenv('OBSIDIAN_PORT', '27124')),
            verify_ssl: bool = False,
        ):
        self.api_key = api_key
        self.protocol = 'http' if protocol == 'http' else 'https'
        self.host = host
        self.port = port
        self.verify_ssl = verify_ssl
        self.timeout = (3, 6)

    def get_base_url(self) -> str:
        return f'{self.protocol}://{self.host}:{self.port}'
    
    def _get_headers(self) -> dict:
        return {'Authorization': f'Bearer {self.api_key}'}

    def _safe_call(self, f) -> Any:
        try:
            return f()
        except requests.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            code = error_data.get('errorCode', -1) 
            message = error_data.get('message', '<unknown>')
            raise Exception(f"Error {code}: {message}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    # ── Vault file operations ──────────────────────────────────────────────

    def list_files_in_vault(self) -> Any:
        url = f"{self.get_base_url()}/vault/"
        def call_fn():
            r = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()['files']
        return self._safe_call(call_fn)

    def list_files_in_dir(self, dirpath: str) -> Any:
        url = f"{self.get_base_url()}/vault/{dirpath}/"
        def call_fn():
            r = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()['files']
        return self._safe_call(call_fn)

    def get_file_contents(self, filepath: str) -> Any:
        url = f"{self.get_base_url()}/vault/{filepath}"
        def call_fn():
            r = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.text
        return self._safe_call(call_fn)

    def get_file_metadata(self, filepath: str) -> Any:
        """Get file metadata (frontmatter, tags, stat) as JSON."""
        url = f"{self.get_base_url()}/vault/{filepath}"
        def call_fn():
            headers = self._get_headers() | {'Accept': 'application/vnd.olrapi.note+json'}
            r = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        return self._safe_call(call_fn)

    def get_document_map(self, filepath: str) -> Any:
        """Return all available PATCH targets (headings, blocks, frontmatter) for a file."""
        url = f"{self.get_base_url()}/vault/{filepath}"
        def call_fn():
            headers = self._get_headers() | {'Accept': 'application/vnd.olrapi.document-map+json'}
            r = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        return self._safe_call(call_fn)

    def get_batch_file_contents(self, filepaths: list[str]) -> str:
        result = []
        for filepath in filepaths:
            try:
                content = self.get_file_contents(filepath)
                result.append(f"# {filepath}\n\n{content}\n\n---\n\n")
            except Exception as e:
                result.append(f"# {filepath}\n\nError reading file: {str(e)}\n\n---\n\n")
        return "".join(result)

    def append_content(self, filepath: str, content: str) -> Any:
        url = f"{self.get_base_url()}/vault/{filepath}"
        def call_fn():
            r = requests.post(
                url,
                headers=self._get_headers() | {'Content-Type': 'text/markdown'},
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def patch_content(
        self,
        filepath: str,
        operation: str,
        target_type: str,
        target: str,
        content: str,
        create_if_missing: bool = False,
        apply_if_preexists: bool = True,
        trim_whitespace: bool = False,
        content_type: str = "text/markdown",
    ) -> Any:
        """
        PATCH a file using the V3 API.

        For heading targets the Target must be the heading text without '#',
        using '::' to delimit nested headings, e.g. 'Parent::Child'.

        For frontmatter array fields pass content_type='application/json'
        and a JSON string as content, e.g. '["tag1","tag2"]'.

        Set create_if_missing=True to create new frontmatter keys or headings.
        """
        url = f"{self.get_base_url()}/vault/{filepath}"
        headers = self._get_headers() | {
            'Content-Type': content_type,
            'Operation': operation,
            'Target-Type': target_type,
            'Target': urllib.parse.quote(target, safe=''),
            'Create-Target-If-Missing': 'true' if create_if_missing else 'false',
            'Apply-If-Content-Preexists': 'true' if apply_if_preexists else 'false',
            'Trim-Target-Whitespace': 'true' if trim_whitespace else 'false',
        }
        body = content.encode('utf-8') if isinstance(content, str) else content

        def call_fn():
            r = requests.patch(url, headers=headers, data=body, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def put_content(self, filepath: str, content: str) -> Any:
        url = f"{self.get_base_url()}/vault/{filepath}"
        def call_fn():
            r = requests.put(
                url,
                headers=self._get_headers() | {'Content-Type': 'text/markdown'},
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def delete_file(self, filepath: str) -> Any:
        url = f"{self.get_base_url()}/vault/{filepath}"
        def call_fn():
            r = requests.delete(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    # ── Active file operations ─────────────────────────────────────────────

    def get_active_file(self, metadata: bool = False) -> Any:
        """Get the currently open file in Obsidian."""
        url = f"{self.get_base_url()}/active/"
        def call_fn():
            headers = self._get_headers()
            if metadata:
                headers['Accept'] = 'application/vnd.olrapi.note+json'
            r = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json() if metadata else r.text
        return self._safe_call(call_fn)

    def put_active_file(self, content: str) -> Any:
        """Replace the content of the currently open file."""
        url = f"{self.get_base_url()}/active/"
        def call_fn():
            r = requests.put(
                url,
                headers=self._get_headers() | {'Content-Type': 'text/markdown'},
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def append_active_file(self, content: str) -> Any:
        """Append content to the currently open file."""
        url = f"{self.get_base_url()}/active/"
        def call_fn():
            r = requests.post(
                url,
                headers=self._get_headers() | {'Content-Type': 'text/markdown'},
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def patch_active_file(
        self,
        operation: str,
        target_type: str,
        target: str,
        content: str,
        create_if_missing: bool = False,
        apply_if_preexists: bool = True,
        trim_whitespace: bool = False,
        content_type: str = "text/markdown",
    ) -> Any:
        """PATCH the currently open file."""
        url = f"{self.get_base_url()}/active/"
        headers = self._get_headers() | {
            'Content-Type': content_type,
            'Operation': operation,
            'Target-Type': target_type,
            'Target': urllib.parse.quote(target, safe=''),
            'Create-Target-If-Missing': 'true' if create_if_missing else 'false',
            'Apply-If-Content-Preexists': 'true' if apply_if_preexists else 'false',
            'Trim-Target-Whitespace': 'true' if trim_whitespace else 'false',
        }
        body = content.encode('utf-8') if isinstance(content, str) else content
        def call_fn():
            r = requests.patch(url, headers=headers, data=body, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def delete_active_file(self) -> Any:
        """Delete the currently open file."""
        url = f"{self.get_base_url()}/active/"
        def call_fn():
            r = requests.delete(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    # ── Periodic notes ─────────────────────────────────────────────────────

    def get_periodic_note(self, period: str, type: str = "content") -> Any:
        url = f"{self.get_base_url()}/periodic/{period}/"
        def call_fn():
            headers = self._get_headers()
            if type == "metadata":
                headers['Accept'] = 'application/vnd.olrapi.note+json'
            r = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.text
        return self._safe_call(call_fn)

    def create_periodic_note(self, period: str) -> Any:
        """Create the current periodic note for the given period."""
        url = f"{self.get_base_url()}/periodic/{period}/"
        def call_fn():
            r = requests.post(url, headers=self._get_headers() | {'Content-Type': 'text/markdown'}, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def get_periodic_note_for_date(self, period: str, date: str, type: str = "content") -> Any:
        """Get a periodic note for a specific date."""
        url = f"{self.get_base_url()}/periodic/{period}/{date}/"
        def call_fn():
            headers = self._get_headers()
            if type == "metadata":
                headers['Accept'] = 'application/vnd.olrapi.note+json'
            r = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.text
        return self._safe_call(call_fn)

    def create_periodic_note_for_date(self, period: str, date: str) -> Any:
        """Create a periodic note for a specific date."""
        url = f"{self.get_base_url()}/periodic/{period}/{date}/"
        def call_fn():
            r = requests.post(url, headers=self._get_headers() | {'Content-Type': 'text/markdown'}, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    def get_recent_periodic_notes(self, period: str, limit: int = 5, include_content: bool = False) -> Any:
        url = f"{self.get_base_url()}/periodic/{period}/recent"
        params = {"limit": limit, "includeContent": include_content}
        def call_fn():
            r = requests.get(url, headers=self._get_headers(), params=params, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        return self._safe_call(call_fn)

    # ── Commands ───────────────────────────────────────────────────────────

    def list_commands(self) -> Any:
        """List all available Obsidian commands."""
        url = f"{self.get_base_url()}/commands/"
        def call_fn():
            r = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        return self._safe_call(call_fn)

    def execute_command(self, command_id: str) -> Any:
        """Execute an Obsidian command by its ID."""
        url = f"{self.get_base_url()}/commands/{command_id}/"
        def call_fn():
            r = requests.post(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return None
        return self._safe_call(call_fn)

    # ── Search ─────────────────────────────────────────────────────────────

    def search(self, query: str, context_length: int = 100) -> Any:
        url = f"{self.get_base_url()}/search/simple/"
        params = {'query': query, 'contextLength': context_length}
        def call_fn():
            r = requests.post(url, headers=self._get_headers(), params=params, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        return self._safe_call(call_fn)

    def search_json(self, query: dict) -> Any:
        url = f"{self.get_base_url()}/search/"
        headers = self._get_headers() | {'Content-Type': 'application/vnd.olrapi.jsonlogic+json'}
        def call_fn():
            r = requests.post(url, headers=headers, json=query, verify=self.verify_ssl, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        return self._safe_call(call_fn)

    def _list_all_files_recursive(self, dirpath: str = "") -> list:
        """Recursively list all files in the vault, returning full relative paths."""
        url = f"{self.get_base_url()}/vault/{dirpath}/" if dirpath else f"{self.get_base_url()}/vault/"
        r = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        entries = r.json().get('files', [])
        all_files = []
        for entry in entries:
            full = f"{dirpath}/{entry}".lstrip('/') if dirpath else entry
            if entry.endswith('/'):
                # It's a directory — recurse without the trailing slash
                all_files.extend(self._list_all_files_recursive(full.rstrip('/')))
            else:
                all_files.append(full)
        return all_files

    def get_recent_changes(self, limit: int = 10, days: int = 90) -> Any:
        """
        Get recently modified files in the vault.

        Uses vault listing + metadata endpoint to get mtime.
        Does NOT require the Dataview plugin (previous DQL approach crashed with 40070).
        """
        try:
            all_files = self._list_all_files_recursive()
        except Exception as e:
            raise Exception(f"Could not list vault files: {str(e)}")

        cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()  # seconds
        results = []
        errors = []

        for filepath in all_files:
            if not str(filepath).endswith('.md'):
                continue
            try:
                # URL-encode the filepath to handle spaces and special chars
                encoded = urllib.parse.quote(str(filepath), safe='/')
                url = f"{self.get_base_url()}/vault/{encoded}"
                headers = self._get_headers() | {'Accept': 'application/vnd.olrapi.note+json'}
                r = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
                r.raise_for_status()
                meta = r.json()
                mtime_raw = meta.get('stat', {}).get('mtime', 0)
                # API returns ms (values > 1e10) — normalise to seconds
                mtime_s = mtime_raw / 1000 if mtime_raw > 1e10 else mtime_raw
                if mtime_s >= cutoff_ts:
                    results.append({
                        'path': filepath,
                        'mtime': mtime_raw,
                        'mtime_human': datetime.fromtimestamp(mtime_s).strftime('%Y-%m-%d %H:%M:%S'),
                        'size': meta.get('stat', {}).get('size', 0),
                        'tags': meta.get('tags', []),
                    })
            except Exception as e:
                errors.append({'path': filepath, 'error': str(e)})
                continue

        results.sort(key=lambda x: x['mtime'], reverse=True)
        out = results[:limit]
        if not out and errors:
            raise Exception(f"No results. {len(errors)} files failed. First error: {errors[0]}")
        return out
