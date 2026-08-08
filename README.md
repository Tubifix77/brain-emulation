# 🧠 Brain Emulation

**A cognitive assembly line for LLMs.** Instead of asking one big model to think
through a whole problem at once, Brain Emulation splits the work across a chain of
tiny, specialised steps — each one modelled on a part of the human brain. A thought
flows down the line like a product down a factory belt and comes out the other end as
a human-like conclusion.

You don't just get the answer. You get to *watch the thought happen*, region by region,
and see exactly how it was built.

> **Status: v1.0 - structure shipped and tested.** The choreographed pipeline, context
> inheritance, cognitive trace, and Tkinter UI are built and verified (see CLAUDE.md for
> detail). This banner was stale - last touched before the pipeline existed. The seed
> brain regions are meant to keep growing; the structure itself is done.

---

## The idea

Most LLM setups make a single agent do all the heavy lifting in one giant prompt. That
makes the "thinking" a black box: when the answer is wrong, you don't know *why*.

Brain Emulation takes the opposite approach. Each step in the chain:

- has **one very small job** and a **very small prompt**,
- **inherits the context** built up by the steps before it,
- and **hands its result to the next step**.

Because every step is small and explicit, the whole reasoning process becomes
transparent and easy to debug — and you can run the small jobs on small, fast, local
models instead of one expensive giant.

## How it works

A prompt travels through a chain of "brain regions", each transforming it a little:

| Region | Inspired by | What it does |
| --- | --- | --- |
| **Thalamus** | Sensory relay | Strips the noise and pins down the core intent |
| **Amygdala** | Emotional processing | Reads the tone, urgency, and emotion behind the input |
| **Prefrontal Cortex** | Rational thinking | Lays out the objective facts and logical constraints |
| **Hippocampus** | Memory | Pulls in relevant past knowledge / context |
| **Broca's Area** | Speech production | Synthesises everything into the final human-like reply |

As each region finishes, its output is added to a shared, growing context — a
"snowball" that the next region picks up. Every run also produces a **cognitive trace**:
a structured log of what each region saw and said, so you can always trace the final
answer back to the step that shaped it.

The chain is modular by design. If a region turns out to need more than a prompt can
give — say, the Hippocampus needs to *actually* look things up — you can swap that one
step from "LLM prompt" to real code (a database, a search, an API) without disturbing
its neighbours.

## The interface

This is the part that makes it click. The app is built around a **live, fMRI-style
view of thought moving through the brain.**

Each region gets its own tab, and every tab has the same three columns:

```
[Thalamus]  *AMYGDALA*  [PFC]  [Hippocampus]  [Broca's Area]
┌─────────────────────┬──────────────────────┬─────────────────────┐
│  System prompt       │  Live thinking        │  Handover result     │
│  (what this step does)│  (streams in real time)│  (passed to next step)│
└─────────────────────┴──────────────────────┴─────────────────────┘
```

It has two modes:

- **While it's thinking** — the view automatically jumps to whichever region is
  currently working, streaming its thoughts live. You watch the "wave of thought" pass
  through the chain in order; the tabs are locked so you can't lose your place.
- **When it's done** — the final answer takes centre stage and the tabs unlock. Now you
  can click freely through any region to audit *why* the AI concluded what it did.

Colour-coded panels, success indicators on the tabs that fired, and a side panel showing
the context snowball grow in real time round it out.

## Why build it this way?

- **Debuggable thinking.** When the output is off, the trace points straight at the weak
  step. You fix *that one step* — a better prompt, a few examples, or swapping in code —
  instead of rewriting everything.
- **Cheap and fast.** Tiny prompts run happily on small local models.
- **Honest.** Nothing is hidden. The reasoning is right there on screen, step by step.

## Requirements

- **Python** (the MVP UI uses Tkinter, which ships with Python — no heavy dependencies)
- **[Ollama](https://ollama.com)** running locally for the language models
- A GPU helps but isn't strictly required. Development targets an **RTX 3080 (10 GB
  VRAM)** — comfortably enough to run a small model with a large context window.

## Getting started

> ⚠️ Not yet runnable — these are the intended steps once the first version lands.

```bash
# 1. Install Ollama, then pull a model
ollama pull llama3.1        # or phi3.5 (tiny) / mistral

# 2. Clone and run
git clone <your-repo-url>
cd brain-emulation
python app.py
```

## Choosing a model

This project has an unusual sweet spot: the jobs are *simple*, so you don't need a big
reasoning model — but the context snowballs as it flows down the chain, so you need a
good **long-context** model. Think *small brains, large memory*.

Good local picks that fit a 10 GB card:

- **Llama 3.1 8B** — balanced default, 128k context window
- **Phi-3.5 Mini 3.8B** — tiny and quick, also 128k context — leaves tons of room for a
  long history
- **Mistral 7B v0.3** — efficient, 32k context

One important tip: Ollama defaults to a small context window (~2–4k tokens), which the
growing context will overflow. Bump it up (to 16k or 32k) when you run, or the chain
will quietly forget what earlier regions said.

## Roadmap

- [ ] Choreographed pipeline (linear region-to-region chain)
- [ ] Ollama integration with proper long-context handling
- [ ] Tkinter UI: tri-pane tabs + auto-focus
- [ ] Cognitive trace viewer
- [ ] Optional orchestrator mode (a central router that decides what runs next)
- [ ] Swap-in code-backed regions (e.g. real memory/retrieval for the Hippocampus)

## License

Released under the [MIT License](LICENSE).
