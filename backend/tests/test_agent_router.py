from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_agent_chat_endpoint():
    response = client.post("/api/agent/chat", json={"message": "hello", "provider": "google", "model": "gemini-3.5-flash"})
    assert response.status_code == 200
