"""Batched generation with Hugging Face transformers (base model plus an optional LoRA adapter)."""

from __future__ import annotations

import math

from tqdm.auto import tqdm

from .common import device, inference_dtype


def load_for_inference(model_name: str, adapter: str | None = None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(adapter or model_name)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=inference_dtype())
    if adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    model.to(device()).eval()
    torch.set_grad_enabled(False)
    return model, tok


def generate(
    model,
    tok,
    conversations: list[list[dict]],
    *,
    batch_size: int = 16,
    max_new_tokens: int = 256,
    num_samples: int = 1,
    temperature: float = 0.0,
    top_p: float = 0.95,
    desc: str = "generating",
) -> list[list[str]]:
    """Return `num_samples` completions per conversation, in input order."""
    import torch
    from transformers import GenerationConfig

    prompts = [tok.apply_chat_template(c, tokenize=False, add_generation_prompt=True) for c in conversations]
    sampling = temperature > 0
    gen_config = GenerationConfig(
        max_new_tokens=max_new_tokens,
        do_sample=sampling,
        temperature=temperature if sampling else None,
        top_p=top_p if sampling else None,
        top_k=None,
        repetition_penalty=1.0,
        num_return_sequences=num_samples,
        eos_token_id=model.generation_config.eos_token_id,
        pad_token_id=tok.pad_token_id,
    )
    # Longest prompts first: batches are tighter and any out-of-memory error shows up immediately.
    order = sorted(range(len(prompts)), key=lambda i: -len(prompts[i]))
    outputs: list[list[str]] = [[] for _ in prompts]
    per_batch = max(1, batch_size // num_samples) if num_samples > 1 else batch_size
    for start in tqdm(range(0, len(order), per_batch), total=math.ceil(len(order) / per_batch), desc=desc):
        idx = order[start : start + per_batch]
        enc = tok([prompts[i] for i in idx], return_tensors="pt", padding=True).to(model.device)
        with torch.inference_mode():
            out = model.generate(**enc, generation_config=gen_config)
        texts = tok.batch_decode(out[:, enc["input_ids"].shape[1] :], skip_special_tokens=True)
        for j, i in enumerate(idx):
            outputs[i] = texts[j * num_samples : (j + 1) * num_samples]
    return outputs
