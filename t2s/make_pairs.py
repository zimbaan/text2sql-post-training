"""Build DPO preference pairs by sampling the SFT model and checking each sample by execution.

For every held-out training question we sample K queries and run them against the database:
  * some right, some wrong -> chosen = a correct sample (on-policy), rejected = wrong samples
  * all wrong              -> chosen = the gold query, rejected = wrong samples
  * all right              -> skipped (nothing to learn)

    python -m t2s.make_pairs --adapter runs/sft --output data/pairs.jsonl
"""

from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path

from .common import DEFAULT_MODEL, seed_everything, write_json, write_jsonl
from .prompts import messages_for
from .spider import db_file, ensure_spider, load_split, split_train, subsample
from .sql import execute, extract_sql, gold_orders_rows, normalize_gold, results_match


def judge(db: Path, gold_rows, order_matters: bool, sql: str) -> tuple[bool, str]:
    res = execute(db, sql)
    if not res.ok:
        return False, "error"
    return (True, "correct") if results_match(gold_rows, res.rows, order_matters) else (False, "wrong_result")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--adapter", required=True, help="SFT adapter to sample from")
    p.add_argument("--output", default="data/pairs.jsonl")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--holdout", type=int, default=2000, help="must match the value used for SFT")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--num-samples", type=int, default=8)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--max-pairs-per-question", type=int, default=2)
    p.add_argument("--no-gold-chosen", action="store_true", help="skip questions where every sample is wrong")
    p.add_argument("--sample-rows", type=int, default=0)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    from .generation import generate, load_for_inference

    seed_everything(args.seed)
    rng = random.Random(args.seed)
    root = ensure_spider(args.data_dir)
    _, pref_pool = split_train(load_split(root, "train"), args.holdout, args.seed)
    if not pref_pool:
        raise SystemExit("No held-out questions: run with --holdout > 0 (and the same value used for SFT).")
    examples = subsample(pref_pool, limit=args.limit)
    conversations = [messages_for(root, ex, args.sample_rows) for ex in examples]

    model, tok = load_for_inference(args.model, args.adapter)
    samples = generate(model, tok, conversations, batch_size=args.batch_size, num_samples=args.num_samples,
                       temperature=args.temperature, desc="sampling")

    pairs, outcomes, verdicts = [], Counter(), Counter()
    for ex, conv, outs in zip(examples, conversations, samples):
        db = db_file(root, ex.db_id)
        gold = execute(db, ex.query)
        if not gold.ok:
            outcomes["gold_failed"] += 1
            continue
        order = gold_orders_rows(ex.query)
        correct, wrong = [], []
        for sql in dict.fromkeys(extract_sql(o) for o in outs):  # dedupe, keep order
            ok, verdict = judge(db, gold.rows, order, sql)
            verdicts[verdict] += 1
            (correct if ok else wrong).append(sql)
        if not wrong:
            outcomes["all_correct"] += 1
            continue
        if correct:
            outcomes["mixed"] += 1
            chosen = rng.choice(correct)
        elif args.no_gold_chosen:
            outcomes["all_wrong_skipped"] += 1
            continue
        else:
            outcomes["all_wrong"] += 1
            chosen = normalize_gold(ex.query)
        for rejected in rng.sample(wrong, min(len(wrong), args.max_pairs_per_question)):
            pairs.append(
                {
                    "id": ex.id,
                    "prompt": conv,
                    "chosen": [{"role": "assistant", "content": chosen}],
                    "rejected": [{"role": "assistant", "content": rejected}],
                    "chosen_source": "model" if correct else "gold",
                }
            )

    out = Path(args.output)
    write_jsonl(out, pairs)
    stats = {
        "questions": len(examples),
        "num_samples": args.num_samples,
        "temperature": args.temperature,
        "pairs": len(pairs),
        "pairs_with_model_chosen": sum(p["chosen_source"] == "model" for p in pairs),
        "question_outcomes": dict(outcomes),
        "unique_sample_verdicts": dict(verdicts),
    }
    write_json(out.with_suffix(".stats.json"), stats)
    print(stats)


if __name__ == "__main__":
    main()
