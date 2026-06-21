"""Entry point: wire the Ollama client + choreographed pipeline into the Tk UI.

Run with:  python app.py
(Requires `ollama serve` running and the configured model pulled — see brain/config.py)
"""
import tkinter as tk

from brain.ollama_client import OllamaClient
from brain.pipeline import ChoreographedPipeline
from brain.ui import BrainEmulationApp


def main() -> None:
    client = OllamaClient()
    pipeline = ChoreographedPipeline(client)
    root = tk.Tk()
    BrainEmulationApp(root, pipeline)
    root.mainloop()


if __name__ == "__main__":
    main()
