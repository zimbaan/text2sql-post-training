"""Small shared helpers: device/precision selection, seeding, JSON I/O."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"


def seed_everything(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def native_bf16() -> bool:
    """True on Ampere or newer. (`torch.cuda.is_bf16_supported()` also counts slow emulation, e.g. on a T4.)"""
    import torch

    return torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8


def train_precision() -> dict[str, bool]:
    """Mixed-precision flags for the Trainer: bf16 on Ampere+, fp16 on T4/P100, full fp32 on CPU."""
    import torch

    if not torch.cuda.is_available():
        return {"bf16": False, "fp16": False}
    if native_bf16():
        return {"bf16": True, "fp16": False}
    return {"bf16": False, "fp16": True}


def inference_dtype():
    import torch

    if not torch.cuda.is_available():
        return torch.float32
    return torch.bfloat16 if native_bf16() else torch.float16


def prepare_trl_for_gpu() -> None:
    """TRL's fused LM-head kernel asks cuBLAS for fp32 output from half-precision inputs, which needs compute
    capability 8.0+. On older GPUs (T4, P100) make it upcast to fp32 before the matmul instead."""
    import torch

    if torch.cuda.is_available() and not native_bf16():
        from trl.kernels import chunked_logprob

        chunked_logprob._MM_OUT_DTYPE = False


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
