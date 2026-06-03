import pytest
from app.services.agent_service import SurveillanceAgent

@pytest.mark.asyncio
async def test_agent_init():
    agent = SurveillanceAgent(provider="google", model="gemini-3.5-flash")
    assert agent is not None
