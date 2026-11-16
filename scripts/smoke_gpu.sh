#!/usr/bin/env bash
# A few minutes on one GPU: every stage with the real model and tiny limits, to catch environment or
# precision problems before the multi-hour run. Writes only under /tmp/t2s-smoke.
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${MODEL:-Qwen/Qwen2.5-Coder-0.5B-Instruct}"
OUT=/tmp/t2s-smoke
rm -rf "$OUT"
quiet() { "$@" 2>&1 | grep -vE "it/s\]|s/it\]|examples/s\]" | tail -n 4; }

quiet python -m t2s.evaluate --model "$MODEL" --tag base --limit 48 --out-dir "$OUT/results"
quiet python -m t2s.train_sft --model "$MODEL" --output "$OUT/sft" --limit 64 --max-steps 4
quiet python -m t2s.make_pairs --model "$MODEL" --adapter "$OUT/sft" --output "$OUT/pairs.jsonl" --limit 16
quiet python -m t2s.train_dpo --model "$MODEL" --adapter "$OUT/sft" --pairs "$OUT/pairs.jsonl" --output "$OUT/dpo" --max-steps 3
quiet python -m t2s.evaluate --model "$MODEL" --adapter "$OUT/dpo" --tag dpo --limit 48 --out-dir "$OUT/results"
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
echo "SMOKE OK"
