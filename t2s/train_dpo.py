"""DPO on execution-verified preference pairs, continuing from the SFT LoRA adapter.

The SFT adapter keeps training as the policy; TRL keeps a frozen copy of it as the reference model,
so the KL anchor is the SFT model rather than the original base model.

    python -m t2s.train_dpo --adapter runs/sft --pairs data/pairs.jsonl --output runs/dpo
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .common import DEFAULT_MODEL, prepare_trl_for_gpu, read_jsonl, seed_everything, train_precision, write_json


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--adapter", required=True, help="SFT adapter to start from")
    p.add_argument("--pairs", default="data/pairs.jsonl")
    p.add_argument("--output", required=True)
    p.add_argument("--beta", type=float, default=0.1)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--max-steps", type=int, default=-1)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--max-length", type=int, default=1536)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    import torch
    from datasets import Dataset
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer

    seed_everything(args.seed)
    prepare_trl_for_gpu()
    rows = read_jsonl(Path(args.pairs))
    if not rows:
        raise SystemExit(f"No pairs in {args.pairs}")
    dataset = Dataset.from_list([{k: r[k] for k in ("prompt", "chosen", "rejected")} for r in rows])

    tok = AutoTokenizer.from_pretrained(args.adapter)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    base = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32)
    model = PeftModel.from_pretrained(base, args.adapter, is_trainable=True)

    config = DPOConfig(
        output_dir=args.output,
        beta=args.beta,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=0.05,
        logging_steps=10,
        save_strategy="no",
        report_to="none",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_length=args.max_length,
        seed=args.seed,
        **train_precision(),
    )
    trainer = DPOTrainer(model=model, ref_model=None, args=config, train_dataset=dataset, processing_class=tok)
    start = time.time()
    result = trainer.train()
    trainer.model.save_pretrained(args.output, selected_adapters=["default"])
    tok.save_pretrained(args.output)
    final_logs = [log for log in trainer.state.log_history if "rewards/accuracies" in log]
    write_json(
        Path(args.output) / "train_meta.json",
        {
            "stage": "dpo",
            "base_model": args.model,
            "init_adapter": args.adapter,
            "n_pairs": len(dataset),
            "train_loss": result.training_loss,
            "last_logged": final_logs[-1] if final_logs else None,
            "seconds": round(time.time() - start, 1),
            "args": vars(args),
        },
    )
    print(f"Saved DPO adapter to {args.output}")


if __name__ == "__main__":
    main()
