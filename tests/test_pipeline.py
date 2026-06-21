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
    RUN_COMPLETE,
    STREAM_CHUNK,
    ChoreographedPipeline,
    build_seed_context,
    run_experiment,
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


def test_continue_conversation_includes_history():
    seed = build_seed_context(
        "and now?", history=[{"user": "server down", "assistant": "try a restart"}]
    )
    assert "CONVERSATION SO FAR" in seed
    assert "server down" in seed and "try a restart" in seed
    assert "and now?" in seed

    client = FakeClient(["a", "b", "c", "d", "e"])
    ChoreographedPipeline(client).run(
        "follow-up question",
        on_event=lambda _e: None,
        history=[{"user": "orig q", "assistant": "orig answer"}],
    )
    # the first region must have seen the prior turn plus the new message
    assert "orig q" in client.prompts[0]
    assert "orig answer" in client.prompts[0]
    assert "follow-up question" in client.prompts[0]


def test_run_experiment_runs_default_then_chain_then_difference():
    responses = [
        "DEFAULT_BASELINE",                                       # Default (control)
        "core problem", "panic high", "constraints", "recalled",  # 5 regions
        "SIMULATED_FINAL",                                        # Broca
        "DIFF_ANALYSIS",                                          # Difference
    ]
    client = FakeClient(responses)
    pipe = ChoreographedPipeline(client)
    events = []

    result = run_experiment(client, pipe, "My server crashed!", on_event=events.append)

    active = [e.node_name for e in events if e.type == ACTIVE_NODE]
    assert active[0] == "Default"        # baseline runs first
    assert active[-1] == "Difference"    # diff runs last
    assert events[-1].type == RUN_COMPLETE

    # the Difference stage must have seen BOTH answers
    diff_prompt = client.prompts[-1]
    assert "DEFAULT_BASELINE" in diff_prompt
    assert "SIMULATED_FINAL" in diff_prompt

    trace, default_answer, difference = result
    assert default_answer == "DEFAULT_BASELINE"
    assert difference == "DIFF_ANALYSIS"
    assert trace.final_output == "SIMULATED_FINAL"


if __name__ == "__main__":
    test_pipeline_emits_events_and_grows_context()
    test_pipeline_stops_on_error()
    test_continue_conversation_includes_history()
    test_run_experiment_runs_default_then_chain_then_difference()
    print("OK — all pipeline smoke tests passed.")
