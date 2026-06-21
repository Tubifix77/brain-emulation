"""Tiny markdown -> styled-segments parser (pure; no tkinter import).

Turns a markdown string into a flat list of ``(text, tags)`` segments so a Tk
Text widget can render bold/italic/code/headers/bullets instead of showing raw
'**asterisks**'. Deliberately small — it handles the constructs LLMs emit most:
ATX headers (#, ##, ###), **bold** / __bold__, *italic* / _italic_, `code`, and
``-`` / ``*`` / ``1.`` list bullets. Keeping it pure (no widget, no tkinter) means
it is unit-testable without a display.
"""
from __future__ import annotations

import re
from typing import List, Tuple

Segment = Tuple[str, Tuple[str, ...]]

_INLINE = re.compile(
    r"\*\*(?P<bold>.+?)\*\*"
    r"|__(?P<bold2>.+?)__"
    r"|(?<!\*)\*(?P<ital>[^*\n]+?)\*(?!\*)"
    r"|(?<!_)_(?P<ital2>[^_\n]+?)_(?!_)"
    r"|`(?P<code>[^`\n]+?)`"
)


def _inline(text: str, base: Tuple[str, ...]) -> List[Segment]:
    out: List[Segment] = []
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], base))
        if m.group("bold") is not None:
            out.append((m.group("bold"), base + ("md_bold",)))
        elif m.group("bold2") is not None:
            out.append((m.group("bold2"), base + ("md_bold",)))
        elif m.group("ital") is not None:
            out.append((m.group("ital"), base + ("md_italic",)))
        elif m.group("ital2") is not None:
            out.append((m.group("ital2"), base + ("md_italic",)))
        elif m.group("code") is not None:
            out.append((m.group("code"), base + ("md_code",)))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], base))
    return out


def parse_markdown(md: str) -> List[Segment]:
    """Return a flat list of ``(text, tags)`` segments, newlines included."""
    segments: List[Segment] = []
    for line in md.split("\n"):
        header = re.match(r"^(#{1,3})\s+(.*)$", line)
        if header:
            tag = f"md_h{len(header.group(1))}"
            segments += _inline(header.group(2), (tag,))
            segments.append(("\n", ()))
            continue
        bullet = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if bullet:
            segments.append(("   •  ", ("md_bullet",)))
            segments += _inline(bullet.group(1), ())
            segments.append(("\n", ()))
            continue
        numbered = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if numbered:
            segments.append((f"   {numbered.group(1)}.  ", ("md_bullet",)))
            segments += _inline(numbered.group(2), ())
            segments.append(("\n", ()))
            continue
        segments += _inline(line, ())
        segments.append(("\n", ()))
    return segments
