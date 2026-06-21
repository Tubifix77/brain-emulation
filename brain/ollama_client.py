"""Minimal streaming client for the Ollama HTTP API (standard library only).

This wrapper owns the ``num_ctx`` override: every generate call allocates a
context window big enough for the accumulated handover context, so the snowball
never gets silently truncated by Ollama's small default.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterator, Optional

from . import config


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or returns an error."""


class OllamaClient:
    def __init__(
        self,
        host: str = config.OLLAMA_HOST,
        model: str = config.MODEL,
        num_ctx: int = config.NUM_CTX,
        timeout: int = config.REQUEST_TIMEOUT,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = timeout

    def stream_generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        num_ctx: Optional[int] = None,
    ) -> Iterator[str]:
        """Yield response text chunks from /api/generate as they stream in."""
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_ctx": num_ctx or self.num_ctx},
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for raw in resp:  # Ollama streams one JSON object per line
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if obj.get("error"):
                        raise OllamaError(obj["error"])
                    chunk = obj.get("response", "")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Could not reach Ollama at {self.host} ({exc}). "
                f"Is `ollama serve` running and is '{model or self.model}' pulled?"
            ) from exc
