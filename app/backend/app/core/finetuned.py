"""In-process inference for the post-trained text-to-SQL model.

The model is Qwen2.5-Coder-0.5B-Instruct with the LoRA adapter trained in this repo (SFT, then DPO on
execution-verified pairs; see the repo README). It was trained on one prompt format, so it is called with
exactly that format: the system prompt below, then the database's CREATE TABLE statements and the question.
It answers with plain SQL rather than the JSON plan the general-purpose models return.

torch / transformers / peft are optional dependencies (`pip install -e ".[finetuned]"`). Without them, or
without the adapter files, the model simply isn't offered.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import math
import re
import threading
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Must match the training prompt (t2s/prompts.py) exactly.
SYSTEM_PROMPT = (
    "You are an expert in SQLite. Given a database schema and a question, write one SQLite query that "
    "answers the question. Reply with only the SQL query and no explanation."
)

_FENCE = re.compile(r"```(?:sql|sqlite)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def build_user_prompt(schema_ddl: str, question: str) -> str:
    return f"Database schema:\n{schema_ddl}\n\nQuestion: {question}"


def _split_outside_quotes(sql: str) -> list[str]:
    parts, buf, quote = [], [], None
    for ch in sql:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
            buf.append(ch)
        elif ch == ";":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _collapse_whitespace(sql: str) -> str:
    out, quote, prev_space = [], None, False
    for ch in sql.strip():
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            prev_space = False
        elif ch.isspace():
            if not prev_space:
                out.append(" ")
            prev_space = True
        else:
            out.append(ch)
            prev_space = False
    return "".join(out).strip()


def extract_sql(text: str) -> str:
    """Pull a single SQL statement out of a model completion (same rules as training-time evaluation)."""
    text = text.strip()
    match = _FENCE.search(text)
    if match:
        text = match.group(1)
    elif text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    text = re.sub(r"^\s*(sql|sqlite)\s*:\s*", "", text, flags=re.IGNORECASE)
    statements = _split_outside_quotes(text)
    return _collapse_whitespace(statements[0]) if statements else ""


def dependencies_installed() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ("torch", "transformers", "peft"))


class FinetunedSQLModel:
    """Loads the base model plus LoRA adapter once, merges them, and generates SQL greedily."""

    def __init__(self, name: str, base_model: str, adapter_path: str, max_new_tokens: int = 256):
        self.name = name
        self.base_model = base_model
        self.adapter_path = Path(adapter_path)
        self.max_new_tokens = max_new_tokens
        self._model = None
        self._tokenizer = None
        self._load_lock = threading.Lock()
        self._generate_lock = threading.Lock()

    @property
    def available(self) -> bool:
        return (
            (self.adapter_path / "adapter_config.json").exists()
            and (self.adapter_path / "adapter_model.safetensors").exists()
            and dependencies_installed()
        )

    def load(self) -> None:
        """Load and merge the model (idempotent). Called on first use, or at startup to warm up."""
        with self._load_lock:
            if self._model is not None:
                return
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32
            logger.info(f"Loading {self.base_model} + adapter {self.adapter_path} on {device}")
            tokenizer = AutoTokenizer.from_pretrained(self.base_model)
            base = AutoModelForCausalLM.from_pretrained(self.base_model, dtype=dtype)
            model = PeftModel.from_pretrained(base, str(self.adapter_path)).merge_and_unload()
            # Drop the base model's sampling defaults (temperature, top_p, ...): decoding here is greedy.
            model.generation_config = GenerationConfig(
                eos_token_id=model.generation_config.eos_token_id,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
            model.to(device).eval()
            self._tokenizer, self._model = tokenizer, model
            logger.info("Post-trained text-to-SQL model loaded")

    def generate(self, schema_ddl: str, question: str) -> Tuple[str, Optional[float]]:
        """Return (raw completion, confidence), where confidence is the geometric-mean token probability."""
        # Load first: it holds the lock that also covers the heavy imports, so a startup preload running in
        # another thread can't race this request on importing transformers.
        self.load()
        import torch
        from transformers import GenerationConfig

        tok, model = self._tokenizer, self._model
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(schema_ddl, question)},
        ]
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        enc = tok(prompt, return_tensors="pt").to(model.device)
        # Greedy decoding, as in evaluation. A fresh config so the base model's sampling defaults don't apply.
        config = GenerationConfig(
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            repetition_penalty=1.0,
            eos_token_id=model.generation_config.eos_token_id,
            pad_token_id=tok.pad_token_id or tok.eos_token_id,
            return_dict_in_generate=True,
            output_scores=True,
        )
        with self._generate_lock, torch.inference_mode():
            out = model.generate(**enc, generation_config=config)
        new_tokens = out.sequences[0, enc["input_ids"].shape[1] :]
        text = tok.decode(new_tokens, skip_special_tokens=True)

        confidence = None
        try:
            scores = model.compute_transition_scores(out.sequences, out.scores, normalize_logits=True)[0]
            finite = scores[torch.isfinite(scores)]
            if finite.numel():
                confidence = float(math.exp(finite.float().mean().item()))
        except Exception as e:  # noqa: BLE001 - confidence is a nice-to-have
            logger.debug(f"Could not compute confidence: {e}")
        return text, confidence

    async def generate_sql(self, schema_ddl: str, question: str) -> Tuple[str, str, Optional[float]]:
        """Async wrapper: returns (extracted SQL, raw completion, confidence)."""
        raw, confidence = await asyncio.to_thread(self.generate, schema_ddl, question)
        return extract_sql(raw), raw, confidence


_finetuned: Optional[FinetunedSQLModel] = None


def get_finetuned_model() -> Optional[FinetunedSQLModel]:
    """The configured fine-tuned model, or None when disabled or not installed."""
    global _finetuned
    settings = get_settings()
    if not settings.finetuned_enabled:
        return None
    if _finetuned is None:
        _finetuned = FinetunedSQLModel(
            name=settings.finetuned_model_name,
            base_model=settings.finetuned_base_model,
            adapter_path=settings.finetuned_adapter_path,
            max_new_tokens=settings.finetuned_max_new_tokens,
        )
    return _finetuned if _finetuned.available else None


def is_finetuned_model(model: Optional[str]) -> bool:
    finetuned = get_finetuned_model()
    return bool(model) and finetuned is not None and model == finetuned.name
