# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**v0.1 prototype — runnable.** The choreographed pipeline, an Ollama streaming
client, the five seed brain regions, and the Tkinter tri-pane / auto-focus UI are
implemented and verified (no-network unit tests plus a live `gemma4:e2b` run). Runs
can be chained into a conversation (the "Continue conversation" toggle re-injects the
prior turn via `build_seed_context`), and the handover/final panes render basic
markdown (`brain/mdtext.py`). It's
still an early prototype: one linear pipeline, no orchestrator yet, and the
Hippocampus is still an LLM prompt rather than real retrieval. Keep this file in sync
as the code grows.

## What this is

A **cognitive assembly line**: an orchestration program that splits one "thinking"
task across a chain of small sub-processes, where each process emulates a
scientifically identified part of the human brain (medical / physical / psychological).
Each process has a *very small job* and a *very small prompt*, inherits its context
from the prior process, and hands its result to the next — like a production line
that ends in a human-like conclusion.

The design bet: you don't need one large model doing heavy lifting. You need many
tiny, explicit steps plus clean context handoff. This makes the AI's "thinking" a
transparent, debuggable modular line instead of a black box.

**Design goal — fidelity, not correctness.** The aim is to *emulate human cognition*,
not to maximise answer quality. A non-specialist human answers off the top of their
head — making assumptions, skipping clarifying questions, sometimes plain wrong — and
that is exactly what the chain should do. It's a feature, not a bug to fix. So resist
the reflex to bolt on truth-seeking machinery (web search, claim-verification,
RAG-for-accuracy) to make answers "better"; that's a different project. Swapping a node
to code is still fair when it emulates a region's *function* (e.g. the Hippocampus
becoming real memory retrieval) — but never as a fact-checker on the output. Success is
how human-like the *process and conclusion* feel, not whether the answer is optimal.

Two parts matter, roughly equally:

1. **The pipeline** — the brain-region processing chain (below).
2. **The UI** — the larger/harder part. A live "functional-MRI" view of thought
   moving across brain regions (see [The UI](#the-ui-the-heart-of-the-app)).

## Architecture

### Pipeline patterns: choreographed vs. orchestrated

Support (or at least design for) both:

- **Choreographed pipeline (no orchestrator)** — node A finishes, appends its output
  to the shared context, triggers node B. A linear relay/production line. Simple,
  low-latency, deterministic. Rigid: every input traverses the full chain even when a
  node has nothing to add. **This is the MVP target — build this first.**
- **Orchestrated hub (with orchestrator)** — a central router (think *Thalamus* /
  executive function) receives input and dynamically decides which region runs next,
  getting results back between hops. Flexible, can loop to "re-think". More complex;
  the orchestrator itself needs a larger prompt to manage traffic.

### Node taxonomy (the brain regions)

Each node is one stage. Keep prompts tiny and single-purpose. The default linear
blueprint:

| Node | Biological inspiration | Role | Tiny prompt (example) |
| --- | --- | --- | --- |
| **Thalamus** | Sensory relay station | Gatekeeper / clarifier — strip noise, extract core intent | "Identify the core problem in the following text in 1 sentence." |
| **Amygdala** | Emotional processing | Tone / urgency detector | "Output JSON with the user's emotional state (e.g. frustrated, curious) and urgency." |
| **Prefrontal Cortex** | Rational thinking / logic | Fact & constraint checker — objective, ignores emotional bias | "Given the core problem, list 3 objective facts or logical constraints we must respect." |
| **Hippocampus** | Memory retrieval | Contextual associator — grounds the response in past data | "What historical patterns or common knowledge apply here?" |
| **Broca's Area** | Speech production | Synthesizer — combine all prior micro-outputs into the final human-like response, matching required tone | "Synthesize the facts and context, matching the required tone, into a final response." |

The taxonomy is meant to grow/change — these are the seed regions, not a fixed set.

### Context inheritance (the "snowball")

The output of node N is appended into the context fed to node N+1, so context grows
organically down the line rather than forcing one model to hold a huge messy prompt
from the start. Keep the accumulated context as a first-class, inspectable object —
the UI renders it growing in real time.

### Cognitive trace (audit trail)

Every run emits a structured trace alongside the final answer — each node's input
prompt and its output. This is the debugger for human-like thought: when the final
output is wrong, the trace points at the exact weak node. Shape:

```json
{
  "Input": "My server crashed and I'm losing money!",
  "Trace": {
    "Thalamus_Output": "Core issue: technical downtime causing financial loss.",
    "Amygdala_Output": "Urgency: High. Emotion: Panic/Frustration.",
    "Prefrontal_Cortex_Output": "C1: needs immediate triage steps. C2: avoid jargon initially.",
    "Hippocampus_Output": "[Mocked: fetched disaster-recovery protocol #4]"
  },
  "Final_Output": "I understand this is critical... [rest of response]"
}
```

### The MVP diagnostic principle (core philosophy)

Because each node has a strict tiny job, you can run inputs through and immediately
see where the chain is weak, over-engineered, or just right. Classify every node into
one of three buckets and act accordingly — **do not rewrite the whole system, fix the
one node**:

1. **Just right (Goldilocks)** — tiny prompt + small/cheap model is consistently
   accurate; making it bigger changes nothing. Stop touching it. (Often Amygdala,
   Thalamus.)
2. **Too MVP (bottleneck)** — a node gives shallow/incomplete output that makes
   downstream nodes fail. Fix *only that node*: add few-shot examples, a more
   structured prompt, or route just that node to a smarter model. (Often Prefrontal
   Cortex.)
3. **Needs something more (beyond LLMs)** — the function is the wrong job for a prompt
   (factual precision, math, time-awareness, real-time data). **Replace the LLM prompt
   with actual code** — a vector-DB/RAG lookup, an API call, a calendar/DB query. The
   next node doesn't care *how* the data was produced, only that the right context was
   handed over. (Hippocampus is the prime candidate: a prompt "remembering" things will
   eventually fail — swap it for retrieval.)

This means **a node is an interface, not necessarily an LLM call.** Keep the node
boundary (input context in, handover context out) stable so any node can be swapped
between "LLM prompt" and "plain code" without touching its neighbors.

## The UI (the heart of the app)

The UI makes invisible execution tangible — the user watches thought physically move
across brain anatomy, like an active fMRI scan, instead of staring at a spinner.

### Per-tab tri-pane layout

One tab per brain region. Every tab shares the same three-column layout, so the eye
tracks Input → Processing → Handover horizontally:

```
[Thalamus]  *AMYGDALA*  [PFC]  [Hippocampus]  [Broca's Area]   <- tab bar
+-------------------------+--------------------------+------------------------+
|  LEFT                   |  MIDDLE                  |  RIGHT                 |
|  System prompt / input  |  Live thinking / status  |  Handover result       |
|  (what this node does)  |  (streaming LLM / logs)  |  (passed to next node) |
+-------------------------+--------------------------+------------------------+
```

The three columns must stay equal-width (~33% each) on resize.

### Two operational modes

- **Live Execution Mode (locked auto-focus)** — on submit, the UI auto-switches tabs
  to whichever node is currently running (Thalamus → Amygdala → PFC → …). The active
  node streams its prompt and raw thinking in real time. **Manual tab-clicking is
  disabled** so the user watches the "wave of thought" pass through in order.
- **Idle Review Mode (unlocked browsing)** — once the final node (Broca's Area)
  finishes, the final answer shows in a prominent panel and **tabs unlock** so the user
  can freely click back through any region to audit *why* the AI concluded what it did.

This is the "auto fan chooser": the node actually thinking is in focus; when idle and
waiting for input, you can browse the tabs.

### Visual language

- Distinct color per pane role (e.g. charcoal input / deep-blue thinking / forest-green
  handover) — nice colors are a requirement, not polish.
- Tabs that executed show a success indicator (green); nodes that were skipped show an
  idle/passed state.
- A left sidebar tracks the **evolving global state**: the input prompt plus the
  accumulated-context "snowball" growing as each node finishes.

## Tech stack & runtime

- **Language:** Python.
- **MVP UI:** Tkinter (`tkinter.ttk.Notebook` for tabs). Zero heavy deps, ships with
  Python. Run the pipeline on a **background thread** and marshal UI updates back via
  `root.after(...)` so the window stays responsive while nodes stream.
- **LLM runtime:** **Ollama**, local, via its HTTP API (`http://localhost:11434`).
- **Future web version (not MVP):** a Python backend (e.g. FastAPI) streaming
  structured execution events over **SSE or WebSockets**, with a React/Vue/Streamlit
  front end. The events drive the same auto-focus behavior:
  `{"status":"active_node","node":"Amygdala"}`,
  `{"status":"stream_chunk", ...}`, `{"status":"node_complete", ...}`.

### Local model selection — "small brains, large memory"

This project has an unusual requirement: the jobs are small (tiny prompts, simple
thoughts) so it does **not** need a large *reasoning* model — but the snowballing
handover context means it needs a strong *context handler*. Optimize for context-window
capacity and instruction-following, not parameter count.

**Hardware target: RTX 3080, 10 GB VRAM.** VRAM splits as
`model weights + KV cache (context memory)`. An 8B model at Q4 ≈ 4.8–5 GB, leaving
~4.5 GB; an 8B's KV cache costs ~0.5 GB per 8k tokens — so ~32k context fits before
spilling to slow system RAM.

Selection criteria:
1. **Native long context** (trained on 32k–128k; uses Flash-Attention / YaRN). Do *not*
   force a short-context model to read 32k — it fails "needle-in-haystack".
2. **High quantization** (`Q4_K_M` or `Q5_K_M`) — fine for extraction/synthesis; keeps
   the base footprint under ~5 GB for context headroom.
3. **Explicit `num_ctx`** (see gotcha below).

Candidate models (all fit the 3080):

| Model | Why | Footprint | Pull |
| --- | --- | --- | --- |
| **Llama 3.1 8B** | 128k native context, sharp instruction-following — balanced default | ~4.7 GB (Q4_K_M), scales to 32k ctx | `ollama run llama3.1` |
| **Phi-3.5 Mini 3.8B** | Punches above its weight; 128k native context, tiny base = max context headroom | ~2.2 GB | `ollama run phi3.5` |
| **Mistral 7B v0.3** | Sliding-window attention, efficient sequential handoff; 32k native | ~4.1 GB | `ollama run mistral` |

**v0.1 actually runs `gemma4:e2b`** (set in `brain/config.py`) — a brand-new small,
efficient Gemma already pulled on this machine; quick and good enough for prototype
testing. The table above is for scaling up later. (The "e" in `e2b` is part of the
model name, not a typo.)

### Critical gotcha: override `num_ctx`

Ollama defaults `num_ctx` to ~2048–4096 tokens. The snowballing context **will** exceed
that and silently truncate. Always pass `num_ctx` explicitly (16384 or 32768) on every
API call (or bake it into a custom Modelfile):

```python
import requests
resp = requests.post("http://localhost:11434/api/generate", json={
    "model": "llama3.1",
    "prompt": accumulated_context + "\n\nYour specific small task...",
    "options": {"num_ctx": 16384},  # allocate VRAM for the long history
})
```

## Commands

```bash
# one-time: start Ollama and pull the model (exact tag lives in brain/config.py)
ollama serve
ollama pull gemma4:e2b

# run the app
python app.py

# run the tests — no network or display needed (fake client; pure functions)
python -m pytest tests/ -q           # or a single file: python tests/test_pipeline.py
```

No third-party runtime dependencies — standard library only (`tkinter`, `urllib`).
`pytest` is optional; the test file also runs standalone.

## Project structure

A single `brain/` package. The node boundary (context in → handover out) is the key
seam: it stays stable so any region can flip between an LLM prompt and plain code per
the diagnostic principle.

```
brain-emulation/
├── app.py                  # entry point: wires client + pipeline + UI, launches Tk
├── brain/
│   ├── config.py           # model, num_ctx, Ollama host, UI palette
│   ├── ollama_client.py    # streaming HTTP client; owns the num_ctx override
│   ├── nodes.py            # Node dataclass + DEFAULT_PIPELINE (the 5 regions)
│   ├── pipeline.py         # ChoreographedPipeline + PipelineEvent (UI-agnostic)
│   ├── trace.py            # CognitiveTrace — the {Input, Trace, Final_Output} audit log
│   ├── mdtext.py           # pure markdown -> styled segments (no tkinter; testable)
│   └── ui.py               # Tkinter tri-pane tabs, auto-focus, continue-convo, md render
└── tests/
    ├── test_pipeline.py    # fake-client unit test: event flow, snowball, trace, history
    └── test_mdtext.py      # markdown parser unit test
```

`pipeline.py` emits `PipelineEvent`s and never imports Tkinter — the same event
stream can later drive the web/SSE front end.

## Design principles to preserve

- **Emulate, don't optimise.** The goal is human-like cognition, not the most correct
  answer — see *Design goal* under "What this is". Don't bolt on truth-seeking features
  to "improve" outputs.
- **Tiny job per node.** If a prompt is growing complex, that's a signal to split the
  node or move it to code — not to bloat it.
- **Stable node boundary.** Context in → handover out. Neighbors must not care whether a
  node is an LLM or a function.
- **Transparency over magic.** The trace and the live UI are features, not debug
  scaffolding — they're how you find the weak link.
- **Fix one node, not the system.** Use the three-bucket diagnostic before reaching for
  a bigger model.
