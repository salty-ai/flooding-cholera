#!/usr/bin/env python
"""Standalone 72-trial benchmark harness for the Cholera Surveillance Copilot.

Runs the platform's *own* agent implementation (``SurveillanceAgent`` from
``app.services.agent_service``) — it is NOT reimplemented here — over 12 schema
variants × 2 prompting conditions × 3 repetitions = 72 trials, against a live
LLM provider (default NVIDIA NIM, ``nvidia/llama-3.1-nemotron-70b-instruct``).

The agent's ``.chat()`` async generator is consumed exactly as the hub's agent
router consumes it (see ``backend/app/routers/agent.py``).

Outputs (all under the harness work dir):
  * benchmark_trials.jsonl       — one JSON object per trial
  * benchmark_results.csv         — flat per-trial table
  * benchmark_summary.json        — aggregate by condition / variant / difficulty
  * provider_status_check.json    — pre-run live provider proof

Usage:
  python run_benchmark.py [--start-from N] [--provider P] [--model M]
                          [--max-trials N] [--out-dir DIR] [--smoke-provider P]
                          [--smoke-model M]

Environment:
  NVIDIA_NIM_API_KEY — read from the environment; litellm picks it up
  automatically.  Must be present for the default NVIDIA NIM run.

Deviation / fallback note:
  If ``NVIDIA_NIM_API_KEY`` is absent on the host, the pre-run assertion halts
  (this is the live-invocation assertion the brief requires — it is working as
  designed).  To produce genuine logs with whatever live provider *is* available
  on the host, override with ``--provider`` / ``--model`` (e.g. the host's live
  Anthropic key via ``--provider anthropic --model claude-3-5-sonnet-20241022``).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

# ── Make the harness CWD-independent ──────────────────────────────────────
# Resolve the work directory (the directory this script lives in) and chdir
# to it so the agent's relative ``data/agent_uploads/...`` paths resolve the
# same way for analyze_file, generate_ui_spec and the prompt.
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK_DIR)

# ── Dependency paths ───────────────────────────────────────────────────────
# litellm is not installed in the shared venv on this host; it was installed
# into a writable target dir.  Put it (and any other deps) on the path first.
DEPS_DIR = os.environ.get("BENCH_DEPS_DIR", "/home/claude-agent/task_b_deps")
if os.path.isdir(DEPS_DIR) and DEPS_DIR not in sys.path:
    sys.path.insert(0, DEPS_DIR)

BACKEND_DIR = "/root/flooding-cholera-gee/backend"

# ── Import the platform's own agent implementation ───────────────────────
# We load ``agent_service.py`` directly via importlib so we avoid executing the
# repo's ``app/services/__init__.py`` (which pulls in geoalchemy2 / earth-engine
# / NASA-GPM services that are not installed and are irrelevant to this
# benchmark).  ``app.database`` is stubbed so we never need a live PostgreSQL
# connection — the agent's ``query_db`` tool is not exercised by visualize
# prompts; ``analyze_file`` and ``generate_ui_spec`` are the real ones.
import types
import importlib.util


def _load_agent_module():
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = [os.path.join(BACKEND_DIR, "app")]
    sys.modules["app"] = app_pkg
    svc_pkg = types.ModuleType("app.services")
    svc_pkg.__path__ = [os.path.join(BACKEND_DIR, "app", "services")]
    sys.modules["app.services"] = svc_pkg

    # Stub app.database so the real (postgres/psycopg2) module never imports.
    db = types.ModuleType("app.database")

    class _DummySession:
        def execute(self, *a, **k):
            raise RuntimeError(
                "query_db is stubbed in the benchmark harness "
                "(no live PostgreSQL); analyze_file/generate_ui_spec are live."
            )

        def close(self):  # noqa: D401
            pass

    db.SessionLocal = lambda: _DummySession()
    db.Base = object
    sys.modules["app.database"] = db

    path = os.path.join(BACKEND_DIR, "app", "services", "agent_service.py")
    spec = importlib.util.spec_from_file_location("app.services.agent_service", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app.services.agent_service"] = mod
    spec.loader.exec_module(mod)
    return mod


_agent_mod = _load_agent_module()
SurveillanceAgent = _agent_mod.SurveillanceAgent
provider_status = _agent_mod.provider_status

# Scoring lives in a sibling module.
sys.path.insert(0, WORK_DIR)
from scoring import (  # noqa: E402
    VARIANTS, CONDITIONS, REPETITIONS, TRUTH, MOCK_MARKERS,
    actual_columns_for, score_trial, detect_mock, parse_ui_spec,
)
from infra_detect import INFRA_ERROR_MARKERS, _is_infra_error  # noqa: E402

# ── Config ─────────────────────────────────────────────────────────────────
DEFAULT_PROVIDER = "nvidia_nim"
# The brief specifies the litellm model string for the nvidia_nim provider.
# SurveillanceAgent._model_name_for_litellm returns a model containing "/" as-is,
# so passing the fully-qualified litellm string yields correct routing.
DEFAULT_MODEL = "nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct"

VARIANTS_DIR = os.path.join(WORK_DIR, "variants")
UPLOADS_DIR = os.path.join(WORK_DIR, "data", "agent_uploads")
ACTIVE_SPEC_PATH = os.path.join(UPLOADS_DIR, "active_ui_spec.json")

TRIALS_JSONL = os.path.join(WORK_DIR, "benchmark_trials.jsonl")
RESULTS_CSV = os.path.join(WORK_DIR, "benchmark_results.csv")
SUMMARY_JSON = os.path.join(WORK_DIR, "benchmark_summary.json")
PROVIDER_CHECK_JSON = os.path.join(WORK_DIR, "provider_status_check.json")

MOCK_TEXT_MARKERS = ("Rate limit reached", "429", "rate_limit", "Too Many Requests")
MAX_RETRIES = 4
INTERTRIAL_SLEEP_S = 2.0


# ── Prompts (mirror the deployed hub's real prompts, paper §3.7/§11) ────────
def build_prompt(variant: str, condition: str) -> str:
    rel_path = f"data/agent_uploads/{variant}.csv"
    base = (
        f"I've uploaded a file '{rel_path}'. Visualize it — build me a "
        f"dashboard showing cases by LGA."
    )
    if condition == "unconstrained":
        return base
    # schema-grounded
    return (
        base + " First call analyze_file to read the file's actual column names. "
        "Use only column names appearing verbatim in that output. "
        "Omit any widget whose required field does not exist."
    )


# ── Provider / live proof ──────────────────────────────────────────────────
def _ensure_uploads():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    src = os.path.join(WORK_DIR, "variants")
    if os.path.isdir(src):
        for f in os.listdir(src):
            if f.endswith(".csv"):
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                s = os.path.join(src, f)
                d = os.path.join(UPLOADS_DIR, f)
                if not os.path.exists(d):
                    with open(s, "rb") as fh1, open(d, "wb") as fh2:
                        fh2.write(fh1.read())


def record_provider_check(provider: str, model: str, allow_no_key: bool) -> dict:
    """Record provider_status() + a 1-token live completion probe + timestamp."""
    import litellm  # noqa: E402

    status = provider_status()
    record = {
        "timestamp_utc": _utcnow(),
        "provider": provider,
        "model": model,
        "provider_status": status,
        "chosen_provider_key_present": status.get(provider, False),
        "live_probe": None,
    }

    def _probe(prov: str, mdl: str) -> dict:
        out: dict[str, Any] = {"provider": prov, "model": mdl}
        try:
            # Use the synchronous client so the probe works whether or not an
            # event loop is already running (record_provider_check is called
            # from inside main_async).
            resp = litellm.completion(
                model=mdl, messages=[{"role": "user", "content": "ping"}],
                max_tokens=1, stream=False,
            )
            out["ok"] = True
            out["response"] = str(resp)[:300]
        except Exception as exc:  # noqa: BLE001
            out["ok"] = False
            out["error"] = f"{type(exc).__name__}: {exc}"[:500]
        return out

    record["live_probe"] = _probe(provider, model)

    with open(PROVIDER_CHECK_JSON, "w") as f:
        json.dump(record, f, indent=2, default=str)

    if not status.get(provider, False):
        msg = (
            f"PROVIDER KEY MISSING: provider_status() reports {provider}=False. "
            f"No trial can be allowed to enter the Mock fallback path. "
            f"Set {provider.upper()}_API_KEY in the environment, or run with a "
            f"live provider via --provider/--model."
        )
        if allow_no_key:
            print(f"[warn] {msg}", file=sys.stderr)
        else:
            print(f"[fatal] {msg}", file=sys.stderr)
            raise SystemExit(2)
    return record


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Trial execution ────────────────────────────────────────────────────────
_TOOL_RE = re.compile(r"Executing tool `([^`]+)` with args: `([^`]*)`")
_SYNTH_RE = re.compile(r"Synthesising response")


async def _run_one_trial(
    agent: SurveillanceAgent, prompt: str, variant: str
) -> dict:
    """Drive one agent.chat() call, collecting the full audit stream."""
    texts: list[str] = []
    thoughts: list[str] = []
    ui_spec_events: list[str] = []
    tool_calls: list[dict] = []
    turns = 0
    synth_seen = 0

    # ensure no stale active spec
    if os.path.exists(ACTIVE_SPEC_PATH):
        os.remove(ACTIVE_SPEC_PATH)

    async for token_type, token in agent.chat(prompt):
        if token_type == "text":
            texts.append(token)
        elif token_type == "thought":
            thoughts.append(token)
            if _SYNTH_RE.search(token):
                synth_seen += 1
            m = _TOOL_RE.search(token)
            if m:
                name = m.group(1)
                args_str = m.group(2)
                try:
                    args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    args = {"_raw": args_str}
                tool_calls.append({"tool": name, "arguments": args})
        elif token_type == "ui_spec":
            ui_spec_events.append(token)

    turns = synth_seen + (1 if any(texts) else 0)

    # Capture the on-disk active_ui_spec.json the agent wrote, then clear it.
    file_spec = None
    if os.path.exists(ACTIVE_SPEC_PATH):
        try:
            with open(ACTIVE_SPEC_PATH) as f:
                file_spec = f.read()
            os.remove(ACTIVE_SPEC_PATH)
        except Exception as exc:  # noqa: BLE001
            file_spec = None

    raw_spec_source = file_spec or (ui_spec_events[-1] if ui_spec_events else None)
    ui_spec = parse_ui_spec(raw_spec_source)

    text_answer = "".join(texts)
    full_stream = "".join(texts + thoughts + ui_spec_events)
    mock_detected = detect_mock(full_stream)

    return {
        "ui_spec_raw": ui_spec,
        "ui_spec_raw_string": raw_spec_source,
        "text_answer": text_answer,
        "thoughts": thoughts,
        "tool_calls": tool_calls,
        "turns": turns,
        "mock_mode_detected": mock_detected,
        "full_stream": full_stream,
    }


# Backwards-compatible alias (old name used by earlier revisions of this file).
_is_rate_limit = _is_infra_error


async def run_trial_with_retries(
    provider: str, model: str, prompt: str, variant: str, trial_id: str
) -> tuple[dict, int, list[str], bool]:
    """Run a trial, retrying infra-error failures with exponential backoff.

    Returns (result_dict, retries, notes, infra_error_excluded).  If all
    retries are exhausted, the last result (possibly an error result) is
    returned with notes describing the failures and infra_error_excluded=True
    — the row is still recorded (paper §3.7: infrastructure failures are
    detected, retried with exponential backoff, and excluded from scoring)
    but the summary/aggregate computations must exclude it.
    """
    notes: list[str] = []
    retries = 0
    last_result: Optional[dict] = None
    for attempt in range(MAX_RETRIES + 1):
        agent = SurveillanceAgent(provider=provider, model=model, history=[])
        exc: Optional[BaseException] = None
        try:
            result = await _run_one_trial(agent, prompt, variant)
        except Exception as e:  # noqa: BLE001
            exc = e
            result = {
                "ui_spec_raw": None, "ui_spec_raw_string": None,
                "text_answer": "", "thoughts": [], "tool_calls": [],
                "turns": 0, "mock_mode_detected": False,
                "full_stream": f"EXC: {type(e).__name__}: {e}",
            }
        if not _is_infra_error(result, exc):
            if retries:
                notes.append(f"recovered after {retries} infra-error retries")
            return result, retries, notes, False
        # infra error → retry with exponential backoff
        retries += 1
        last_result = result
        backoff = min(60, 5 * 2 ** attempt)  # 5,10,20,40,60,...
        msg = (f"infra-error on attempt {attempt + 1} "
               f"({exc or 'stream marker'}); backing off {backoff}s")
        notes.append(msg)
        print(f"[{trial_id}] {msg}", file=sys.stderr)
        await asyncio.sleep(backoff)
    notes.append(f"exhausted {MAX_RETRIES} retries; excluding from scoring as infra error")
    return last_result or result, retries, notes, True


# ── Per-trial record assembly ─────────────────────────────────────────────
CSV_FIELDS = [
    "trial_id", "timestamp_utc", "variant", "condition", "repetition",
    "provider", "model", "prompt_text", "ui_spec_raw", "text_answer",
    "referenced_columns", "grounding", "correct_lga_binding",
    "correct_case_binding", "correct_deaths_binding", "latency_seconds",
    "turns", "tool_calls", "mock_mode_detected", "mock_mode_asserted_ok",
    "retries", "notes", "infra_error_excluded",
]


def assemble_row(
    trial_id: str, variant: str, condition: str, rep: int,
    provider: str, model: str, prompt: str, result: dict,
    latency: float, retries: int, notes: list[str],
    infra_error_excluded: bool = False,
) -> dict:
    actual_cols = actual_columns_for(variant, VARIANTS_DIR)
    scored = score_trial(result.get("ui_spec_raw"), variant, actual_cols)
    mock_detected = result.get("mock_mode_detected", False)
    mock_asserted_ok = not mock_detected  # per-trial assertion: no mock markers

    row = {
        "trial_id": trial_id,
        "timestamp_utc": _utcnow(),
        "variant": variant,
        "condition": condition,
        "repetition": rep,
        "provider": provider,
        "model": model,
        "prompt_text": prompt,
        "ui_spec_raw": result.get("ui_spec_raw"),
        "text_answer": result.get("text_answer", ""),
        "referenced_columns": scored["referenced_columns"],
        "grounding": scored["grounding"],
        "correct_lga_binding": scored["correct_lga_binding"],
        "correct_case_binding": scored["correct_case_binding"],
        "correct_deaths_binding": scored["correct_deaths_binding"],
        "latency_seconds": round(latency, 3),
        "turns": result.get("turns", 0),
        "tool_calls": result.get("tool_calls", []),
        "mock_mode_detected": mock_detected,
        "mock_mode_asserted_ok": mock_asserted_ok,
        "retries": retries,
        "notes": " | ".join(notes),
        "infra_error_excluded": infra_error_excluded,
        # full audit stream (thoughts) kept in JSONL only, not the flat CSV
        "_thoughts": result.get("thoughts", []),
        "_ui_spec_raw_string": result.get("ui_spec_raw_string"),
    }
    return row


def write_jsonl_row(row: dict):
    with open(TRIALS_JSONL, "a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def write_csv_header():
    with open(RESULTS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()


def write_csv_row(row: dict):
    flat = {k: row.get(k) for k in CSV_FIELDS}
    # serialize complex fields for CSV
    flat["ui_spec_raw"] = json.dumps(row.get("ui_spec_raw"), default=str) if row.get("ui_spec_raw") is not None else ""
    flat["referenced_columns"] = json.dumps(row.get("referenced_columns"), default=str)
    flat["tool_calls"] = json.dumps(row.get("tool_calls"), default=str)
    with open(RESULTS_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writerow(flat)


# ── Summary (paper Table 8) ───────────────────────────────────────────────
def build_summary(rows: list[dict]) -> dict:
    def rate(rows_subset, key):
        vals = [r.get(key) for r in rows_subset if r.get(key) is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 4)

    def deaths_rate(rows_subset):
        vals = [r.get("correct_deaths_binding") for r in rows_subset
                if r.get("correct_deaths_binding") is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 4)

    # Infra-error trials are recorded for the audit trail but must not
    # contribute to n or any rate (paper §3.7).
    scoreable_rows = [r for r in rows if not r.get("infra_error_excluded")]

    summary: dict[str, Any] = {
        "total_trials": len(rows),
        "by_condition": {},
        "by_variant": {},
    }
    for cond in CONDITIONS:
        all_sub = [r for r in rows if r["condition"] == cond]
        sub = [r for r in all_sub if not r.get("infra_error_excluded")]
        summary["by_condition"][cond] = {
            "n": len(sub),
            "grounding_rate": rate(sub, "grounding"),
            "lga_binding_rate": rate(sub, "correct_lga_binding"),
            "case_binding_rate": rate(sub, "correct_case_binding"),
            "deaths_binding_rate": deaths_rate(sub),
            "mock_mode_detected_count": sum(1 for r in sub if r.get("mock_mode_detected")),
            "avg_latency_seconds": round(
                sum(r.get("latency_seconds", 0) for r in sub) / len(sub), 3
            ) if sub else None,
            "infra_excluded_count": len(all_sub) - len(sub),
        }
    for v in VARIANTS:
        all_sub = [r for r in rows if r["variant"] == v]
        sub = [r for r in all_sub if not r.get("infra_error_excluded")]
        summary["by_variant"][v] = {
            "n": len(sub),
            "grounding_rate": rate(sub, "grounding"),
            "lga_binding_rate": rate(sub, "correct_lga_binding"),
            "case_binding_rate": rate(sub, "correct_case_binding"),
            "deaths_binding_rate": deaths_rate(sub),
            "infra_excluded_count": len(all_sub) - len(sub),
        }
    summary["infra_excluded_count"] = len(rows) - len(scoreable_rows)
    return summary


def print_summary_table(summary: dict):
    print("\n" + "=" * 78)
    print("Benchmark summary (paper Table 8 analogue)")
    print("=" * 78)
    hdr = (f"{'condition':<18}{'n':>4}{'ground':>9}{'lga':>9}{'case':>9}"
           f"{'deaths':>9}{'mock':>6}{'excluded':>10}")
    print(hdr)
    print("-" * len(hdr))
    for cond in CONDITIONS:
        c = summary["by_condition"].get(cond, {})
        def fmt(x):
            return f"{x:.2%}" if isinstance(x, float) else "  n/a"
        print(
            f"{cond:<18}{c.get('n', 0):>4}"
            f"{fmt(c.get('grounding_rate')):>9}"
            f"{fmt(c.get('lga_binding_rate')):>9}"
            f"{fmt(c.get('case_binding_rate')):>9}"
            f"{fmt(c.get('deaths_binding_rate')):>9}"
            f"{c.get('mock_mode_detected_count', 0):>6}"
            f"{c.get('infra_excluded_count', 0):>10}"
        )
    print("=" * 78)


# ── Orchestration ──────────────────────────────────────────────────────────
def trial_sequence() -> list[tuple[str, str, int, str]]:
    """Deterministic order: variant, condition, rep (no random seeding)."""
    seq = []
    idx = 0
    for variant in VARIANTS:
        for condition in CONDITIONS:
            for rep in REPETITIONS:
                idx += 1
                trial_id = f"t{idx:03d}"
                seq.append((variant, condition, rep, trial_id))
    return seq


async def main_async(args):
    _ensure_uploads()

    provider = args.provider
    model = args.model

    # Pre-run live provider proof (asserts key present → no Mock path).
    check = record_provider_check(provider, model, allow_no_key=args.allow_no_key)
    print(f"[provider] status={check['provider_status']} "
          f"key_present={check['chosen_provider_key_present']} "
          f"probe_ok={check['live_probe'].get('ok') if check.get('live_probe') else 'n/a'}")

    seq = trial_sequence()
    start_idx = args.start_from
    total = len(seq)

    # Fresh outputs (resume rewrites from start_from; to append-resume, keep
    # existing JSONL — here we keep it simple and deterministic per the brief's
    # --start-from semantics: rows < start_from are not recomputed).
    if start_idx <= 1:
        write_csv_header()
        if os.path.exists(TRIALS_JSONL):
            os.remove(TRIALS_JSONL)

    rows: list[dict] = []
    # If resuming, load prior rows so the summary covers the whole run.
    if start_idx > 1 and os.path.exists(TRIALS_JSONL):
        with open(TRIALS_JSONL) as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

    done = 0
    for variant, condition, rep, trial_id in seq:
        idx = int(trial_id[1:])
        if idx < start_idx:
            continue
        if args.max_trials is not None and done >= args.max_trials:
            break

        prompt = build_prompt(variant, condition)
        print(f"\n[{trial_id}] {variant} / {condition} / rep{rep}  (trial {idx}/{total})")
        t0 = time.time()
        result, retries, notes, infra_error_excluded = await run_trial_with_retries(
            provider, model, prompt, variant, trial_id
        )
        latency = time.time() - t0

        # Unhandled-exception safety: if result itself is an error shell, record
        # the error in notes and continue (never abort the run).
        try:
            row = assemble_row(
                trial_id, variant, condition, rep, provider, model,
                prompt, result, latency, retries, notes, infra_error_excluded,
            )
        except Exception as exc:  # noqa: BLE001
            row = {
                "trial_id": trial_id, "timestamp_utc": _utcnow(),
                "variant": variant, "condition": condition, "repetition": rep,
                "provider": provider, "model": model, "prompt_text": prompt,
                "ui_spec_raw": None, "text_answer": result.get("text_answer", ""),
                "referenced_columns": [], "grounding": False,
                "correct_lga_binding": False, "correct_case_binding": False,
                "correct_deaths_binding": TRUTH.get(variant, {}).get("deaths") is None and None,
                "latency_seconds": round(latency, 3), "turns": result.get("turns", 0),
                "tool_calls": result.get("tool_calls", []),
                "mock_mode_detected": result.get("mock_mode_detected", False),
                "mock_mode_asserted_ok": True, "retries": retries,
                "notes": f"assemble_row error: {type(exc).__name__}: {exc}",
                "infra_error_excluded": infra_error_excluded,
                "_thoughts": result.get("thoughts", []),
            }

        write_jsonl_row(row)
        write_csv_row(row)
        rows.append(row)

        # Per-trial live assertion: no Mock markers.
        if row["mock_mode_detected"]:
            print(f"[{trial_id}] !!! MOCK MODE DETECTED — assertion failure", file=sys.stderr)

        done += 1
        grounding = row["grounding"]
        print(f"[{trial_id}] done in {latency:.1f}s  grounding={grounding} "
              f"case={row['correct_case_binding']} lga={row['correct_lga_binding']} "
              f"deaths={row['correct_deaths_binding']} retries={retries}")

        if args.sleep >= 0:
            await asyncio.sleep(args.sleep)

    # Summary
    summary = build_summary(rows)
    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print_summary_table(summary)
    print(f"\nWrote: {TRIALS_JSONL}\n       {RESULTS_CSV}\n       {SUMMARY_JSON}\n"
          f"       {PROVIDER_CHECK_JSON}")
    print(f"Trials recorded this run: {done} / total in file: {len(rows)}")


def parse_args():
    p = argparse.ArgumentParser(description="Surveillance Copilot 72-trial benchmark")
    p.add_argument("--start-from", type=int, default=1,
                   help="1-indexed trial number to start from (resume)")
    p.add_argument("--provider", default=DEFAULT_PROVIDER,
                   help=f"litellm provider id (default {DEFAULT_PROVIDER})")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help="litellm model string (default uses NVIDIA NIM nemotron)")
    p.add_argument("--max-trials", type=int, default=None,
                   help="stop after N trials (smoke testing)")
    p.add_argument("--out-dir", default=WORK_DIR, help="output directory")
    p.add_argument("--sleep", type=float, default=INTERTRIAL_SLEEP_S,
                   help="seconds to sleep between trials (default 2)")
    p.add_argument("--allow-no-key", action="store_true",
                   help="proceed even if the chosen provider key is absent "
                        "(for smoke/demo runs against a fallback provider)")
    return p.parse_args()


def main():
    args = parse_args()
    if args.out_dir and args.out_dir != WORK_DIR:
        os.chdir(args.out_dir)
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n[interrupt] partial results retained.", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
