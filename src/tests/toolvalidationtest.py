from conftest import nc
 
 
def get_tool(name):
    return next(t for t in nc.get_all_tools() if t.name == name)
 
 
def test_missing_required_field():
    error = nc.validate_tool_args(get_tool("read_file"), {})
    assert "path" in error
 
 
def test_wrong_type_is_rejected():
    error = nc.validate_tool_args(
        get_tool("write_file"), {"path": "x.txt", "content": 123}
    )
    assert "content" in error
    assert "string" in error
 
 
def test_valid_simple_args_pass():
    assert nc.validate_tool_args(get_tool("bash"), {"command": "ls"}) is None
 
 
def test_valid_nested_array_of_objects_passes():
    error = nc.validate_tool_args(
        get_tool("todo_write"),
        {"items": [{"content": "do x", "status": "pending"}]},
    )
    assert error is None
 
 
def test_nested_enum_violation_is_rejected():
    error = nc.validate_tool_args(
        get_tool("todo_write"),
        {"items": [{"content": "do x", "status": "kinda_done"}]},
    )
    assert "status" in error
    assert "kinda_done" in error
 
 
def test_nested_missing_required_field_is_rejected():
    error = nc.validate_tool_args(
        get_tool("todo_write"), {"items": [{"status": "pending"}]}
    )
    assert "content" in error
 
 
def test_bool_does_not_satisfy_string_type():
    # bool is a subclass of int in Python; make sure that quirk doesn't
    # let a boolean sneak past a schema that declares "string".
    error = nc.validate_tool_args(get_tool("grep"), {"pattern": "x", "path": True})
    assert error is not None
    assert "path" in error
 
 
def test_extra_unrecognized_fields_are_ignored():
    # The validator checks declared properties; it shouldn't choke on
    # extra fields a model might add.
    error = nc.validate_tool_args(
        get_tool("bash"), {"command": "ls", "extra_field": "whatever"}
    )
    assert error is None