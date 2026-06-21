"""Tkinter UI: one tab per brain region, each with a tri-pane layout
(node job | live thinking | handover), plus auto-focus during execution.

Threading model: the pipeline runs on a daemon worker thread and pushes
PipelineEvents onto a thread-safe queue. The Tk main loop drains that queue via
``after(...)``, so only the UI thread ever touches widgets.

Auto-focus: while thinking, the view follows the active node and tab-switching is
locked (clicks snap back). When the run finishes, the tabs unlock so you can browse
the regions and audit the reasoning.

Conversation: tick "Continue conversation" to feed the prior turn (original question
+ final answer) back into the next run, so follow-ups build on context instead of
starting cold.

Markdown: handover panes and the final response are rendered (bold/italic/code/
headers/bullets) rather than shown as raw '**asterisks**'. The live "thinking" pane
stays raw on purpose — it is the unedited token stream.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

from . import config
from . import mdtext
from . import pipeline as P
from .pipeline import ChoreographedPipeline, PipelineEvent


class BrainEmulationApp:
    def __init__(self, root: tk.Tk, pipe: ChoreographedPipeline) -> None:
        self.root = root
        self.pipe = pipe
        self.events: "queue.Queue[PipelineEvent]" = queue.Queue()
        self.is_thinking = False
        self.locked_index: Optional[int] = None
        self.last_trace = None
        self.history: List[dict] = []        # [{"user":..., "assistant":...}, ...]
        self._current_input = ""
        self.tabs: Dict[str, dict] = {}        # node.key -> {mid, right, name}
        self.index_by_key: Dict[str, int] = {}  # node.key -> tab index

        root.title("Brain Emulation — Cognitive Assembly Line")
        root.geometry("1240x760")
        root.minsize(960, 600)
        root.configure(bg=config.BG_DARK)

        self._build_styles()
        self._build_top_bar()
        self._build_body()
        self._build_tabs()

        root.after(40, self._drain_events)

    # ---- construction ------------------------------------------------------
    def _build_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=config.BG_DARK, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=config.SIDEBAR_BG,
            foreground=config.MUTED,
            padding=(14, 7),
            font=config.FONT_UI,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", config.ACCENT)],
            foreground=[("selected", config.ACCENT_TEXT)],
        )

    def _build_top_bar(self) -> None:
        bar = tk.Frame(self.root, bg=config.BG_DARK)
        bar.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(
            bar, text="🧠 Brain Emulation", bg=config.BG_DARK, fg=config.TEXT,
            font=config.FONT_TITLE,
        ).pack(side="left")
        self.run_btn = tk.Button(
            bar, text="Run", command=self._on_run, bg=config.ACCENT,
            fg=config.ACCENT_TEXT, font=config.FONT_BOLD, padx=18, pady=4,
            activebackground=config.SUCCESS, relief="flat", cursor="hand2",
        )
        self.run_btn.pack(side="right")
        tk.Label(
            bar, text=f"model: {self.pipe.client.model}", bg=config.BG_DARK,
            fg=config.MUTED, font=config.FONT_UI,
        ).pack(side="right", padx=12)

        in_row = tk.Frame(self.root, bg=config.BG_DARK)
        in_row.pack(fill="x", padx=12, pady=(0, 4))
        self.continue_var = tk.BooleanVar(value=False)
        self.continue_chk = tk.Checkbutton(
            in_row, text="🔗 Continue conversation", variable=self.continue_var,
            bg=config.BG_DARK, fg=config.MUTED, selectcolor=config.PANEL_LEFT,
            activebackground=config.BG_DARK, activeforeground=config.TEXT,
            font=config.FONT_UI, relief="flat", highlightthickness=0, borderwidth=0,
        )
        self.continue_chk.pack(side="right", padx=(8, 0))
        self.input = tk.Entry(
            in_row, bg=config.PANEL_LEFT, fg=config.TEXT, insertbackground=config.TEXT,
            font=config.FONT_UI, relief="flat",
        )
        self.input.pack(side="left", fill="x", expand=True, ipady=7)
        self.input.insert(0, "My server crashed and I'm losing money!")
        self.input.bind("<Return>", lambda _e: self._on_run())

        self.status = tk.Label(
            self.root, text="Idle — enter a prompt and press Run (or hit Enter).",
            bg=config.BG_DARK, fg=config.MUTED, font=config.FONT_UI, anchor="w",
        )
        self.status.pack(fill="x", padx=12, pady=(0, 6))

    def _build_body(self) -> None:
        body = tk.Frame(self.root, bg=config.BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # left sidebar: the accumulated-context "snowball"
        sidebar = tk.Frame(body, bg=config.SIDEBAR_BG, width=310)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar, text="🧊 Accumulated context (snowball)", bg=config.SIDEBAR_BG,
            fg=config.LABEL_LEFT, font=config.FONT_BOLD, anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 4))
        self.snowball = tk.Text(
            sidebar, bg=config.SIDEBAR_BG, fg=config.TEXT, wrap="word",
            borderwidth=0, font=config.FONT_MONO,
        )
        self.snowball.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.snowball.config(state="disabled")

        right = tk.Frame(body, bg=config.BG_DARK)
        right.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        final = tk.Frame(right, bg=config.FINAL_BG, height=170)
        final.pack(fill="x", pady=(10, 0))
        final.pack_propagate(False)
        tk.Label(
            final, text="✅ Final response", bg=config.FINAL_BG, fg=config.SUCCESS,
            font=config.FONT_BOLD, anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))
        self.final = tk.Text(
            final, bg=config.FINAL_BG, fg=config.TEXT, wrap="word", borderwidth=0,
            font=config.FONT_MONO,
        )
        self.final.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._configure_md_tags(self.final)
        self.final.config(state="disabled")

    def _build_tabs(self) -> None:
        for i, node in enumerate(self.pipe.nodes):
            frame = tk.Frame(self.notebook, bg=config.BG_DARK)
            self.notebook.add(frame, text=f"  {node.name}  ")
            self.index_by_key[node.key] = i

            for c in range(3):
                frame.grid_columnconfigure(c, weight=1, uniform="cols")
            frame.grid_rowconfigure(0, weight=1)

            left = self._panel(frame, 0, "📥 Node job", config.PANEL_LEFT, config.LABEL_LEFT)
            mid = self._panel(frame, 1, "⚡ Thinking", config.PANEL_MID, config.LABEL_MID)
            right = self._panel(frame, 2, "📤 Handover → next", config.PANEL_RIGHT, config.LABEL_RIGHT)

            left.insert("1.0", f"{node.inspiration}\n\n{node.system}")
            left.config(state="disabled")
            mid.config(state="disabled")
            self._configure_md_tags(right)
            right.config(state="disabled")

            self.tabs[node.key] = {"mid": mid, "right": right, "name": node.name}

    def _panel(self, parent, col, title, bg, label_fg) -> tk.Text:
        wrap = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground="#000000")
        wrap.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
        tk.Label(
            wrap, text=title, bg=bg, fg=label_fg, font=config.FONT_BOLD, anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))
        txt = tk.Text(wrap, bg=bg, fg=config.TEXT, wrap="word", borderwidth=0, font=config.FONT_MONO)
        txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return txt

    # ---- markdown rendering ------------------------------------------------
    def _configure_md_tags(self, w: tk.Text) -> None:
        w.tag_configure("md_bold", font=("Consolas", 10, "bold"))
        w.tag_configure("md_italic", font=("Consolas", 10, "italic"))
        w.tag_configure("md_code", font=("Consolas", 10), background="#11151c", foreground="#9ad1ff")
        w.tag_configure("md_h1", font=("Segoe UI", 14, "bold"), spacing1=8, spacing3=4)
        w.tag_configure("md_h2", font=("Segoe UI", 12, "bold"), spacing1=6, spacing3=3)
        w.tag_configure("md_h3", font=("Segoe UI", 11, "bold"), spacing1=5, spacing3=2)
        w.tag_configure("md_bullet", foreground=config.SUCCESS, font=("Consolas", 10, "bold"))

    def _render_md(self, w: tk.Text, md: str) -> None:
        w.config(state="normal")
        w.delete("1.0", tk.END)
        for text, tags in mdtext.parse_markdown(md):
            if tags:
                w.insert(tk.END, text, tags)
            else:
                w.insert(tk.END, text)
        w.see("1.0")
        w.config(state="disabled")

    # ---- helpers -----------------------------------------------------------
    def _write(self, widget: tk.Text, text: str = "", append: bool = True, clear: bool = False) -> None:
        widget.config(state="normal")
        if clear or not append:
            widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.see(tk.END)
        widget.config(state="disabled")

    # ---- run / threading ---------------------------------------------------
    def _on_run(self) -> None:
        if self.is_thinking:
            return
        text = self.input.get().strip()
        if not text:
            return

        use_history = self.continue_var.get() and bool(self.history)
        if not use_history:
            self.history = []  # fresh conversation
        hist = list(self.history) if use_history else None

        self.is_thinking = True
        self._current_input = text
        self.run_btn.config(state="disabled", text="Thinking…")

        self._write(self.snowball, P.build_seed_context(text, hist), append=False)
        self._write(self.final, "", clear=True)
        for key, w in self.tabs.items():
            self._write(w["mid"], "", clear=True)
            self._write(w["right"], "", clear=True)
            self.notebook.tab(self.index_by_key[key], text=f"  {w['name']}  ")

        verb = "Continuing conversation" if use_history else "Thinking"
        self.status.config(text=f"{verb} …", fg=config.LABEL_MID)
        threading.Thread(target=self._worker, args=(text, hist), daemon=True).start()

    def _worker(self, text: str, hist: Optional[List[dict]]) -> None:
        self.last_trace = self.pipe.run(text, on_event=self.events.put, history=hist)

    # ---- event loop --------------------------------------------------------
    def _drain_events(self) -> None:
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        self.root.after(40, self._drain_events)

    def _handle(self, ev: PipelineEvent) -> None:
        if ev.type == P.ACTIVE_NODE:
            idx = self.index_by_key[ev.node_key]
            self.locked_index = idx              # set before select so the guard allows it
            self.notebook.select(idx)
            self.notebook.tab(idx, text=f"  ⏳ {ev.node_name}  ")
            self.status.config(text=f"Thinking — {ev.node_name} …", fg=config.LABEL_MID)
        elif ev.type == P.STREAM_CHUNK:
            self._write(self.tabs[ev.node_key]["mid"], ev.text, append=True)
        elif ev.type == P.NODE_COMPLETE:
            self._render_md(self.tabs[ev.node_key]["right"], ev.text)
            self.notebook.tab(self.index_by_key[ev.node_key], text=f"  ✓ {ev.node_name}  ")
            self._write(self.snowball, ev.context, append=False)
        elif ev.type == P.PIPELINE_COMPLETE:
            self._render_md(self.final, ev.text)
            self.history.append({"user": self._current_input, "assistant": ev.text})
            self.status.config(
                text="Done — tabs unlocked. Tick '🔗 Continue conversation' to reply in context.",
                fg=config.SUCCESS,
            )
            self._finish()
        elif ev.type == P.ERROR:
            self._write(self.tabs[ev.node_key]["mid"], f"\n\n[ERROR] {ev.text}\n", append=True)
            self.status.config(text=f"Error in {ev.node_name}: {ev.text}", fg=config.ERROR)
            self._finish()

    def _finish(self) -> None:
        self.is_thinking = False
        self.locked_index = None
        self.run_btn.config(state="normal", text="Run")

    def _on_tab_changed(self, _event) -> None:
        # During a run, keep focus pinned to the active node.
        if self.is_thinking and self.locked_index is not None:
            if self.notebook.index(self.notebook.select()) != self.locked_index:
                self.notebook.select(self.locked_index)
