"""Surveillance Agent service — multi-provider, streaming, tool-use."""
import logging
import json
import os
import re
import pandas as pd
import litellm
from dotenv import load_dotenv
from app.database import SessionLocal

# Load .env into os.environ so litellm can discover API keys
load_dotenv()

logger = logging.getLogger(__name__)

# ── Google Antigravity (optional) ──────────────────────────────────────────
try:
    from google.antigravity import Agent, LocalAgentConfig
    HAS_ANTIGRAVITY = True
except ImportError:
    HAS_ANTIGRAVITY = False

    class LocalAgentConfig:  # noqa: D101
        def __init__(self, **kwargs):
            self.model = kwargs.get("model")
            self.system_instructions = kwargs.get("system_instructions")
            self.tools = kwargs.get("tools", [])

    class Agent:  # noqa: D101
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def chat(self, prompt):
            pass


# ── Provider → env key mappings ────────────────────────────────────────────
PROVIDER_ENV_KEYS = {
    "google":      "GEMINI_API_KEY",
    "vertex":      "GOOGLE_APPLICATION_CREDENTIALS",
    "anthropic":   "ANTHROPIC_API_KEY",
    "deepseek":    "DEEPSEEK_API_KEY",
    "openrouter":  "OPENROUTER_API_KEY",
    "nvidia_nim":  "NVIDIA_NIM_API_KEY",
}


def _adc_available() -> bool:
    """True if Google ADC / Vertex creds are usable (file path set and exists)."""
    p = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    return bool(p and os.path.exists(p))


def _has_key(provider: str) -> bool:
    """Return True if credentials for *provider* are configured in the environment."""
    # google + vertex both authenticate through Vertex ADC in this deployment
    if provider in ("vertex", "google"):
        return _adc_available() or bool(os.environ.get("GEMINI_API_KEY"))
    env_key = PROVIDER_ENV_KEYS.get(provider)
    return bool(env_key and os.environ.get(env_key))


def provider_status() -> dict[str, bool]:
    """Return a dict of {provider_id: has_key} for all known providers."""
    return {p: _has_key(p) for p in PROVIDER_ENV_KEYS}


def _model_name_for_litellm(provider: str, model: str) -> str:
    """Build the model string litellm expects for the given provider."""
    # If the model already contains a slash it is already fully qualified
    if "/" in model:
        return model

    # Map UI model ids to models actually available on our Vertex project
    _VERTEX_ALIAS = {
        "gemini-3.5-flash": "gemini-2.5-flash",
        "gemini-3.6-flash": "gemini-2.5-flash",
        "gemini-3.1-pro-preview": "gemini-2.5-pro",
    }

    if provider == "google":
        # No Gemini API key in this deployment → route Google models through Vertex ADC
        if not os.environ.get("GEMINI_API_KEY") and _adc_available():
            return f"vertex_ai/{_VERTEX_ALIAS.get(model, model)}"
        return f"gemini/{model}"
    if provider == "vertex":
        return f"vertex_ai/{_VERTEX_ALIAS.get(model, model)}"
    if provider == "deepseek":
        return f"deepseek/{model}"
    if provider == "openrouter":
        return f"openrouter/{model}"
    if provider == "nvidia_nim":
        return f"nvidia_nim/{model}"
    # anthropic uses the model name directly (no prefix needed)
    return model


class StreamingDSMLFilter:
    """Filters out DSML blocks from a text stream."""

    def __init__(self):
        self.buffer = ""
        self.in_dsml = False

    def _normalize(self, text: str) -> str:
        # Replace fullwidth pipes with ASCII pipes
        text = text.replace("｜", "|")
        # Remove spaces
        text = text.replace(" ", "")
        # Replace double pipes with single pipe
        while "||" in text:
            text = text.replace("||", "|")
        return text.lower()

    def feed(self, chunk: str) -> str:
        self.buffer += chunk
        output = []

        while True:
            if not self.in_dsml:
                idx = self.buffer.find("<")
                if idx == -1:
                    output.append(self.buffer)
                    self.buffer = ""
                    break

                sub = self.buffer[idx:]
                normalized = self._normalize(sub)

                if normalized.startswith("<|dsml") or normalized.startswith("<dsml"):
                    output.append(self.buffer[:idx])
                    self.buffer = sub
                    self.in_dsml = True
                    continue

                # Check if it's a partial match for a start tag
                is_prefix = False
                for p in ("<|dsml", "<dsml"):
                    if len(normalized) < len(p) and p.startswith(normalized):
                        is_prefix = True
                        break

                if is_prefix:
                    output.append(self.buffer[:idx])
                    self.buffer = sub
                    break

                output.append(self.buffer[:idx + 1])
                self.buffer = self.buffer[idx + 1:]
            else:
                idx_end = self.buffer.lower().find("</")
                if idx_end == -1:
                    if len(self.buffer) > 1000:
                        self.buffer = self.buffer[-1000:]
                    break

                sub = self.buffer[idx_end:]
                normalized = self._normalize(sub)

                # Check if it matches the main end tag to exit DSML mode
                target_end = "</|dsml|tool_calls>"
                target_end_simple = "</dsml>"
                if normalized.startswith(target_end) or normalized.startswith(target_end_simple):
                    gt_idx = sub.find(">")
                    if gt_idx != -1:
                        self.buffer = sub[gt_idx + 1:]
                        self.in_dsml = False
                        continue

                # Check if it's a partial match for any end tag
                is_prefix_end = False
                for p in (target_end, target_end_simple):
                    if len(normalized) < len(p) and p.startswith(normalized):
                        is_prefix_end = True
                        break

                if is_prefix_end:
                    self.buffer = sub
                    break

                self.buffer = self.buffer[idx_end + 1:]
                break

        return "".join(output)

    def flush(self) -> str:
        if not self.in_dsml:
            res = self.buffer
            self.buffer = ""
            return res
        return ""


_READ_ONLY_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


class SurveillanceAgent:
    """Streaming, multi-provider agent for cholera surveillance assistance."""

    SYSTEM_INSTRUCTIONS = (
        "You are the Cholera Environmental Surveillance Copilot. "
        "You help epidemiologists and health officers analyse disease data for Cross River State, Nigeria.\n"
        "You have three tools available:\n"
        "  • query_db — run read-only SQL SELECT queries against the LGA and case tables.\n"
        "  • analyze_file — perform descriptive analytics (describe, corr, head) on uploaded CSV/Excel files.\n"
        "  • generate_ui_spec — create a custom interactive UI layout (KPIs, charts, maps, tables) to visualize the data in an uploaded CSV or Excel file. Call this tool when a user uploads a file and asks to visualize it or when they want to build an interactive dashboard for their file.\n"
        "Always explain your reasoning before calling a tool and summarise findings clearly after."
    )

    def __init__(
        self,
        provider: str = "deepseek",
        model: str = "deepseek-v4-flash",
        api_key: str | None = None,
        history: list[dict] | None = None,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        # conversation history (list of {role, content} dicts)
        self.history: list[dict] = history or []
        # Instance system instructions copy
        self.system_instructions = self.SYSTEM_INSTRUCTIONS

    # ── Tools ─────────────────────────────────────────────────────────────

    def query_db(self, SQL_query: str) -> str:
        """Run a read-only SQL SELECT query against LGA and case tables."""
        if not _READ_ONLY_RE.match(SQL_query):
            return json.dumps({"error": "Only SELECT statements are allowed."})
        db = SessionLocal()
        try:
            from sqlalchemy import text
            result = db.execute(text(SQL_query)).fetchall()
            return json.dumps([dict(row._mapping) for row in result], default=str)
        except Exception as exc:
            logger.warning("query_db error: %s", exc)
            return json.dumps({"error": str(exc)})
        finally:
            db.close()

    def analyze_file(self, file_path: str, operation: str) -> str:
        """Load an uploaded CSV or Excel file and run pandas analytics."""
        try:
            resolved_path = file_path
            if not os.path.exists(resolved_path):
                filename = os.path.basename(file_path)
                alt_path1 = os.path.join("data", "agent_uploads", filename)
                alt_path2 = os.path.join("backend", "data", "agent_uploads", filename)

                if os.path.exists(alt_path1):
                    resolved_path = alt_path1
                elif os.path.exists(alt_path2):
                    resolved_path = alt_path2
                else:
                    uploads_dir = "data/agent_uploads"
                    files = os.listdir(uploads_dir) if os.path.exists(uploads_dir) else []
                    return json.dumps({
                        "error": f"File not found: {file_path}. Checked alternative locations but none exist. Available files: {files}"
                    })

            df = (
                pd.read_csv(resolved_path)
                if resolved_path.endswith(".csv")
                else pd.read_excel(resolved_path)
            )
            if operation == "describe":
                return df.describe().to_json()
            if operation == "corr":
                return df.corr(numeric_only=True).to_json()
            return df.head().to_json()
        except Exception as exc:
            logger.warning("analyze_file error: %s", exc)
            return json.dumps({"error": str(exc)})

    def generate_ui_spec(self, file_path: str, ui_config: str) -> str:
        """Register a custom UI dashboard layout configuration for the uploaded dataset."""
        try:
            parsed = json.loads(ui_config)
            os.makedirs("data/agent_uploads", exist_ok=True)
            with open("data/agent_uploads/active_ui_spec.json", "w") as f:
                json.dump({"file_path": file_path, "config": parsed}, f)
            return json.dumps({
                "status": "success",
                "file_path": file_path,
                "ui_config": parsed
            })
        except Exception as exc:
            return json.dumps({"error": f"Invalid JSON config: {exc}"})

    # ── OpenAI-compatible tool schema ─────────────────────────────────────

    @staticmethod
    def _tools_schema() -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_db",
                    "description": (
                        "Run a read-only SQL SELECT query against the LGA and "
                        "cholera case tables in the surveillance database."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "SQL_query": {
                                "type": "string",
                                "description": "A valid SQL SELECT statement.",
                            }
                        },
                        "required": ["SQL_query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_file",
                    "description": (
                        "Load an uploaded CSV or Excel file and perform "
                        "descriptive analytics using pandas."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "operation": {
                                "type": "string",
                                "enum": ["describe", "corr", "head"],
                            },
                        },
                        "required": ["file_path", "operation"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_ui_spec",
                    "description": (
                        "Generate a custom UI dashboard layout configuration (widgets like maps, charts, tables, KPIs) "
                        "to visualize and explore the data in an uploaded CSV/Excel file."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the uploaded CSV or Excel file."
                            },
                            "ui_config": {
                                "type": "string",
                                "description": (
                                    "A JSON string containing the UI layout specification. "
                                    "Conforms to: {\n"
                                    "  \"title\": \"Dashboard Title\",\n"
                                    "  \"description\": \"Brief description\",\n"
                                    "  \"widgets\": [\n"
                                    "    {\n"
                                    "      \"type\": \"kpi\" | \"chart\" | \"map\" | \"table\" | \"text\",\n"
                                    "      \"title\": \"Widget Title\",\n"
                                    "      \"gridSpan\": 1-12,\n"
                                    "      \"config\": {\n"
                                    "        \"valueKey\": \"column name\",\n"
                                    "        \"aggType\": \"sum\" | \"avg\" | \"count\",\n"
                                    "        \"chartType\": \"bar\" | \"line\" | \"area\",\n"
                                    "        \"xAxisKey\": \"column name\",\n"
                                    "        \"series\": [{\"key\": \"column\", \"color\": \"#hex\"}],\n"
                                    "        \"latKey\": \"column name\",\n"
                                    "        \"lngKey\": \"column name\",\n"
                                    "        \"labelKey\": \"column name\"\n"
                                    "      }\n"
                                    "    }\n"
                                    "  ]\n"
                                    "}"
                                )
                            }
                        },
                        "required": ["file_path", "ui_config"],
                    },
                },
            },
        ]

    # ── Chat ──────────────────────────────────────────────────────────────

    async def chat(self, prompt: str):
        """Async generator yielding (type, content) tuples.

        Types:
          "thought" — internal reasoning / tool events (shown in console)
          "text"    — final response tokens (shown in sidebar)
        """
        filter_obj = StreamingDSMLFilter()
        async for token_type, token in self._chat_raw(prompt):
            if token_type == "text":
                filtered = filter_obj.feed(token)
                if filtered:
                    yield "text", filtered
            else:
                yield token_type, token

        flushed = filter_obj.flush()
        if flushed:
            yield "text", flushed

    async def _chat_raw(self, prompt: str):
        """Internal raw async generator yielding raw (type, content) tuples."""
        # ── Google Antigravity path ────────────────────────────────────────
        if self.provider == "google" and HAS_ANTIGRAVITY:
            config = LocalAgentConfig(
                model=self.model,
                system_instructions=self.system_instructions,
                tools=[self.query_db, self.analyze_file, self.generate_ui_spec],
            )
            async with Agent(config=config) as agent:
                response = await agent.chat(prompt)
                async for thought in response.thoughts:
                    yield "thought", thought
                async for token in response:
                    yield "text", token
            return

        # ── LiteLLM fallback path (all providers) ─────────────────────────
        if not _has_key(self.provider):
            yield "thought", f"⚠️  No API key found for provider '{self.provider}' ({PROVIDER_ENV_KEYS.get(self.provider, 'N/A')}). Running in Mock Mode."
            yield "thought", f"Mock executing: provider={self.provider}, model={self.model}"
            if re.search(r"\b(visualize|ui|spec|dashboard|render)\b", prompt, re.IGNORECASE):
                import pandas as pd

                file_path = None
                match = re.search(r'["\']([^"\']+\.(?:csv|xlsx?))["\']', prompt)
                if match:
                    file_path = f"data/agent_uploads/{os.path.basename(match.group(1))}"
                
                # Check history if not found in prompt
                if not file_path:
                    for msg in reversed(self.history):
                        if msg.get("role") == "user" and "I've uploaded" in msg.get("content", ""):
                            h_match = re.search(r'["\']([^"\']+\.(?:csv|xlsx?))["\']', msg.get("content", ""))
                            if h_match:
                                file_path = f"data/agent_uploads/{os.path.basename(h_match.group(1))}"
                                break

                # Search directory for any files if still not found
                if not file_path:
                    upload_dir = "data/agent_uploads"
                    if os.path.exists(upload_dir):
                        files = [f for f in os.listdir(upload_dir) if f.endswith(('.csv', '.xlsx', '.xls'))]
                        if files:
                            # Prefer non-mock_data first
                            real_files = [f for f in files if f != 'mock_data.csv']
                            file_path = f"data/agent_uploads/{real_files[0] if real_files else files[0]}"

                # Fallback
                if not file_path:
                    file_path = "data/agent_uploads/mock_data.csv"

                yield "thought", f"🔧 Executing tool generate_ui_spec with file_path: {file_path}"

                # Read columns dynamically
                cols = []
                try:
                    full_path = file_path
                    if not os.path.exists(full_path):
                        filename = os.path.basename(file_path)
                        alt_path1 = os.path.join("data", "agent_uploads", filename)
                        alt_path2 = os.path.join("backend", "data", "agent_uploads", filename)
                        if os.path.exists(alt_path1):
                            full_path = alt_path1
                        elif os.path.exists(alt_path2):
                            full_path = alt_path2
                    
                    df = pd.read_csv(full_path) if full_path.endswith('.csv') else pd.read_excel(full_path)
                    cols = [str(c) for c in df.columns]
                except Exception as e:
                    logger.error(f"Error reading columns from {file_path}: {e}")

                lga_col = "lga"
                cases_col = "cases"
                risk_col = "risk_score"
                rain_col = "precipitation"
                lat_col = "latitude"
                lng_col = "longitude"
                date_col = "date"

                if cols:
                    # LGA/location column
                    for kw in ["lga", "district", "county", "municip", "region", "location", "area", "settlement", "state", "name"]:
                        found = False
                        for c in cols:
                            if kw in c.lower():
                                lga_col = c
                                found = True
                                break
                        if found:
                            break
                    # Cases column
                    for c in cols:
                        if any(w in c.lower() for w in ["case", "suspect", "confirm", "count", "total", "number", "new_cases"]):
                            cases_col = c
                            break
                    # Risk score column
                    for c in cols:
                        if any(w in c.lower() for w in ["risk", "score", "level", "index"]):
                            risk_col = c
                            break
                    # Precipitation column
                    for c in cols:
                        if any(w in c.lower() for w in ["rain", "precip", "water", "weather", "precipitation"]):
                            rain_col = c
                            break
                    # Latitude column
                    for c in cols:
                        if any(w in c.lower() for w in ["lat", "y"]):
                            lat_col = c
                            break
                    # Longitude column
                    for c in cols:
                        if any(w in c.lower() for w in ["lon", "lng", "x", "long"]):
                            lng_col = c
                            break
                    # Date column
                    for c in cols:
                        if any(w in c.lower() for w in ["date", "time", "day", "month", "year"]):
                            date_col = c
                            break

                mock_ui_spec = {
                    "title": f"Surveillance Analysis: {os.path.basename(file_path)}",
                    "description": "AI-generated dashboard mapping spatial risk factors and cases from the uploaded file.",
                    "widgets": [
                        {
                            "type": "kpi",
                            "title": f"Total {cases_col.replace('_', ' ').title()}",
                            "gridSpan": 4,
                            "config": {
                                "valueKey": cases_col,
                                "aggType": "sum",
                                "icon": "coronavirus",
                                "color": "red"
                            }
                        },
                        {
                            "type": "kpi",
                            "title": f"Average {risk_col.replace('_', ' ').title()}",
                            "gridSpan": 4,
                            "config": {
                                "valueKey": risk_col,
                                "aggType": "avg",
                                "icon": "water_drop",
                                "color": "blue"
                            }
                        },
                        {
                            "type": "kpi",
                            "title": "Records Count",
                            "gridSpan": 4,
                            "config": {
                                "valueKey": cases_col,
                                "aggType": "count",
                                "icon": "monitoring",
                                "color": "green"
                            }
                        },
                        {
                            "type": "map",
                            "title": "Spatial Distribution",
                            "gridSpan": 12,
                            "config": {
                                "latKey": lat_col,
                                "lngKey": lng_col,
                                "labelKey": lga_col,
                                "valueKeyForMarker": risk_col
                            }
                        },
                        {
                            "type": "chart",
                            "title": f"{cases_col.replace('_', ' ').title()} by {lga_col.replace('_', ' ').title()}",
                            "gridSpan": 6,
                            "config": {
                                "chartType": "bar",
                                "xAxisKey": lga_col,
                                "series": [
                                    {"key": cases_col, "color": "#fa6238"}
                                ]
                            }
                        },
                        {
                            "type": "chart",
                            "title": f"{rain_col.replace('_', ' ').title()} vs {cases_col.replace('_', ' ').title()} Correlation",
                            "gridSpan": 6,
                            "config": {
                                "chartType": "line",
                                "xAxisKey": date_col,
                                "series": [
                                    {"key": cases_col, "color": "#fa6238"},
                                    {"key": rain_col, "color": "#1392ec"}
                                ]
                            }
                        },
                        {
                            "type": "table",
                            "title": "Uploaded Dataset Table Viewer",
                            "gridSpan": 12,
                            "config": {}
                        }
                    ]
                }
                
                # yield ui_spec
                yield "ui_spec", json.dumps({"file_path": file_path, "config": mock_ui_spec})
                yield "thought", "📦 Tool generate_ui_spec output: success"
                yield "text", (
                    f"**Dynamic UI Dashboard Generated!** *(No API key configured)*\n\n"
                    f"I have successfully analyzed the uploaded file `{os.path.basename(file_path)}`, detected columns `{', '.join(cols[:5])}...`, and dynamically built an interactive dashboard map and charts. "
                    f"Click **View UI** or switch to the **Agent Explorer** tab to inspect the interactive widgets!"
                )
            elif re.search(r"\b(select|query|data|lga|risk|cases)\b", prompt, re.IGNORECASE):
                sql = "SELECT name, risk_score FROM lgas LIMIT 3;"
                yield "thought", f"🔧 Executing tool query_db with SQL: {sql}"
                res = self.query_db(sql)
                yield "thought", f"📦 Tool output: {res}"
                yield "text", f"**Mock result** *(No API key configured)*\n\n{res}"
            else:
                yield "text", (
                    f"**Mock response** *(No API key configured for `{self.provider}`)*\n\n"
                    f"Your message was: *{prompt}*\n\n"
                    "Configure the relevant API key in your `.env` file to enable live responses."
                )
            return

        model_str = _model_name_for_litellm(self.provider, self.model)
        messages = [
            {"role": "system", "content": self.system_instructions},
            *self.history,
            {"role": "user", "content": prompt},
        ]

        try:
            max_turns = 10
            for turn in range(max_turns):
                # On the last turn, force a final text response by not offering tools
                active_tools = self._tools_schema() if turn < max_turns - 1 else None
                _extra = {}
                if model_str.startswith("vertex_ai/"):
                    _extra = {
                        "vertex_project": os.getenv("VERTEX_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT"),
                        "vertex_location": os.getenv("VERTEX_LOCATION", "global"),
                    }
                response = await litellm.acompletion(
                    model=model_str,
                    messages=messages,
                    tools=active_tools,
                    stream=True,
                    **_extra,
                )

                tool_calls_acc: list[dict] = []
                async for chunk in response:
                    delta = chunk.choices[0].delta
                    
                    # Yield reasoning content as thoughts (e.g. for thinking models)
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        yield "thought", reasoning

                    # Accumulate tool call chunks
                    if getattr(delta, "tool_calls", None):
                        for tc in delta.tool_calls:
                            while len(tool_calls_acc) <= tc.index:
                                tool_calls_acc.append({"id": "", "name": "", "arguments": ""})
                            if tc.id:
                                tool_calls_acc[tc.index]["id"] = tc.id
                            if tc.function.name:
                                tool_calls_acc[tc.index]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[tc.index]["arguments"] += tc.function.arguments

                    # Stream text tokens directly
                    if getattr(delta, "content", None):
                        yield "text", delta.content

                # If no tool calls were generated in this turn, we are done!
                if not tool_calls_acc:
                    break

                # ── Execute any tool calls ─────────────────────────────────────
                tool_results_messages: list[dict] = []

                for idx, tc in enumerate(tool_calls_acc):
                    name = tc["name"]
                    args_str = tc["arguments"]
                    tc_id = tc["id"] or f"call_{idx}_{turn}"

                    try:
                        args = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        args = {}

                    yield "thought", f"🔧 Executing tool `{name}` with args: `{json.dumps(args)}`"

                    if name == "query_db":
                        res = self.query_db(args.get("SQL_query", ""))
                    elif name == "analyze_file":
                        res = self.analyze_file(
                            args.get("file_path", ""),
                            args.get("operation", "head"),
                        )
                    elif name == "generate_ui_spec":
                        file_path = args.get("file_path", "")
                        ui_config_str = args.get("ui_config", "")
                        res = self.generate_ui_spec(file_path, ui_config_str)
                        try:
                            ui_config_obj = json.loads(ui_config_str)
                            yield "ui_spec", json.dumps({"file_path": file_path, "config": ui_config_obj})
                        except Exception as exc:
                            yield "thought", f"⚠️ Error parsing generate_ui_spec json: {exc}"
                    else:
                        res = json.dumps({"error": f"Unknown tool: {name}"})

                    yield "thought", f"📦 Tool `{name}` output: {res[:400]}{'...' if len(res) > 400 else ''}"

                    tool_results_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": name,
                            "content": res,
                        }
                    )

                # Add assistant's tool calls and tool results to messages for the next turn
                assistant_tool_calls_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc["id"] or f"call_{i}_{turn}",
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for i, tc in enumerate(tool_calls_acc)
                    ],
                }

                messages.append(assistant_tool_calls_msg)
                messages.extend(tool_results_messages)

                yield "thought", "💬 Synthesising response from tool outputs…"

        except litellm.exceptions.AuthenticationError as exc:
            yield "thought", f"❌ Authentication error: {exc}"
            yield "text", f"Authentication failed for `{self.provider}`. Please check your API key."
        except litellm.exceptions.RateLimitError as exc:
            yield "thought", f"⏳ Rate limit hit: {exc}"
            yield "text", "Rate limit reached. Please wait a moment and try again."
        except Exception as exc:
            logger.exception("agent_service chat error")
            yield "thought", f"❌ Unexpected error: {exc}"
            yield "text", f"Sorry, an error occurred: {exc}"
