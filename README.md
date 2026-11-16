# Text-to-SQL post-training: SFT and execution-verified DPO

How much do supervised fine-tuning (SFT) and preference optimization (DPO) improve a small open model at
writing SQL, and is DPO on execution-checked preference pairs a better use of extra questions than more SFT?

This repo fine-tunes **Qwen2.5-Coder-0.5B-Instruct** on the [Spider](https://yale-lily.github.io/spider)
benchmark with LoRA, mines preference pairs by running the model's own SQL against the databases, trains DPO
on those pairs, and evaluates every stage by **execution accuracy** on the Spider dev set.

## Results

_Pending the full run. `python -m t2s.report` writes the table to `results/summary.md` and a chart to
`results/accuracy.png`._

## Experiments

| Run | What changes | Question it answers |
|---|---|---|
| `base` | No training | Where does the model start? |
| `sft-25` | SFT on 25% of the SFT split | How much does SFT data size matter? |
| `sft` | SFT on the full SFT split (6,659 questions) | What does SFT alone achieve? |
| `dpo` | `sft` + DPO on pairs mined from 2,000 held-out questions | Does execution-verified DPO add on top of SFT? |
| `sft-all` | SFT on all 8,659 questions, including the 2,000 used for DPO | Control: is DPO better than just adding those questions to SFT? |

## Method

**Data.** Spider has 8,659 training and 1,034 dev questions over 200 SQLite databases. A seeded split holds
out 2,000 training questions for preference mining; SFT never sees them (except in the `sft-all` control).
The dev set is used only for the final evaluation.

**Prompt.** The system prompt asks for a single SQLite query. The user turn contains the database's
`CREATE TABLE` statements followed by the question. Training examples longer than 1,536 tokens are dropped
rather than truncated.

**SFT.** LoRA (r=16, alpha=32, all linear layers) trained with TRL's `SFTTrainer` for 2 epochs at
learning rate 2e-4 with a cosine schedule. Loss is computed on the SQL answer tokens only.

**Preference mining.** For each held-out question the SFT model samples 8 queries (temperature 1.0). Each
distinct query is executed against the database and compared with the gold result:

- some right, some wrong: chosen = a correct sample (on-policy), rejected = up to 2 wrong samples
- all wrong: chosen = the gold query, rejected = up to 2 wrong samples
- all right: skipped

Counts of each outcome are written to `data/pairs.stats.json`.

**DPO.** TRL's `DPOTrainer` continues training the SFT adapter, with a frozen copy of the SFT adapter as the
reference model (beta 0.1, learning rate 2e-5, 1 epoch).

**Evaluation.** Greedy decoding. A prediction counts as correct when it returns the same rows as the gold
query: compared as a multiset (in order only if the gold query has `ORDER BY`), ignoring column order, with
floats rounded to 4 decimals. Queries run on a read-only connection with a 10-second timeout. Accuracy is
also broken down by query structure (single table, group/order, join, nested/set operations).

## Reproduce

**Kaggle (free GPU).** Create a notebook from `notebooks/kaggle_pipeline.ipynb`, set the accelerator to a
GPU (T4 or P100) and turn on internet, then *Save & Run All*. Each stage is skipped if its output already
exists, so a re-run continues where it stopped.

**Any Linux machine with an NVIDIA GPU:**

```bash
pip install -r requirements.txt
bash scripts/run_pipeline.sh
```

**Single steps:**

```bash
python -m t2s.evaluate --tag base
python -m t2s.train_sft --output runs/sft
python -m t2s.evaluate --adapter runs/sft --tag sft
python -m t2s.make_pairs --adapter runs/sft --output data/pairs.jsonl
python -m t2s.train_dpo --adapter runs/sft --pairs data/pairs.jsonl --output runs/dpo
python -m t2s.evaluate --adapter runs/dpo --tag dpo
python -m t2s.report --runs base sft dpo
```

Spider is downloaded on first use from a pinned copy of the official release and checked against its
SHA-256. Unit tests for SQL extraction, execution and result matching run on CPU: `pytest -q`.

## Layout

```
t2s/
  spider.py       download, splits, held-out set
  prompts.py      schema text and chat messages
  sql.py          SQL extraction, sandboxed execution, result comparison
  generation.py   batched generation (base model + optional LoRA adapter)
  evaluate.py     execution accuracy on Spider dev
  train_sft.py    LoRA SFT
  make_pairs.py   execution-verified preference pairs
  train_dpo.py    DPO from the SFT adapter
  report.py       results table and chart
scripts/run_pipeline.sh
notebooks/kaggle_pipeline.ipynb
tests/
```

## Limitations

- The metric is a simplified execution match, not the official Spider test-suite evaluation, so numbers are
  not directly comparable with leaderboard results.
- Results come from a single seed.
- A 0.5B model was chosen to fit a free GPU; larger models are a one-flag change (`--model`).

## Data and model licenses

Spider is released under CC BY-SA 4.0 (Yu et al., *Spider: A Large-Scale Human-Labeled Dataset for Complex
and Cross-Domain Semantic Parsing and Text-to-SQL Task*, EMNLP 2018). Qwen2.5-Coder is released under
Apache 2.0.
