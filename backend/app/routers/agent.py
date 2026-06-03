"""Agent router — chat, file upload, and provider status endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.agent_service import SurveillanceAgent, provider_status
import shutil
import os

router = APIRouter(prefix="/api/agent", tags=["agent"])
UPLOAD_DIR = "data/agent_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    provider: str = "deepseek"
    model: str = "deepseek-v4-flash"
    history: list[ChatMessage] = []


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    agent_instance = SurveillanceAgent(
        provider=request.provider,
        model=request.model,
        history=history,
    )
    try:
        async def response_generator():
            import json
            async for token_type, token in agent_instance.chat(request.message):
                if token_type == "ui_spec":
                    # token is already a single-line JSON string
                    yield f"UI_SPEC:{token}\n"
                else:
                    yield f"{token_type.upper()}:{json.dumps(token)}\n"

        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def normalize_name(s: str) -> str:
    """Normalize location names for robust matching."""
    s = str(s).lower().replace("-", "").replace(" ", "").replace("_", "").strip()
    if s in ("yakurr", "yakuur"):
        return "yakuur"
    if "calabarmunicipal" in s or "calabarmunicipality" in s:
        return "calabarmunicipal"
    return s


def get_local_lga_centroid(lga_name: str) -> tuple[float, float] | None:
    """Extract LGA centroid from local geojson if name matches."""
    geojson_path = "backend/data/cross_river_lgas.geojson"
    if not os.path.exists(geojson_path):
        geojson_path = "data/cross_river_lgas.geojson"
    if not os.path.exists(geojson_path):
        return None
    try:
        import json
        with open(geojson_path, "r") as f:
            data = json.load(f)
        for feature in data.get("features", []):
            name = feature.get("properties", {}).get("name", "")
            if normalize_name(name) == normalize_name(lga_name):
                geom = feature.get("geometry", {})
                if geom.get("type") == "Polygon":
                    ring = geom.get("coordinates", [])[0]
                    lats = [pt[1] for pt in ring]
                    lons = [pt[0] for pt in ring]
                    return sum(lats) / len(lats), sum(lons) / len(lons)
    except Exception:
        pass
    return None


@router.get("/active-spec")
async def get_active_spec():
    """Retrieve the currently active generated spec JSON."""
    spec_path = os.path.join(UPLOAD_DIR, "active_ui_spec.json")
    if not os.path.exists(spec_path):
        # Also check alternative path
        alt_path = os.path.join("backend", UPLOAD_DIR, "active_ui_spec.json")
        if os.path.exists(alt_path):
            spec_path = alt_path
        else:
            return None
    try:
        import json
        with open(spec_path, "r") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/providers/status")
async def providers_status_endpoint():
    """Return which AI provider API keys are configured in the environment."""
    return provider_status()


@router.post("/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "file_path": file_path, "filename": file.filename}


@router.get("/data")
async def get_data_endpoint(file_path: str):
    """Retrieve and parse CSV/Excel file rows as JSON objects."""
    if not os.path.exists(file_path):
        # Check alternative locations
        filename = os.path.basename(file_path)
        alt_path1 = os.path.join("data", "agent_uploads", filename)
        alt_path2 = os.path.join("backend", "data", "agent_uploads", filename)
        if os.path.exists(alt_path1):
            file_path = alt_path1
        elif os.path.exists(alt_path2):
            file_path = alt_path2
        else:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    try:
        import pandas as pd
        import math
        import requests
        import json

        df = (
            pd.read_csv(file_path)
            if file_path.endswith(".csv")
            else pd.read_excel(file_path)
        )
        records = df.to_dict(orient="records")
        for r in records:
            for k, v in r.items():
                if isinstance(v, float) and math.isnan(v):
                    r[k] = None

        # Geocode LGA names if lat/lng are missing
        coord_cols = [c for c in df.columns if any(w in str(c).lower() for w in ["lat", "lng", "lon", "coord"])]
        if not coord_cols:
            lga_col = None
            for kw in ["lga", "district", "county", "municip", "region", "location", "area", "settlement", "state", "name"]:
                found = False
                for col in df.columns:
                    if kw in str(col).lower():
                        lga_col = col
                        found = True
                        break
                if found:
                    break
            
            if lga_col:
                cache_filename = "geocoding_cache.json"
                cache_path = os.path.join("backend", "data", cache_filename) if os.path.exists("backend") else os.path.join("data", cache_filename)
                
                geocoding_cache = {}
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, "r") as f:
                            geocoding_cache = json.load(f)
                    except Exception:
                        pass
                
                # Fetch distinct values
                unique_locations = df[lga_col].dropna().unique()
                cache_dirty = False
                
                for loc in unique_locations:
                    loc_str = str(loc).strip()
                    if not loc_str:
                        continue
                    
                    # Try local GeoJSON first (Cross River LGAs)
                    local_centroid = get_local_lga_centroid(loc_str)
                    if local_centroid:
                        if loc_str not in geocoding_cache or geocoding_cache[loc_str]["lat"] != local_centroid[0]:
                            geocoding_cache[loc_str] = {
                                "lat": local_centroid[0],
                                "lon": local_centroid[1]
                            }
                            cache_dirty = True
                    # Fallback to cache or Nominatim query
                    elif loc_str not in geocoding_cache:
                        try:
                            # Use custom User-Agent to satisfy Nominatim requirements
                            r = requests.get(
                                f"https://nominatim.openstreetmap.org/search?q={loc_str}+Nigeria&format=json&limit=1",
                                headers={"User-Agent": "CholeraSurveillanceSystem/1.0 (yakky@dev.local)"},
                                timeout=5
                            )
                            if r.status_code == 200:
                                res_data = r.json()
                                if res_data:
                                    geocoding_cache[loc_str] = {
                                        "lat": float(res_data[0]["lat"]),
                                        "lon": float(res_data[0]["lon"])
                                    }
                                    cache_dirty = True
                        except Exception:
                            pass
                
                if cache_dirty:
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path, "w") as f:
                        json.dump(geocoding_cache, f)
                
                # Inject coordinates into records list
                for r in records:
                    loc_val = str(r.get(lga_col, "")).strip()
                    if loc_val in geocoding_cache:
                        r["latitude"] = geocoding_cache[loc_val]["lat"]
                        r["longitude"] = geocoding_cache[loc_val]["lon"]

        return records
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
