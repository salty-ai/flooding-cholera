#!/bin/bash
# Task B — run the 72-trial benchmark on the deployed hub's live provider (NVIDIA NIM).
# Model: nvidia/nemotron-3-super-120b-a12b — live on the account, tool-calling verified.
# NOTE: the hub's frontend-advertised nvidia/llama-3.1-nemotron-70b-instruct returns
# 404 function-not-found (endpoint retired); deepseek-v4-flash is the working
# tool-calling model on the same NIM provider/key.
set -a
source /root/.hermes/.env
set +a
export NVIDIA_NIM_API_KEY="$NVIDIA_API_KEY"
cd /home/claude-agent/task_b
PYTHONPATH=/home/claude-agent/task_b_deps python3 run_benchmark.py \
  --provider nvidia_nim \
  --model "nvidia_nim/nvidia/nemotron-3-super-120b-a12b" ${START_FROM:+--start-from $START_FROM}
echo "BENCH_RUN_EXIT=$?"
