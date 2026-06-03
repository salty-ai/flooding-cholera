import logging
import json
import pandas as pd
import litellm
from app.database import SessionLocal

logger = logging.getLogger(__name__)

try:
    from google.antigravity import Agent, LocalAgentConfig
    HAS_ANTIGRAVITY = True
except ImportError:
    HAS_ANTIGRAVITY = False
    class LocalAgentConfig:
        def __init__(self, **kwargs):
            self.model = kwargs.get("model")
            self.system_instructions = kwargs.get("system_instructions")
            self.tools = kwargs.get("tools", [])

    class Agent:
        def __init__(self, config):
            self.config = config
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def chat(self, prompt):
            pass

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
            from sqlalchemy import text
            result = db.execute(text(SQL_query)).fetchall()
            return json.dumps([dict(row._mapping) for row in result], default=str)
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
        if self.provider == "google" and HAS_ANTIGRAVITY:
            config = LocalAgentConfig(
                model=self.model,
                system_instructions=self.system_instructions,
                tools=[self.query_db, self.analyze_file]
            )
            async with Agent(config=config) as agent:
                response = await agent.chat(prompt)
                async for thought in response.thoughts:
                    yield "thought", thought
                async for token in response:
                    yield "text", token
        else:
            # Fallback when google-antigravity is missing or for other providers using litellm
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
            
            try:
                import os
                has_keys = False
                model_name = self.model
                if self.provider == "google" or "gemini" in self.model:
                    has_keys = "GEMINI_API_KEY" in os.environ
                    model_name = f"gemini/{self.model}"
                elif self.provider == "openai" or "gpt" in self.model:
                    has_keys = "OPENAI_API_KEY" in os.environ
                elif self.provider == "anthropic" or "claude" in self.model:
                    has_keys = "ANTHROPIC_API_KEY" in os.environ
                else:
                    has_keys = any(k.endswith("_API_KEY") for k in os.environ.keys())

                if not has_keys:
                    yield "thought", "Checking local keys... None found. Falling back to Mock response."
                    yield "thought", f"Mock executing: provider={self.provider}, model={self.model}"
                    if "select" in prompt.lower() or "query" in prompt.lower():
                        yield "thought", f"Simulating query_db tool call for prompt: '{prompt}'"
                        res = self.query_db("SELECT name, risk_score FROM lgas LIMIT 3;")
                        yield "text", f"Here is the database query result:\n{res}"
                    else:
                        yield "text", f"This is a mocked response because no API keys were found in the environment. Your prompt was: '{prompt}'"
                    return

                response = await litellm.acompletion(
                    model=model_name if "/" in model_name else f"{self.provider}/{self.model}" if self.provider != "openrouter" else f"openrouter/{self.model}",
                    messages=[
                        {"role": "system", "content": self.system_instructions},
                        {"role": "user", "content": prompt}
                    ],
                    tools=tools,
                    stream=True
                )
                
                tool_calls = []
                async for chunk in response:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            if len(tool_calls) <= tool_call.index:
                                tool_calls.append({"name": "", "arguments": ""})
                            if tool_call.function.name:
                                tool_calls[tool_call.index]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                tool_calls[tool_call.index]["arguments"] += tool_call.function.arguments
                    
                    if hasattr(delta, "content") and delta.content:
                        yield "text", delta.content
                
                for tool_call in tool_calls:
                    name = tool_call["name"]
                    args_str = tool_call["arguments"]
                    try:
                        args = json.loads(args_str) if args_str else {}
                    except Exception:
                        args = {}
                    
                    yield "thought", f"Executing tool {name} with args {args}"
                    if name == "query_db":
                        res = self.query_db(args.get("SQL_query", ""))
                        yield "thought", f"Tool output: {res}"
                        tool_response = await litellm.acompletion(
                            model=model_name if "/" in model_name else f"{self.provider}/{self.model}" if self.provider != "openrouter" else f"openrouter/{self.model}",
                            messages=[
                                {"role": "system", "content": self.system_instructions},
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": None, "tool_calls": [
                                    {"id": "call_1", "type": "function", "function": {"name": name, "arguments": args_str}}
                                ]},
                                {"role": "tool", "tool_call_id": "call_1", "name": name, "content": res}
                            ],
                            stream=True
                        )
                        async for chunk in tool_response:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, "content") and delta.content:
                                yield "text", delta.content
                    elif name == "analyze_file":
                        res = self.analyze_file(args.get("file_path", ""), args.get("operation", ""))
                        yield "thought", f"Tool output: {res}"
                        tool_response = await litellm.acompletion(
                            model=model_name if "/" in model_name else f"{self.provider}/{self.model}" if self.provider != "openrouter" else f"openrouter/{self.model}",
                            messages=[
                                {"role": "system", "content": self.system_instructions},
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": None, "tool_calls": [
                                    {"id": "call_2", "type": "function", "function": {"name": name, "arguments": args_str}}
                                ]},
                                {"role": "tool", "tool_call_id": "call_2", "name": name, "content": res}
                            ],
                            stream=True
                        )
                        async for chunk in tool_response:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, "content") and delta.content:
                                yield "text", delta.content
            except Exception as e:
                yield "thought", f"Error during completion: {str(e)}"
                yield "text", f"Sorry, I encountered an error: {str(e)}"
