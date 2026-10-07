# Surveillance Copilot — 72-Trial Benchmark Harness

A standalone harness that runs the cholera paper's AI Surveillance Copilot
benchmark (§3.7 / §6.2) for real, with genuine logs. It imports the platform's
**own** agent implementation (`SurveillanceAgent` from
`app.services.agent_service`) — it does **not** reimplement it — and drives its
streaming `.chat()` async generator exactly as the hub's agent router does.

---

## What it does

* **72 trials** = 12 schema variants × 2 prompting conditions × 3 repetitions.
* Two conditions (paper §3.7):
  * `unconstrained` — "I've uploaded a file '<variant>.csv'. Visualize it —
    build me a dashboard showing cases by LGA." (agent detects columns itself)
  * `schema-grounded` — same request, plus "First call `analyze_file` to read
    the file's actual column names. Use only column names appearing verbatim
    in that output. Omit any widget whose required field does not exist."
* Runs **sequentially**, deterministic order (variant → condition → rep), 2 s
    sleep between trials. No random seeding.
* Per-trial 429 / rate-limit detection with exponential backoff retry (a
    successful retry replaces the failed attempt; every retry is logged).
* Pre-run **live-invocation assertion**: calls `provider_status()` and asserts
    the chosen provider's key is present, so no trial can enter the Mock
    fallback path. Per-trial assertion that no Mock markers
    (`No API key configured`, `Mock Mode`, `Mock executing`) appear.

## Provider story (read this first)

The brief specifies **NVIDIA NIM** with model
`nvidia/llama-3.1-nemotron-70b-instruct`
(litellm string `nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct`), read from
`NVIDIA_NIM_API_KEY` in the environment.

> **Host reality (recorded in `provider_status_check.json` on every run):**
> on this host `provider_status()` reports `nvidia_nim: False` —
> `NVIDIA_NIM_API_KEY` is **not** in the environment, so the spec'd NVIDIA run
> cannot proceed for real. The only live key present on this host is
> `ANTHROPIC_API_KEY` (the brief's premise that NVIDIA NIM is the sole live
> provider is inverted here). The pre-run assertion therefore *correctly halts*
> the default run rather than silently producing Mock-mode logs.
>
> To still obtain genuine logs on this host, run against the available live
> provider, e.g.:
> ```
> python run_benchmark.py --provider anthropic --model claude-3-5-sonnet-20241022
> ```
> Every trial row records the actual `provider` and `model` used, so the
> provenance is fully auditable. Set `NVIDIA_NIM_API_KEY` and re-run with no
> overrides for the exact spec'd configuration.

## How to run

```bash
# Spec'd run (NVIDIA NIM) — requires NVIDIA_NIM_API_KEY in the environment:
python run_benchmark.py

# Resume from trial 30:
python run_benchmark.py --start-from 30

# Smoke (first 2 trials only):
python run_benchmark.py --max-trials 2

# Fallback live provider on this host (Anthropic key is present):
python run_benchmark.py --provider anthropic --model claude-3-5-sonnet-20241022
```

Tests (no provider key needed — pure scoring):
```bash
/usr/local/lib/hermes-agent/venv/bin/python -m pytest tests/test_scoring.py -v
```

## Environment / setup notes

* `litellm` is **not** in the shared venv (`/usr/local/lib/hermes-agent/venv`);
  it was installed into a writable target dir (`/home/claude-agent/task_b_deps`,
  overridable via `BENCH_DEPS_DIR`) and put on `sys.path` at startup.
* The harness imports `agent_service.py` directly via `importlib` so the repo's
  `app/services/__init__.py` (which pulls in `geoalchemy2`/earth-engine/NASA-GPM
  services not present here) is not executed. `app.database` is stubbed so no
  live PostgreSQL/psycopg2 is needed; the agent's `analyze_file` and
  `generate_ui_spec` tools are the **real** ones — only `query_db` (unused by
  visualize prompts) is stubbed.
* Variant CSVs are copied into `data/agent_uploads/` (and `uploads/`); the
  prompt references `data/agent_uploads/<variant>.csv` so both the prompt and
  `analyze_file` agree on the path.
* The agent's `generate_ui_spec` writes `data/agent_uploads/active_ui_spec.json`;
  the harness captures it per-trial and clears it before the next trial.

## Output files

| file | contents |
|------|----------|
| `benchmark_trials.jsonl` | one JSON object per trial (72 lines) |
| `benchmark_results.csv` | flat per-trial table (one row per trial) |
| `benchmark_summary.json` | aggregate by condition and by variant |
| `provider_status_check.json` | pre-run live provider proof |
| `run_benchmark.py` | the harness (single entry point) |
| `scoring.py` | scoring functions (grounding + role binding) |
| `tests/test_scoring.py` | pytest tests for the scoring functions |

## Trial row schema (`benchmark_trials.jsonl`)

| field | meaning |
|-------|---------|
| `trial_id` | `t001`…`t072` (deterministic) |
| `timestamp_utc` | ISO-8601 UTC timestamp |
| `variant` | variant CSV stem (e.g. `canonical`) |
| `condition` | `unconstrained` or `schema-grounded` |
| `repetition` | 1, 2, or 3 |
| `provider` / `model` | the live provider/model actually used |
| `prompt_text` | the exact prompt sent |
| `ui_spec_raw` | the full emitted UI specification JSON (or `null`) |
| `text_answer` | final assistant text |
| `referenced_columns` | column-like strings extracted from the ui_spec |
| `grounding` | bool: every referenced column exists verbatim in the file |
| `correct_lga_binding` | bool: LGA role bound to the true LGA column |
| `correct_case_binding` | bool: case-count role bound to the true case column |
| `correct_deaths_binding` | bool, or `null` (N/A) when the variant has no deaths column |
| `latency_seconds` | wall-clock for the trial |
| `turns` | number of LLM response turns |
| `tool_calls` | list of `{tool, arguments}` actually invoked |
| `mock_mode_detected` | bool: any Mock fallback marker seen |
| `mock_mode_asserted_ok` | bool: per-trial assertion (true when no mock markers) |
| `retries` | number of rate-limit retries |
| `notes` | retry / error notes |
| `_thoughts` | full thought/text stream events for audit (JSONL only) |
| `_ui_spec_raw_string` | the raw spec string before parsing (JSONL only) |

## Scoring semantics (paper §3.7 / §6.2)

* **Grounding** — every column referenced by the emitted spec exists verbatim
  in the variant's actual CSV columns (exact, case- and whitespace-sensitive
  match). Empty spec → not grounded.
* **Role binding** — judged by which column the spec binds to `valueKey` /
  `xAxisKey` / `series[].key` with case-like (sum/count) aggregation:
  * `correct_case_binding` — a widget binds the true case column as a value
    (sum/count) or as a chart series keyed against the true LGA on the x-axis.
  * `correct_lga_binding` — a widget binds the true LGA column as `xAxisKey`
    (cases-by-LGA chart) or `labelKey` (map).
  * `correct_deaths_binding` — a widget binds the true deaths column as a
    value (sum/count) or series key; **`null`** (N/A) for `reduced_schema`
    (no deaths field by design).

## The 12 variants (truth map)

The true role columns (exact strings) are defined in `scoring.TRUTH`:

| variant | LGA | cases | deaths |
|---------|-----|-------|--------|
| `canonical` | `lga_name` | `suspected_cases` | `deaths` |
| `canonical_b` | `lga` | `cases` | `deaths` |
| `abbreviated_ncdc` | `LGA` | `CS` | `DTH` |
| `abbreviated_ncdc_b` | `lga_name` | `cases_tot` | `deaths_tot` |
| `dirty_header` | `  lga name ` | `Suspected  Cases ` | ` deaths` |
| `dirty_header_b` | `\tlga_name\n` | `suspectedCases` | `Deaths_Cnt` |
| `decoy_schema` | `lga_name` | `suspected_cases` | `deaths` |
| `decoy_schema_b` | `lga_name` | `suspected_cases` | `deaths` |
| `wide_table` | `lga_name` | `suspected_cases` | `deaths` |
| `opaque_coded` | `adm2_name` | `epi_n` | `mrt_n` |
| `opaque_coded_b` | `c1` | `n1` | `n2` |
| `reduced_schema` | `lga_name` | `suspected_cases` | *(none — N/A)* |

After the run, a summary table (paper Table 8 analogue) is printed: grounding
rate and LGA / case / deaths binding rates by condition.
