import subprocess
 
import pytest
 
from conftest import nc
 
 
# --- ReadFileTool -----------------------------------------------------
 
def test_read_file_returns_content(workspace):
    (workspace / "hello.txt").write_text("hello world")
    result = nc.ReadFileTool().execute({"path": "hello.txt"})
    assert result == "hello world"
 
 
def test_read_file_missing_file(workspace):
    result = nc.ReadFileTool().execute({"path": "nope.txt"})
    assert "not found" in result.lower()
 
 
def test_read_file_blocked_outside_workspace(workspace, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_text("top secret")
    result = nc.ReadFileTool().execute({"path": str(outside)})
    assert "outside the workspace" in result
 
 
# --- WriteFileTool ------------------------------------------------------
 
def test_write_file_creates_file(workspace):
    result = nc.WriteFileTool().execute({"path": "new.txt", "content": "hi"})
    assert result == "Wrote new.txt"
    assert (workspace / "new.txt").read_text() == "hi"
 
 
def test_write_file_overwrites_existing(workspace):
    (workspace / "a.txt").write_text("old")
    nc.WriteFileTool().execute({"path": "a.txt", "content": "new"})
    assert (workspace / "a.txt").read_text() == "new"
 
 
def test_write_file_blocked_outside_workspace(workspace, tmp_path_factory):
    outside_dir = tmp_path_factory.mktemp("outside")
    target = outside_dir / "pwned.txt"
    result = nc.WriteFileTool().execute({"path": str(target), "content": "oops"})
    assert "outside the workspace" in result
    assert not target.exists()
 
 
# --- EditFileTool ---------------------------------------------------------
 
def test_edit_file_replaces_text(workspace):
    (workspace / "app.py").write_text("def foo():\n    return 1\n")
    result = nc.EditFileTool().execute({
        "path": "app.py",
        "old_string": "return 1",
        "new_string": "return 2",
    })
    assert result == "Edited app.py"
    assert (workspace / "app.py").read_text() == "def foo():\n    return 2\n"
 
 
def test_edit_file_old_string_not_found(workspace):
    (workspace / "app.py").write_text("def foo():\n    return 1\n")
    result = nc.EditFileTool().execute({
        "path": "app.py",
        "old_string": "does not exist",
        "new_string": "x",
    })
    assert "old_string not found" in result
    # File must be left untouched.
    assert (workspace / "app.py").read_text() == "def foo():\n    return 1\n"
 
 
def test_edit_file_missing_file(workspace):
    result = nc.EditFileTool().execute({
        "path": "ghost.py", "old_string": "a", "new_string": "b",
    })
    assert "not found" in result.lower()
 
 
def test_edit_file_blocked_outside_workspace(workspace, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_text("secret")
    result = nc.EditFileTool().execute({
        "path": str(outside), "old_string": "secret", "new_string": "HACKED",
    })
    assert "outside the workspace" in result
    assert outside.read_text() == "secret"
 
 
# --- GrepTool -------------------------------------------------------------
 
def test_grep_finds_matches_with_line_numbers(workspace):
    (workspace / "a.txt").write_text("foo\nbar\nfoobar\n")
    result = nc.GrepTool().execute({"pattern": "foo", "path": "."})
    assert "a.txt:1: foo" in result
    assert "a.txt:3: foobar" in result
    assert "bar\n" not in result.split("a.txt:1")[0]  # sanity: line 2 alone isn't a match
 
 
def test_grep_no_matches(workspace):
    (workspace / "a.txt").write_text("nothing relevant here")
    result = nc.GrepTool().execute({"pattern": "zzz", "path": "."})
    assert result == "No matches found."
 
 
def test_grep_invalid_regex(workspace):
    result = nc.GrepTool().execute({"pattern": "(unclosed", "path": "."})
    assert "Invalid regex" in result
 
 
def test_grep_skips_undecodable_files(workspace):
    (workspace / "binary.dat").write_bytes(b"\xff\xfe\x00\x01binary")
    (workspace / "text.txt").write_text("findme")
    result = nc.GrepTool().execute({"pattern": "findme", "path": "."})
    assert "text.txt:1: findme" in result  # doesn't crash on the binary file
 
 
def test_grep_blocked_outside_workspace(workspace, tmp_path_factory):
    outside_dir = tmp_path_factory.mktemp("outside")
    (outside_dir / "a.txt").write_text("secret")
    result = nc.GrepTool().execute({"pattern": "secret", "path": str(outside_dir)})
    assert "outside the workspace" in result
 
 
# --- BashTool ---------------------------------------------------------
 
def test_bash_captures_stdout(workspace):
    result = nc.BashTool().execute({"command": "echo hello"})
    assert "hello" in result
 
 
def test_bash_runs_with_workspace_as_cwd(workspace):
    result = nc.BashTool().execute({"command": "pwd"})
    assert result.strip() == str(workspace)
 
 
def test_bash_timeout(workspace, monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="sleep 999", timeout=30)
 
    monkeypatch.setattr(nc.subprocess, "run", fake_run)
    result = nc.BashTool().execute({"command": "sleep 999"})
    assert "timed out" in result.lower()
 
 
# --- TodoWriteTool ------------------------------------------------------
 
def test_todo_write_formats_checklist():
    tool = nc.TodoWriteTool()
    result = tool.execute({"items": [
        {"content": "write tests", "status": "in_progress"},
        {"content": "ship it", "status": "pending"},
        {"content": "set up ci", "status": "done"},
    ]})
    assert result == "[~] write tests\n[ ] ship it\n[x] set up ci"
    assert tool.items[0]["content"] == "write tests"
 
 
# --- WebFetchTool (network mocked) --------------------------------------
 
class _FakeResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status
 
    def raise_for_status(self):
        if self.status_code >= 400:
            raise nc.requests.HTTPError(f"status {self.status_code}")
 
    def json(self):
        return self._json
 
 
def test_web_fetch_returns_markdown(monkeypatch):
    monkeypatch.setattr(
        nc.requests, "post",
        lambda *a, **k: _FakeResponse({"data": {"markdown": "# Hello"}}),
    )
    result = nc.WebFetchTool().execute({"url": "https://example.com"})
    assert result == "# Hello"
 
 
def test_web_fetch_truncates_long_content(monkeypatch):
    long_markdown = "x" * (nc.MAX_WEB_CONTENT_LENGTH + 500)
    monkeypatch.setattr(
        nc.requests, "post",
        lambda *a, **k: _FakeResponse({"data": {"markdown": long_markdown}}),
    )
    result = nc.WebFetchTool().execute({"url": "https://example.com"})
    assert len(result) == nc.MAX_WEB_CONTENT_LENGTH
 
 
def test_web_fetch_handles_request_exception(monkeypatch):
    def raise_error(*a, **k):
        raise nc.requests.RequestException("boom")
 
    monkeypatch.setattr(nc.requests, "post", raise_error)
    result = nc.WebFetchTool().execute({"url": "https://example.com"})
    assert "Error fetching URL" in result
 
 
def test_web_fetch_handles_malformed_response(monkeypatch):
    monkeypatch.setattr(
        nc.requests, "post", lambda *a, **k: _FakeResponse({"data": {}}),
    )
    result = nc.WebFetchTool().execute({"url": "https://example.com"})
    assert "Error parsing response" in result
 
 
# --- WebSearchTool (network mocked) --------------------------------------
 
def test_web_search_formats_results(monkeypatch):
    monkeypatch.setattr(
        nc.requests, "post",
        lambda *a, **k: _FakeResponse({"data": {"web": [
            {"title": "Result A", "url": "https://a.example", "description": "desc a"},
            {"title": "Result B", "url": "https://b.example", "description": "desc b"},
        ]}}),
    )
    result = nc.WebSearchTool().execute({"query": "test query"})
    assert "Result A" in result and "https://a.example" in result
    assert "Result B" in result and "https://b.example" in result
 
 
def test_web_search_handles_request_exception(monkeypatch):
    def raise_error(*a, **k):
        raise nc.requests.RequestException("boom")
 
    monkeypatch.setattr(nc.requests, "post", raise_error)
    result = nc.WebSearchTool().execute({"query": "test query"})
    assert "Error searching web" in result