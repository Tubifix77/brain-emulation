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

from .nodes import DEFAULT_PIPELINE, Node
from .ollama_client import OllamaClient, OllamaError
from .trace import CognitiveTrace

# event types
ACTIVE_NODE = "active_node"
STREAM_CHUNK = "stream_chunk"
NODE_COMPLETE = "node_complete"
PIPELINE_COMPLETE = "pipeline_complete"
ERROR = "error"


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


class ChoreographedPipeline:
    def __init__(self, client: OllamaClient, nodes: Optional[List[Node]] = None) -> None:
        self.client = client
        self.nodes = nodes if nodes is not None else DEFAULT_PIPELINE

    def run(self, user_input: str, on_event: EventHandler) -> CognitiveTrace:
        """Run the full chain. Blocking — call from a worker thread in a GUI."""
        trace = CognitiveTrace(user_input=user_input)
        context = f"USER INPUT:\n{user_input.strip()}\n"
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
