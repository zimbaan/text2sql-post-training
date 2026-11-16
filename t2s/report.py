"""Collect results/*.json into a markdown table and a bar chart.

    python -m t2s.report --runs base sft-25 sft sft-all dpo
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .common import read_json

LABELS = {
    "base": "Base model (no training)",
    "sft-25": "SFT, 25% of data",
    "sft": "SFT, full SFT split",
    "sft-all": "SFT, SFT split + DPO questions (control)",
    "dpo": "SFT + DPO (execution-verified pairs)",
}


def load(results_dir: Path, tags: list[str] | None) -> list[dict]:
    if tags:
        found = [results_dir / f"{t}.json" for t in tags]
        return [read_json(f) for f in found if f.exists()]
    return [read_json(f) for f in sorted(results_dir.glob("*.json")) if not f.name.startswith("summary")]


def table(results: list[dict]) -> str:
    cats = sorted({c for r in results for c in r["by_category"]})
    base = next((r for r in results if r["tag"] == "base"), None)
    head = ["Run", "Execution acc.", "vs base", "SQL errors", *cats]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in results:
        delta = "" if base is None or r is base else f"{(r['execution_accuracy'] - base['execution_accuracy']) * 100:+.1f} pts"
        cells = [
            LABELS.get(r["tag"], r["tag"]),
            f"**{r['execution_accuracy']:.1%}**",
            delta,
            f"{r['exec_error_rate']:.1%}",
            *[f"{r['by_category'][c]['accuracy']:.1%}" if c in r["by_category"] else "" for c in cats],
        ]
        lines.append("| " + " | ".join(cells) + " |")
    n = results[0]["n"] if results else 0
    counts = ", ".join(f"{c}: {results[0]['by_category'][c]['n']}" for c in cats if results and c in results[0]["by_category"])
    lines.append("")
    lines.append(f"Spider {results[0]['split'] if results else 'dev'}, {n} questions ({counts}).")
    return "\n".join(lines)


def chart(results: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [LABELS.get(r["tag"], r["tag"]).replace(" (", "\n(").replace(", ", ",\n", 1) for r in results]
    values = [r["execution_accuracy"] * 100 for r in results]
    fig, ax = plt.subplots(figsize=(1.9 * len(results) + 1, 4.2))
    bars = ax.bar(labels, values, color="#5b7cfa")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center", fontsize=10)
    ax.set_ylabel("Execution accuracy (%)")
    ax.set_ylim(0, max(values + [10]) * 1.15)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results-dir", default="results")
    p.add_argument("--runs", nargs="*", default=None, help="tags in display order")
    args = p.parse_args(argv)
    results_dir = Path(args.results_dir)
    results = load(results_dir, args.runs)
    if not results:
        raise SystemExit(f"No results in {results_dir}")
    md = table(results)
    (results_dir / "summary.md").write_text(md + "\n", encoding="utf-8")
    chart(results, results_dir / "accuracy.png")
    print(md)


if __name__ == "__main__":
    main()
