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
