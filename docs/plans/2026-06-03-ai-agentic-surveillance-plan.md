# AI-Agentic Surveillance Control Center Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Cholera Surveillance System into an AI-agentic control center with an integrated sidebar chat copilot (supporting Gemini, Claude, DeepSeek, OpenRouter, and NVIDIA NIM), a system thoughts console, and dynamic CSV/Excel upload analysis.

**Architecture:** Create an agent endpoint in FastAPI using the Google Antigravity SDK for Gemini and `litellm` for alternative models/providers. Bind database and file tools to both paths and stream responses/thoughts via SSE to the React frontend.

**Tech Stack:** FastAPI, Python, Google Antigravity SDK, LiteLLM, Pandas, React 18, Tailwind CSS.

---

### Task 1: Environment & Dependency Setup

**Files:**
- Modify: [requirements.txt](file:///Users/yakky/Dev/flooding-cholera/backend/requirements.txt:41-45)

**Step 1: Write the failing test**
Create a temporary script `backend/tests/test_deps.py` to assert dependencies are loadable.
```python
def test_dependencies():
    import google.antigravity
    import litellm
    import pandas
    assert google.antigravity is not None
    assert litellm is not None
    assert pandas is not None
```

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest backend/tests/test_deps.py`
Expected: FAIL (ModuleNotFoundError: No module named 'google')

**Step 3: Write minimal implementation**
Edit [requirements.txt](file:///Users/yakky/Dev/flooding-cholera/backend/requirements.txt):
Add `google-antigravity>=0.1.0` and `litellm>=1.20.0`.
Create venv and install:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install google-antigravity litellm
```

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest backend/tests/test_deps.py`
Expected: PASS

**Step 5: Commit**
```bash
git add backend/requirements.txt
git commit -m "chore: add google-antigravity and litellm dependencies"
```

---

### Task 2: Backend Agent Service & Tools

**Files:**
- Create: [agent_service.py](file:///Users/yakky/Dev/flooding-cholera/backend/app/services/agent_service.py)
- Create: [test_agent_service.py](file:///Users/yakky/Dev/flooding-cholera/backend/tests/test_agent_service.py)

**Step 1: Write the failing test**
```python
import pytest
from app.services.agent_service import SurveillanceAgent

@pytest.mark.asyncio
async def test_agent_init():
    agent = SurveillanceAgent(provider="google", model="gemini-3.5-flash")
    assert agent is not None
```

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest backend/tests/test_agent_service.py`
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**
Create [agent_service.py](file:///Users/yakky/Dev/flooding-cholera/backend/app/services/agent_service.py):
```python
from google.antigravity import Agent, LocalAgentConfig
from app.database import SessionLocal
import pandas as pd
import litellm
import json

class SurveillanceAgent:
    def __init__(self, provider: str = "google", model: str = "gemini-3.5-flash", api_key: str = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        
        self.system_instructions = (
            "You are the Cholera Environmental Surveillance Copilot. Assist users with "
            "epidemiological and environmental analysis. You have access to tools for querying "
            "the system's database and analyzing uploaded files."
        )

    def query_db(self, SQL_query: str) -> str:
        """Run read-only database queries against LGA and case tables."""
        db = SessionLocal()
        try:
            result = db.execute(SQL_query).fetchall()
            return json.dumps([dict(row) for row in result])
        except Exception as e:
            return str(e)
        finally:
            db.close()

    def analyze_file(self, file_path: str, operation: str) -> str:
        """Load an uploaded CSV or Excel file and perform descriptive analytics using Pandas."""
        try:
            df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
            if operation == "describe":
                return df.describe().to_json()
            elif operation == "corr":
                return df.corr(numeric_only=True).to_json()
            return df.head().to_json()
        except Exception as e:
            return str(e)

    async def chat(self, prompt: str):
        if self.provider == "google":
            config = LocalAgentConfig(
                model=self.model,
                system_instructions=self.system_instructions,
                tools=[self.query_db, self.analyze_file]
            )
            async with Agent(config=config) as agent:
                response = await agent.chat(prompt)
                # Yield tuple of (thought, text)
                async for thought in response.thoughts:
                    yield "thought", thought
                async for token in response:
                    yield "text", token
        else:
            # Route other providers through litellm
            # Map tools to standard openai tool format
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "query_db",
                        "description": "Run read-only database queries against LGA and case tables.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "SQL_query": {"type": "string"}
                            },
                            "required": ["SQL_query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "analyze_file",
                        "description": "Load an uploaded CSV or Excel file and perform descriptive analytics using Pandas.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "operation": {"type": "string", "enum": ["describe", "corr", "head"]}
                            },
                            "required": ["file_path", "operation"]
                        }
                    }
                }
            ]
            response = await litellm.acompletion(
                model=f"{self.provider}/{self.model}" if self.provider != "openrouter" else f"openrouter/{self.model}",
                messages=[
                    {"role": "system", "content": self.system_instructions},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                stream=True
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield "text", delta.content
```

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest backend/tests/test_agent_service.py`
Expected: PASS

**Step 5: Commit**
```bash
git add backend/app/services/agent_service.py
git commit -m "feat: implement SurveillanceAgent backend service with tools and litellm fallback"
```

---

### Task 3: Backend Agent & Ingestion Router

**Files:**
- Create: [agent.py](file:///Users/yakky/Dev/flooding-cholera/backend/app/routers/agent.py)
- Modify: [main.py](file:///Users/yakky/Dev/flooding-cholera/backend/app/main.py:160-175)

**Step 1: Write the failing test**
Create `backend/tests/test_agent_router.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_agent_chat_endpoint():
    response = client.post("/api/agent/chat", json={"message": "hello", "provider": "google", "model": "gemini-3.5-flash"})
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest backend/tests/test_agent_router.py`
Expected: FAIL (404 Not Found)

**Step 3: Write minimal implementation**
Create [agent.py](file:///Users/yakky/Dev/flooding-cholera/backend/app/routers/agent.py):
```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.agent_service import SurveillanceAgent
import shutil
import os

router = APIRouter(prefix="/api/agent", tags=["agent"])
UPLOAD_DIR = "data/agent_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    message: str
    provider: str = "google"
    model: str = "gemini-3.5-flash"

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    agent_instance = SurveillanceAgent(provider=request.provider, model=request.model)
    try:
        async def response_generator():
            async for token_type, token in agent_instance.chat(request.message):
                if token_type == "thought":
                    yield f"THOUGHT: {token}\n"
                else:
                    yield f"TEXT: {token}\n"
        return StreamingResponse(response_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "file_path": file_path}
```
Expose this router in `backend/app/main.py` by importing `agent_router` and calling `app.include_router(agent_router)`.

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest backend/tests/test_agent_router.py`
Expected: PASS

**Step 5: Commit**
```bash
git add backend/app/routers/agent.py backend/app/main.py
git commit -m "feat: add agent router supporting custom providers"
```

---

### Task 4: Frontend Layout Revamp (AI Copilot & Console)

**Files:**
- Create: [AgentSidebar.tsx](file:///Users/yakky/Dev/flooding-cholera/frontend/src/components/Agent/AgentSidebar.tsx)
- Create: [SystemConsole.tsx](file:///Users/yakky/Dev/flooding-cholera/frontend/src/components/Agent/SystemConsole.tsx)
- Modify: [MainLayout.tsx](file:///Users/yakky/Dev/flooding-cholera/frontend/src/components/Layout/MainLayout.tsx)

**Step 1: Write UI Structure**
Create [SystemConsole.tsx](file:///Users/yakky/Dev/flooding-cholera/frontend/src/components/Agent/SystemConsole.tsx) for terminal window logs.
Create [AgentSidebar.tsx](file:///Users/yakky/Dev/flooding-cholera/frontend/src/components/Agent/AgentSidebar.tsx) to host the right-sidebar chat, provider/model dropdowns, and drag-drop files.

**Step 2: Modify MainLayout for the Three-Column Layout**
Include `AgentSidebar` on the right side of the main workspace wrapper.
Include `SystemConsole` at the bottom of the main layout center pane.
Ensure the layout is highly interactive with collapsible buttons.

**Step 3: Connect API and Stream Handling**
Implement SSE parser to split `THOUGHT:` tokens (rendered in System Console) and `TEXT:` tokens (rendered in AgentSidebar chat bubble).

**Step 4: Verify UI functionality**
Deploy locally and manually check that layout splits correctly, sidebar collapses/expands, and console opens/closes.

**Step 5: Commit**
```bash
git add frontend/src/components/Agent/ frontend/src/components/Layout/MainLayout.tsx
git commit -m "feat: implement premium AI workspace shell with Copilot Sidebar & System Console"
```
