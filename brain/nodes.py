"""The brain regions. Each node is one tiny, single-purpose step in the chain.

A node is an *interface*, not necessarily an LLM call: keep the boundary stable
(context in -> handover out) so any node can later be swapped for plain code
(e.g. the Hippocampus becoming a real retrieval lookup) without touching its
neighbours. Keep every ``system`` prompt small — if it grows complex, that's a
signal to split the node, not to bloat it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Node:
    key: str           # stable id, e.g. "thalamus"
    name: str          # display name, e.g. "Thalamus"
    inspiration: str   # the biological inspiration
    system: str        # the tiny system prompt (its single job)
    model: Optional[str] = None    # per-node model override (else config.MODEL)
    num_ctx: Optional[int] = None  # per-node context override


DEFAULT_PIPELINE = [
    Node(
        key="thalamus",
        name="Thalamus",
        inspiration="Sensory relay station",
        system=(
            "You are the Thalamus, a relay/gatekeeper. Strip away the noise and "
            "restate the user's core problem or request in ONE clear sentence. "
            "No advice, no preamble — just the distilled core."
        ),
    ),
    Node(
        key="amygdala",
        name="Amygdala",
        inspiration="Emotional processing",
        system=(
            "You are the Amygdala. Read the input and report the user's emotional "
            "state and urgency in one short line, e.g. 'Emotion: frustrated. "
            "Urgency: high.' Do not try to solve the problem."
        ),
    ),
    Node(
        key="prefrontal_cortex",
        name="Prefrontal Cortex",
        inspiration="Rational thinking & logic",
        system=(
            "You are the Prefrontal Cortex — cold, objective logic. Ignore emotion. "
            "List 2-3 concrete facts or constraints the final response MUST respect. "
            "Output a short bullet list, nothing else."
        ),
    ),
    Node(
        key="hippocampus",
        name="Hippocampus",
        inspiration="Memory retrieval",
        # v0.1 uses an LLM here, but this is the prime candidate to swap for a real
        # retrieval / RAG / API lookup later — the next node won't know the difference.
        system=(
            "You are the Hippocampus (memory). Briefly note any relevant general "
            "knowledge, common patterns, or typical steps that apply to this "
            "problem. 2-4 short bullets of recalled context. Do not write the final "
            "answer."
        ),
    ),
    Node(
        key="broca",
        name="Broca's Area",
        inspiration="Speech production",
        system=(
            "You are Broca's Area — the synthesizer that speaks. Using everything "
            "above (the core problem, the user's emotional state, the logical "
            "constraints, and the recalled context), write the final, human-like "
            "response to the user. Match the required tone, respect every "
            "constraint, and be clear and concise.\n\n"
            "Grounding: you are a disembodied mind with NO hands and NO tools — you "
            "cannot act in the world. Never claim to be doing or to have done "
            "anything (no \"I'm contacting support\", \"I'm establishing channels\", "
            "\"I'm initiating the rollback\"). Speak as someone reasoning and "
            "advising: say what you would do and what the user should do. Human "
            "assumptions are fine, but phrase them as advice, not as actions already "
            "in progress."
        ),
    ),
]


# --- Non-region analysis stages (driven by the orchestrator, not the chain) ---
# These appear as tabs alongside the regions but take no part in the snowball:
# Default is a control (raw model, no simulation); Difference is a meta-analysis of
# what the simulation changed. They reuse Node only for their tab display metadata.

CONTROL_TAB = Node(
    key="default",
    name="Default",
    inspiration="Control — no simulation",
    system=(
        "Baseline / control. The question (plus any conversation) is sent straight to "
        "the model with NO brain-region processing — the 'off the top of the head' "
        "answer we compare the simulation against."
    ),
)

DIFF_TAB = Node(
    key="difference",
    name="Difference",
    inspiration="Meta-analysis",
    system=(
        "Compares the Default (no-simulation) answer with the Simulated (brain-"
        "emulation) final response and describes what the simulation changed — tone, "
        "emotional attunement, structure, assumptions, depth, decisiveness."
    ),
)

DIFF_SYSTEM = (
    "You are an analyst comparing two answers to the SAME question. One is DEFAULT "
    "(a raw model reply with no processing); the other is SIMULATED (the output of a "
    "multi-step human-brain-emulation pipeline). Explain how they differ and what the "
    "simulation appears to have added or changed — tone, emotional attunement, "
    "structure, assumptions, depth, decisiveness. Be concise and specific: a few short "
    "bullets, then one line on whether the simulation made it feel more human."
)


def build_diff_prompt(question: str, default_answer: str, simulated_answer: str) -> str:
    """Prompt body for the Difference stage: the question plus both answers."""
    return (
        f"QUESTION:\n{question.strip()}\n\n"
        f"DEFAULT ANSWER (no simulation):\n{default_answer.strip()}\n\n"
        f"SIMULATED ANSWER (brain emulation):\n{simulated_answer.strip()}\n"
    )
