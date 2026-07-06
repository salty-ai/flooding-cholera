import pytest
from app.services.agent_service import SurveillanceAgent, StreamingDSMLFilter

@pytest.mark.asyncio
async def test_agent_init():
    agent = SurveillanceAgent(provider="deepseek", model="deepseek-v4-flash")
    assert agent is not None

def test_streaming_dsml_filter():
    f = StreamingDSMLFilter()
    chunks = [
        "Hello ", 
        "world!", 
        " < | DSML | tool_calls>", 
        "< | DSML | invoke name=\"analyze_file\">", 
        "some args", 
        "</ | DSML | invoke>", 
        "</ | DSML | tool_calls>", 
        " Done!"
    ]
    out = [f.feed(c) for c in chunks] + [f.flush()]
    assert "".join(out) == "Hello world!  Done!"

