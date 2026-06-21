"""Unit tests for the choreographed pipeline — no network, no Ollama, no display.

Uses a fake streaming client so we can verify the event sequence, the growing
context snowball, and the cognitive trace deterministically. Runs either under
pytest or directly: ``python tests/test_pipeline.py``.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.nodes import DEFAULT_PIPELINE  # noqa: E402
from brain.ollama_client import OllamaError  # noqa: E402
from brain.pipeline import (  # noqa: E402
    ACTIVE_NODE,
    ERROR,
    NODE_COMPLETE,
    PIPELINE_COMPLETE,
    STREAM_CHUNK,
    ChoreographedPipeline,
)


class FakeClient:
    """Returns a canned, word-streamed response per call, in order."""

    model = "fake"

    def __init__(self, responses):
        self.responses = responses
        self.prompts = []

    def stream_generate(self, prompt, system=None, model=None, num_ctx=None):
        self.prompts.append(prompt)
        text = self.responses[len(self.prompts) - 1]
        for word in text.split():
            yield word + " "


def test_pipeline_emits_events_and_grows_context():
    responses = [
        "core problem distilled",
        "Emotion: panic. Urgency: high.",
        "- be fast - avoid jargon",
        "- standard recovery steps apply",
        "Here is the final reassuring answer.",
    ]
    client = FakeClient(responses)
    pipe = ChoreographedPipeline(client)
    events = []

    trace = pipe.run("My server crashed!", on_event=events.append)

    n = len(DEFAULT_PIPELINE)
    assert sum(e.type == ACTIVE_NODE for e in events) == n
    assert sum(e.type == NODE_COMPLETE for e in events) == n
    assert sum(e.type == STREAM_CHUNK for e in events) >= n
    assert sum(e.type == PIPELINE_COMPLETE for e in events) == 1
    assert events[-1].type == PIPELINE_COMPLETE

    # the snowball must accumulate every region's handover plus the user input
    final_context = events[-1].context
    assert "USER INPUT:" in final_context
    for node in DEFAULT_PIPELINE:
        assert f"[{node.name}]" in final_context

    # each node only ever saw a context at least as big as the one before it
    sizes = [len(p) for p in client.prompts]
    assert sizes == sorted(sizes)

    # the trace mirrors the run
    d = trace.to_dict()
    assert d["Input"] == "My server crashed!"
    assert len(d["Trace"]) == n
    assert d["Final_Output"] == "Here is the final reassuring answer."
    assert events[-1].text == d["Final_Output"]


def test_pipeline_stops_on_error():
    class BoomClient:
        model = "boom"

        def stream_generate(self, prompt, system=None, model=None, num_ctx=None):
            raise OllamaError("Ollama is down")

    events = []
    trace = ChoreographedPipeline(BoomClient()).run("hello", on_event=events.append)

    assert any(e.type == ERROR for e in events)
    assert not any(e.type == PIPELINE_COMPLETE for e in events)
    assert trace.final_output == ""


if __name__ == "__main__":
    test_pipeline_emits_events_and_grows_context()
    test_pipeline_stops_on_error()
    print("OK — all pipeline smoke tests passed.")
