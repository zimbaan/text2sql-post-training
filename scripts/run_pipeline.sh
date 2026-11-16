#!/usr/bin/env bash
# Full experiment on one GPU. Each stage is skipped if its output already exists, so the script can be
# re-run after an interruption.
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-Qwen/Qwen2.5-Coder-0.5B-Instruct}"
HOLDOUT="${HOLDOUT:-2000}"
PY="${PY:-python}"

stage() {  # stage <done-file> <command...>
  local done_file="$1"; shift
  if [[ -e "$done_file" ]]; then echo "skip: $done_file exists"; return; fi
  echo; echo ">>> $*"; "$@"
}

stage results/base.json      $PY -m t2s.evaluate --model "$MODEL" --tag base

stage runs/sft/train_meta.json    $PY -m t2s.train_sft --model "$MODEL" --holdout "$HOLDOUT" --output runs/sft
stage results/sft.json            $PY -m t2s.evaluate --model "$MODEL" --adapter runs/sft --tag sft

stage runs/sft-25/train_meta.json $PY -m t2s.train_sft --model "$MODEL" --holdout "$HOLDOUT" --fraction 0.25 --output runs/sft-25
stage results/sft-25.json         $PY -m t2s.evaluate --model "$MODEL" --adapter runs/sft-25 --tag sft-25

stage data/pairs.jsonl            $PY -m t2s.make_pairs --model "$MODEL" --adapter runs/sft --holdout "$HOLDOUT" --output data/pairs.jsonl
stage runs/dpo/train_meta.json    $PY -m t2s.train_dpo --model "$MODEL" --adapter runs/sft --pairs data/pairs.jsonl --output runs/dpo
stage results/dpo.json            $PY -m t2s.evaluate --model "$MODEL" --adapter runs/dpo --tag dpo

# Control: give plain SFT the DPO questions too, to check that DPO beats simply adding more SFT data.
stage runs/sft-all/train_meta.json $PY -m t2s.train_sft --model "$MODEL" --holdout 0 --output runs/sft-all
stage results/sft-all.json         $PY -m t2s.evaluate --model "$MODEL" --adapter runs/sft-all --tag sft-all

$PY -m t2s.report --runs base sft-25 sft sft-all dpo
