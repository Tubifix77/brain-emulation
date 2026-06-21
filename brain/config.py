"""Central configuration: model, context window, Ollama endpoint, and UI palette.

Everything tweakable lives here so a v0.1 prototype run is one edit away from a
different model or a wider context window.
"""

# --- LLM / Ollama -----------------------------------------------------------
OLLAMA_HOST = "http://localhost:11434"

# Brand-new small, efficient Gemma variant already pulled on this machine.
# NOTE: the "e" in "e2b" is part of the model name (an efficient edge build),
# not a typo. It's quick and good enough for v0.1 prototype testing.
MODEL = "gemma4:e2b"

# Ollama defaults num_ctx to ~2k-4k tokens, which the growing "snowball" context
# will overflow and silently truncate. Override it so the whole chain's handover
# history fits. e2b is tiny, so a generous window is cheap on a 10 GB card.
NUM_CTX = 16384

# Per-request timeout (seconds) for a streaming call to Ollama.
REQUEST_TIMEOUT = 180

# --- UI palette -------------------------------------------------------------
BG_DARK = "#1e1e24"
SIDEBAR_BG = "#23262d"
PANEL_LEFT = "#2a2d34"   # node job / system prompt   (charcoal)
PANEL_MID = "#001f3f"    # live thinking              (deep blue)
PANEL_RIGHT = "#1b4332"  # handover to next step      (forest green)
FINAL_BG = "#21303a"     # final response panel       (slate)

ACCENT = "#4a4e69"
ACCENT_TEXT = "#ffffff"
TEXT = "#f1faee"
MUTED = "#9aa0aa"
SUCCESS = "#52b788"
ERROR = "#e5576f"

LABEL_LEFT = "#a8dadc"
LABEL_MID = "#f1faee"
LABEL_RIGHT = "#b7e4c7"

FONT_UI = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_MONO = ("Consolas", 10)
