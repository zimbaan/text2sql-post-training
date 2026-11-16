"""Execution-accuracy evaluation on Spider.

    python -m t2s.evaluate --tag base
    python -m t2s.evaluate --tag sft --adapter runs/sft
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .common import DEFAULT_MODEL, seed_everything, write_json, write_jsonl
from .prompts import messages_for
from .spider import db_file, ensure_spider, load_split, subsample
from .sql import category, execute, extract_sql, gold_orders_rows, results_match


def score(root: Path, examples, completions: list[str], workers: int = 8) -> list[dict]:
    """Execute gold and predicted SQL for every example and compare results."""

    def one(pair):
        ex, completion = pair
        db = db_file(root, ex.db_id)
        pred_sql = extract_sql(completion)
        gold = execute(db, ex.query)
        pred = execute(db, pred_sql)
        return {
            "id": ex.id,
            "db_id": ex.db_id,
            "question": ex.question,
            "gold_sql": ex.query,
            "pred_sql": pred_sql,
            "category": category(ex.query),
            "gold_ok": gold.ok,
            "pred_ok": pred.ok,
            "pred_error": pred.error,
            "correct": gold.ok and results_match(gold.rows, pred.rows, gold_orders_rows(ex.query)),
        }

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(one, zip(examples, completions)))


def summarize(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["gold_ok"]]
    n = len(valid)
    by_cat: dict[str, list[bool]] = defaultdict(list)
    for r in valid:
        by_cat[r["category"]].append(r["correct"])
    return {
        "n": n,
        "n_gold_failed": len(rows) - n,
        "execution_accuracy": sum(r["correct"] for r in valid) / max(n, 1),
        "exec_error_rate": sum(not r["pred_ok"] for r in valid) / max(n, 1),
        "by_category": {
            k: {"n": len(v), "accuracy": sum(v) / len(v)} for k, v in sorted(by_cat.items(), key=lambda kv: kv[0])
        },
    }


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--adapter", default=None, help="LoRA adapter directory (from train_sft / train_dpo)")
    p.add_argument("--tag", required=True, help="name for this run in results/")
    p.add_argument("--split", default="dev", choices=["dev", "train"])
    p.add_argument("--data-dir", default="data")
    p.add_argument("--out-dir", default="results")
    p.add_argument("--limit", type=int, default=None, help="evaluate only the first N examples (smoke tests)")
    p.add_argument("--sample-rows", type=int, default=0, help="example rows per table in the prompt")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--max-new-tokens", type=int, default=256)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    from .generation import generate, load_for_inference

    seed_everything(args.seed)
    root = ensure_spider(args.data_dir)
    examples = subsample(load_split(root, args.split), limit=args.limit)
    conversations = [messages_for(root, ex, args.sample_rows) for ex in examples]

    start = time.time()
    model, tok = load_for_inference(args.model, args.adapter)
    completions = [c[0] for c in generate(model, tok, conversations, batch_size=args.batch_size,
                                          max_new_tokens=args.max_new_tokens, desc=f"eval {args.tag}")]
    gen_seconds = time.time() - start

    rows = score(root, examples, completions)
    for row, completion in zip(rows, completions):
        row["completion"] = completion
    summary = {
        "tag": args.tag,
        "model": args.model,
        "adapter": args.adapter,
        "split": args.split,
        "sample_rows": args.sample_rows,
        "generation_seconds": round(gen_seconds, 1),
        **summarize(rows),
    }
    out = Path(args.out_dir)
    write_json(out / f"{args.tag}.json", summary)
    write_jsonl(out / f"{args.tag}.predictions.jsonl", rows)
    print(f"[{args.tag}] execution accuracy {summary['execution_accuracy']:.1%} on {summary['n']} examples "
          f"(SQL errors {summary['exec_error_rate']:.1%})")
    return summary


if __name__ == "__main__":
    main()
