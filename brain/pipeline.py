"""The choreographed pipeline: run each region in sequence, growing a shared
context "snowball" and emitting events the UI (or a future web client) can follow.

The pipeline is UI-agnostic. It only calls ``on_event(PipelineEvent)``; the caller
decides what to do with each event — drive a Tkinter view, push SSE frames to a
browser, log to disk, etc. This keeps the choreographed-vs-orchestrated and the
Tkinter-vs-web choices independent of the reasoning logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

from .nodes import (
    CONTROL_TAB,
    DEFAULT_PIPELINE,
    DIFF_SYSTEM,
    DIFF_TAB,
    Node,
    build_diff_prompt,
)
from .ollama_client import OllamaClient, OllamaError
from .trace import CognitiveTrace

# event types
ACTIVE_NODE = "active_node"
STREAM_CHUNK = "stream_chunk"
NODE_COMPLETE = "node_complete"
PIPELINE_COMPLETE = "pipeline_complete"
ERROR = "error"
RUN_COMPLETE = "run_complete"


@dataclass
class PipelineEvent:
    type: str
    node_key: Optional[str] = None
    node_name: Optional[str] = None
    text: str = ""      # chunk text, node output, final output, or error message
    context: str = ""   # the accumulated snowball after this step

    def to_dict(self) -> dict:
        return asdict(self)


EventHandler = Callable[[PipelineEvent], None]


def build_seed_context(user_input: str, history: Optional[List[dict]] = None) -> str:
    """Build the first region's initial context.

    With no history this is just the user's message. With history (a list of
    ``{"user", "assistant"}`` turns) it prepends the conversation so a follow-up
    run continues in context instead of starting cold.
    """
    history = history or []
    if not history:
        return f"USER INPUT:\n{user_input.strip()}\n"
    lines = ["CONVERSATION SO FAR:"]
    for turn in history:
        lines.append(f"  User: {turn['user']}")
        lines.append(f"  Assistant: {turn['assistant']}")
    lines.append("")
    lines.append(f"USER'S NEW MESSAGE:\n{user_input.strip()}")
    return "\n".join(lines) + "\n"


class ChoreographedPipeline:
    def __init__(self, client: OllamaClient, nodes: Optional[List[Node]] = None) -> None:
        self.client = client
        self.nodes = nodes if nodes is not None else DEFAULT_PIPELINE

    def run(
        self,
        user_input: str,
        on_event: EventHandler,
        history: Optional[List[dict]] = None,
    ) -> CognitiveTrace:
        """Run the full chain. Blocking — call from a worker thread in a GUI.

        Pass ``history`` (a list of ``{"user", "assistant"}`` turns) to continue a
        conversation: the prior turns are folded into the first region's input so
        the chain reasons with the original question and its earlier answer in view.
        """
        trace = CognitiveTrace(user_input=user_input)
        context = build_seed_context(user_input, history)
        output = ""

        for node in self.nodes:
            on_event(PipelineEvent(ACTIVE_NODE, node.key, node.name))

            chunks: List[str] = []
            try:
                for chunk in self.client.stream_generate(
                    prompt=context,
                    system=node.system,
                    model=node.model,
                    num_ctx=node.num_ctx,
                ):
                    chunks.append(chunk)
                    on_event(PipelineEvent(STREAM_CHUNK, node.key, node.name, text=chunk))
            except OllamaError as exc:
                on_event(PipelineEvent(ERROR, node.key, node.name, text=str(exc)))
                return trace

            output = "".join(chunks).strip()
            trace.add(node, output)

            # grow the snowball: append this region's handover for the next region
            context += f"\n[{node.name}] {output}\n"
            on_event(
                PipelineEvent(NODE_COMPLETE, node.key, node.name, text=output, context=context)
            )

        trace.final_output = output
        on_event(PipelineEvent(PIPELINE_COMPLETE, text=output, context=context))
        return trace


def _stream_collect(client, on_event, tab, prompt, system):
    """Stream one model call into STREAM_CHUNK events; return its text (None on error)."""
    chunks: List[str] = []
    try:
        for chunk in client.stream_generate(prompt=prompt, system=system):
            chunks.append(chunk)
            on_event(PipelineEvent(STREAM_CHUNK, tab.key, tab.name, text=chunk))
    except OllamaError as exc:
        on_event(PipelineEvent(ERROR, tab.key, tab.name, text=str(exc)))
        return None
    return "".join(chunks).strip()


def run_experiment(
    client: OllamaClient,
    pipe: ChoreographedPipeline,
    user_input: str,
    on_event: EventHandler,
    history: Optional[List[dict]] = None,
):
    """Run the full comparison: baseline (no simulation) -> brain chain -> difference.

    Emits the same PipelineEvents as the chain (so the UI renders every stage in a tab
    uniformly), with two extra stages keyed 'default' and 'difference', plus a terminal
    RUN_COMPLETE. Returns ``(trace, default_answer, difference)``, or None if a step
    errored (an ERROR event is emitted in that case).
    """
    seed = build_seed_context(user_input, history)

    # 1) Default — the raw model: same input, no system prompt, no brain processing.
    on_event(PipelineEvent(ACTIVE_NODE, CONTROL_TAB.key, CONTROL_TAB.name))
    default_answer = _stream_collect(client, on_event, CONTROL_TAB, prompt=seed, system=None)
    if default_answer is None:
        return None
    on_event(PipelineEvent(NODE_COMPLETE, CONTROL_TAB.key, CONTROL_TAB.name, text=default_answer))

    # 2) The brain simulation (emits region events + PIPELINE_COMPLETE).
    trace = pipe.run(user_input, on_event, history)
    if not trace.final_output:
        return None  # a region errored; ERROR already emitted

    # 3) Difference — feed the question and BOTH answers back, analyse the gap.
    on_event(PipelineEvent(ACTIVE_NODE, DIFF_TAB.key, DIFF_TAB.name))
    difference = _stream_collect(
        client,
        on_event,
        DIFF_TAB,
        prompt=build_diff_prompt(user_input, default_answer, trace.final_output),
        system=DIFF_SYSTEM,
    )
    if difference is None:
        return None
    on_event(PipelineEvent(NODE_COMPLETE, DIFF_TAB.key, DIFF_TAB.name, text=difference))

    on_event(PipelineEvent(RUN_COMPLETE, text=trace.final_output))
    return trace, default_answer, difference
