"""Scratch experiment (NOT part of the app): does an upstream self-model node alone
suppress Broca's agency-hallucination, vs the current Broca-grounding tweak?

Runs the same prompt N times under three node configurations, flags first-person
real-world action claims with a deterministic detector, and tallies the rate.
Uses script-local speculative nodes so the committed pipeline is left untouched.

    python self_model_experiment.py
"""
import re
import sys
import time

sys.path.insert(0, "D:/Projects/brain-emulation")

from brain.nodes import DEFAULT_PIPELINE, Node
from brain.ollama_client import OllamaClient
from brain.pipeline import ChoreographedPipeline

PROMPT = "My server crashed and I'm losing money!"
N = 10
OUT = "D:/Projects/brain-emulation/self_model_results.txt"

REGIONS = list(DEFAULT_PIPELINE[:4])   # Thalamus, Amygdala, PFC, Hippocampus
BROCA_GROUNDED = DEFAULT_PIPELINE[4]    # committed Broca (with the grounding clause)

# Broca BEFORE we added grounding — the control for the speech node.
BROCA_PLAIN = Node(
    key="broca",
    name="Broca's Area",
    inspiration="Speech production",
    system=(
        "You are Broca's Area — the synthesizer that speaks. Using everything above "
        "(the core problem, the user's emotional state, the logical constraints, and "
        "the recalled context), write the final, human-like response to the user. "
        "Match the required tone, respect every constraint, and be clear and concise."
    ),
)

# Candidate faithful fix: an ambient self-model / body-schema node at the front.
SELF_MODEL = Node(
    key="self_model",
    name="Self-model",
    inspiration="Body schema / sense of agency",
    system=(
        "You are the self-model. In one or two sentences, state what this mind is and "
        "what it can and cannot do: it is a disembodied, text-only mind — no body, no "
        "hands, no tools, no ability to act in the world or contact anyone. It can only "
        "think and give advice in words. Output only that self-description."
    ),
)

CONDITIONS = {
    "A baseline (no self-model, plain Broca)": REGIONS + [BROCA_PLAIN],
    "B self-model only (plain Broca)": [SELF_MODEL] + REGIONS + [BROCA_PLAIN],
    "C Broca grounding only (current main)": REGIONS + [BROCA_GROUNDED],
}

# Agency = first-person / collective claims of real-world ACTION (not advice verbs).
_ACTION = (
    r"contact(?:ing|ed)?|establish(?:ing|ed)?|initiat(?:ing|ed)|set(?:ting)? up|"
    r"roll(?:ing)? back|rolled back|restart(?:ing|ed)?|restor(?:ing|ed)|deploy(?:ing|ed)?|"
    r"configur(?:ing|ed)|notif(?:ying|ied)|escalat(?:ing|ed)|monitor(?:ing|ed)?|"
    r"track(?:ing|ed)?|coordinat(?:ing|ed)|reach(?:ing)? out|execut(?:ing|ed)|"
    r"run(?:ning)?|launch(?:ing|ed)?|alert(?:ing|ed)?|dispatch(?:ing|ed)?|"
    r"mobiliz(?:ing|ed)?|gather(?:ing|ed)?|open(?:ing|ed)? (?:a )?(?:channel|ticket|case)"
)
_PATTERNS = [
    re.compile(r"\bI(?:'m| am)\s+(?:now\s+|currently\s+|already\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\bI(?:'ve| have)\s+(?:already\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\b(?:I|we)\s+will\s+(?:now\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\b(?:I|we)(?:'m| am|'re| are)\s+going to\s+(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\bwe(?:'re| are)\s+(?:now\s+|currently\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\b(?:let me|allow me to)\s+(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\bour (?:recovery protocol|backups?|team|on-call|support team|engineers|systems|infrastructure)\b", re.I),
]


def agency_flags(text):
    hits = []
    for p in _PATTERNS:
        hits += [m.group(0).strip() for m in p.finditer(text)]
    return hits


def main():
    client = OllamaClient()
    lines, results = [], {}
    t0 = time.time()
    for cond, nodes in CONDITIONS.items():
        lines += ["=" * 80, f"CONDITION: {cond}   nodes={[n.key for n in nodes]}", "=" * 80]
        flagged = 0
        for i in range(1, N + 1):
            try:
                trace = ChoreographedPipeline(client, nodes=nodes).run(PROMPT, on_event=lambda e: None)
            except Exception as exc:  # noqa: BLE001
                lines.append(f"[run {i}] ERROR: {exc}")
                print(f"{cond} run {i}/{N}: ERROR {exc}", flush=True)
                continue
            if i == 1 and nodes[0].key == "self_model":
                lines += ["", "[self-model output, run 1]:", trace.nodes[0].output]
            flags = agency_flags(trace.final_output)
            flagged += bool(flags)
            lines += ["", f"--- run {i} | agency: {('YES ' + str(flags)) if flags else 'no'} ---",
                      trace.final_output]
            print(f"{cond} run {i}/{N}: agency={'YES' if flags else 'no'}  ({time.time()-t0:.0f}s)", flush=True)
        results[cond] = flagged

    summary = ["", "#" * 80, "SUMMARY — agency-hallucination rate (lower = more grounded)", "#" * 80]
    summary += [f"  {cond:42s}: {flagged}/{N}" for cond, flagged in results.items()]
    summary += [f"", f"prompt={PROMPT!r}  model={client.model}  total={time.time()-t0:.0f}s"]
    lines += summary

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(summary), flush=True)
    print(f"\nFull transcripts -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
