from conftest import nc
 
 
class FakeFunctionDelta:
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments
 
 
class FakeToolCallDelta:
    def __init__(self, index, id=None, name=None, arguments=None):
        self.index = index
        self.id = id
        self.function = FakeFunctionDelta(name=name, arguments=arguments)
 
 
class FakeDelta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
 
 
class FakeChoice:
    def __init__(self, delta, finish_reason=None):
        self.delta = delta
        self.finish_reason = finish_reason
 
 
class FakeChunk:
    def __init__(self, choice):
        self.choices = [choice]
 
 
def chunk(content=None, tool_calls=None, finish_reason=None):
    return FakeChunk(FakeChoice(FakeDelta(content=content, tool_calls=tool_calls), finish_reason))
 
 
def test_plain_text_reply_no_tool_calls():
    stream = [
        chunk(content="Hello"),
        chunk(content=", world!"),
        chunk(finish_reason="stop"),
    ]
    reply, tool_calls, finish_reason = nc.parse_tool_calls(stream)
    assert reply == "Hello, world!"
    assert tool_calls == []
    assert finish_reason == "stop"
 
 
def test_single_tool_call_assembled_across_chunks():
    stream = [
        chunk(tool_calls=[FakeToolCallDelta(index=0, id="call_1", name="read_file", arguments='{"pa')]),
        chunk(tool_calls=[FakeToolCallDelta(index=0, arguments='th": ')]),
        chunk(tool_calls=[FakeToolCallDelta(index=0, arguments='"app.py"}')]),
        chunk(finish_reason="tool_calls"),
    ]
    reply, tool_calls, finish_reason = nc.parse_tool_calls(stream)
    assert reply == ""
    assert len(tool_calls) == 1
    call = tool_calls[0]
    assert call.id == "call_1"
    assert call.name == "read_file"
    assert call.arguments == '{"path": "app.py"}'
    assert finish_reason == "tool_calls"
 
 
def test_multiple_interleaved_tool_calls_assembled_independently():
    stream = [
        chunk(tool_calls=[FakeToolCallDelta(index=0, id="call_0", name="read_file", arguments="")]),
        chunk(tool_calls=[FakeToolCallDelta(index=1, id="call_1", name="bash", arguments="")]),
        chunk(tool_calls=[FakeToolCallDelta(index=0, arguments='{"path": "a.py"}')]),
        chunk(tool_calls=[FakeToolCallDelta(index=1, arguments='{"command": "ls"}')]),
        chunk(finish_reason="tool_calls"),
    ]
    _, tool_calls, _ = nc.parse_tool_calls(stream)
    assert len(tool_calls) == 2
    assert tool_calls[0].name == "read_file"
    assert tool_calls[0].arguments == '{"path": "a.py"}'
    assert tool_calls[1].name == "bash"
    assert tool_calls[1].arguments == '{"command": "ls"}'
 
 
def test_content_and_tool_calls_in_same_stream():
    # A model can emit some narration before/alongside deciding to call a tool.
    stream = [
        chunk(content="Let me check that file."),
        chunk(tool_calls=[FakeToolCallDelta(index=0, id="call_1", name="read_file", arguments='{"path": "x"}')]),
        chunk(finish_reason="tool_calls"),
    ]
    reply, tool_calls, finish_reason = nc.parse_tool_calls(stream)
    assert reply == "Let me check that file."
    assert len(tool_calls) == 1
    assert finish_reason == "tool_calls"
 
 
def test_empty_stream_returns_defaults():
    reply, tool_calls, finish_reason = nc.parse_tool_calls([])
    assert reply == ""
    assert tool_calls == []
    assert finish_reason is None