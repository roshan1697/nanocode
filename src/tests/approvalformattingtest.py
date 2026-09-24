from conftest import nc
 
 
def get_tool(name):
    return next(t for t in nc.get_all_tools() if t.name == name)
 
 
def test_write_file_preview_shows_line_and_byte_count():
    content = "\n".join(f"line {i}" for i in range(15))
    preview = nc._format_tool_call_for_approval(
        get_tool("write_file"), {"path": "app.py", "content": content}
    )
    assert "app.py" in preview
    assert "15 lines" in preview
    assert f"{len(content)} bytes" in preview
 
 
def test_write_file_preview_truncates_long_content():
    content = "\n".join(f"line {i}" for i in range(15))
    preview = nc._format_tool_call_for_approval(
        get_tool("write_file"), {"path": "app.py", "content": content}
    )
    assert "line 0" in preview
    assert "line 9" in preview
    assert "line 14" not in preview  # beyond the 10-line preview window
    assert "5 more lines" in preview
 
 
def test_write_file_short_content_not_truncated():
    preview = nc._format_tool_call_for_approval(
        get_tool("write_file"), {"path": "x.txt", "content": "one\ntwo"}
    )
    assert "more lines" not in preview
 
 
def test_edit_file_shows_unified_diff():
    preview = nc._format_tool_call_for_approval(
        get_tool("edit_file"),
        {"path": "app.py", "old_string": "return 1", "new_string": "return 2"},
    )
    assert "app.py" in preview
    assert "-return 1" in preview
    assert "+return 2" in preview
 
 
def test_edit_file_no_visible_changes():
    preview = nc._format_tool_call_for_approval(
        get_tool("edit_file"),
        {"path": "app.py", "old_string": "same", "new_string": "same"},
    )
    assert "no visible changes" in preview
 
 
def test_bash_shows_raw_command():
    preview = nc._format_tool_call_for_approval(
        get_tool("bash"), {"command": "rm -rf build/"}
    )
    assert preview == "bash: rm -rf build/"
 
 
def test_task_shows_description_and_prompt():
    preview = nc._format_tool_call_for_approval(
        get_tool("task"),
        {"description": "refactor auth", "prompt": "Refactor the auth module."},
    )
    assert "refactor auth" in preview
    assert "Refactor the auth module." in preview
 
 
def test_unknown_tool_falls_back_to_json():
    preview = nc._format_tool_call_for_approval(
        get_tool("grep"), {"pattern": "foo", "path": "."}
    )
    assert "grep" in preview
    assert "foo" in preview