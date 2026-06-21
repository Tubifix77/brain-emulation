"""Generic experiment runner: run named pipeline configurations (conditions) over
repeated prompts, score each output with pluggable detectors, aggregate, and save.

Usage (see run_register.py / run_self_model.py):

    run_experiment(
        conditions=[Condition("name", node_list), ...],
        prompts={"label": "prompt text", ...},
        detectors={"agency": agency, "register": register},
        n=15,
        out_path=".../results/foo.txt",
    )
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable, Dict, List

from brain.ollama_client import OllamaClient
from brain.pipeline import ChoreographedPipeline

Detector = Callable[[str], Dict]


@dataclass
class Condition:
    name: str
    nodes: list  # list[brain.nodes.Node]


def _aggregate_line(metric: str, vals: list) -> str:
    if all(isinstance(v, bool) for v in vals):
        return f"    {metric:24s}: {sum(vals)}/{len(vals)}"
    return f"    {metric:24s}: mean {sum(vals) / len(vals):.2f}  (max {max(vals)})"


def run_experiment(*, conditions: List[Condition], prompts, detectors: Dict[str, Detector],
                   n: int, out_path: str, client: OllamaClient = None, history=None) -> Dict:
    """Run every (condition x prompt) n times; return {(cond, prompt): [per-run metric dicts]}."""
    client = client or OllamaClient()
    if not isinstance(prompts, dict):
        prompts = {f"p{i + 1}": p for i, p in enumerate(prompts)}

    lines: List[str] = []
    agg: Dict = {}
    t0 = time.time()

    for cond in conditions:
        for plabel, ptext in prompts.items():
            runs: List[Dict] = []
            lines += ["=" * 90,
                      f"CONDITION: {cond.name} | PROMPT: {plabel} | nodes={[nd.key for nd in cond.nodes]}",
                      "=" * 90]
            for i in range(1, n + 1):
                try:
                    trace = ChoreographedPipeline(client, nodes=cond.nodes).run(
                        ptext, on_event=lambda _e: None, history=history)
                    out = trace.final_output
                except Exception as exc:  # noqa: BLE001
                    lines.append(f"[run {i}] ERROR: {exc}")
                    print(f"{cond.name} | {plabel} {i}/{n}: ERROR {exc}", flush=True)
                    continue
                metrics: Dict = {}
                for dname, dfn in detectors.items():
                    for mk, mv in dfn(out).items():
                        metrics[f"{dname}.{mk}"] = mv
                runs.append(metrics)
                flags = [k for k, v in metrics.items() if isinstance(v, bool) and v]
                lines += ["", f"--- run {i} | {flags or 'clean'} ---", out]
                print(f"{cond.name} | {plabel} {i}/{n}: {flags or 'clean'}  ({time.time()-t0:.0f}s)", flush=True)
            agg[(cond.name, plabel)] = runs

    metric_keys = sorted({k for runs in agg.values() for r in runs for k in r})
    summary = ["", "#" * 90, "SUMMARY  (booleans = count/N, numbers = mean)", "#" * 90]
    for (cname, plabel), runs in agg.items():
        summary.append(f"\n[{cname} | {plabel}]  ({len(runs)} runs)")
        for mk in metric_keys:
            vals = [r[mk] for r in runs if mk in r]
            if vals:
                summary.append(_aggregate_line(mk, vals))
    summary.append(f"\nmodel={client.model}  n={n}  total={time.time()-t0:.0f}s")
    lines += summary

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(summary), flush=True)
    print(f"\nFull transcripts -> {out_path}", flush=True)
    return agg
