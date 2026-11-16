"""Supervised fine-tuning with LoRA on Spider (gold question -> SQL pairs).

    python -m t2s.train_sft --output runs/sft                       # all SFT data
    python -m t2s.train_sft --output runs/sft-25 --fraction 0.25    # data-size ablation
    python -m t2s.train_sft --output runs/sft-all --holdout 0       # also trains on the DPO questions
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .common import DEFAULT_MODEL, seed_everything, train_precision, write_json
from .prompts import messages_for
from .spider import ensure_spider, load_split, split_train, subsample
from .sql import normalize_gold


def build_dataset(root: Path, examples, sample_rows: int):
    from datasets import Dataset

    rows = [
        {
            "prompt": messages_for(root, ex, sample_rows),
            "completion": [{"role": "assistant", "content": normalize_gold(ex.query)}],
        }
        for ex in examples
    ]
    return Dataset.from_list(rows)


def drop_long(dataset, tok, max_length: int):
    """Drop examples that would be truncated, so the model never learns from a cut-off schema or answer."""

    def fits(row):
        ids = tok.apply_chat_template(row["prompt"] + row["completion"], tokenize=True)
        ids = ids["input_ids"] if isinstance(ids, dict) or hasattr(ids, "keys") else ids
        return len(ids) <= max_length

    return dataset.filter(fits)


def lora_config(r: int, alpha: int, dropout: float):
    from peft import LoraConfig

    return LoraConfig(r=r, lora_alpha=alpha, lora_dropout=dropout, target_modules="all-linear",
                      task_type="CAUSAL_LM")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--output", required=True)
    p.add_argument("--data-dir", default="data")
    p.add_argument("--holdout", type=int, default=2000, help="train questions reserved for DPO (0 = use all)")
    p.add_argument("--fraction", type=float, default=1.0, help="fraction of the SFT pool to train on")
    p.add_argument("--limit", type=int, default=None, help="cap on training examples (smoke tests)")
    p.add_argument("--sample-rows", type=int, default=0)
    p.add_argument("--epochs", type=float, default=2.0)
    p.add_argument("--max-steps", type=int, default=-1)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--grad-accum", type=int, default=2)
    p.add_argument("--max-length", type=int, default=1536)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    from transformers import AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    seed_everything(args.seed)
    root = ensure_spider(args.data_dir)
    sft_pool, _ = split_train(load_split(root, "train"), args.holdout, args.seed)
    examples = subsample(sft_pool, args.fraction, args.limit, args.seed)

    tok = AutoTokenizer.from_pretrained(args.model)
    dataset = drop_long(build_dataset(root, examples, args.sample_rows), tok, args.max_length)
    print(f"SFT examples: {len(dataset)} (pool {len(sft_pool)}, fraction {args.fraction}, "
          f"{len(examples) - len(dataset)} dropped as too long)")

    config = SFTConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=0.03,
        logging_steps=10,
        save_strategy="no",
        report_to="none",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_length=args.max_length,
        completion_only_loss=True,
        seed=args.seed,
        **train_precision(),
    )
    trainer = SFTTrainer(
        model=args.model,
        args=config,
        train_dataset=dataset,
        processing_class=tok,
        peft_config=lora_config(args.lora_r, args.lora_alpha, args.lora_dropout),
    )
    start = time.time()
    result = trainer.train()
    trainer.save_model(args.output)
    tok.save_pretrained(args.output)
    write_json(
        Path(args.output) / "train_meta.json",
        {
            "stage": "sft",
            "base_model": args.model,
            "n_train": len(dataset),
            "sft_pool": len(sft_pool),
            "train_loss": result.training_loss,
            "seconds": round(time.time() - start, 1),
            "args": vars(args),
        },
    )
    print(f"Saved LoRA adapter to {args.output}")


if __name__ == "__main__":
    main()
