"""Unit tests for the pure markdown parser — no tkinter, no display."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.mdtext import parse_markdown  # noqa: E402


def _text(segs):
    return "".join(t for t, _ in segs)


def _tagged(segs, tag):
    return [t for t, tags in segs if tag in tags]


def test_bold_is_tagged_and_markers_removed():
    segs = parse_markdown("Here is **important** text")
    assert "important" in _tagged(segs, "md_bold")
    assert "**" not in _text(segs)  # the literal asterisks are gone


def test_headers_and_bullets():
    segs = parse_markdown("# Title\n- one\n- two")
    assert "Title" in _tagged(segs, "md_h1")
    assert any("•" in marker for marker in _tagged(segs, "md_bullet"))


def test_inline_code_and_italic():
    segs = parse_markdown("run `ollama serve` then stay *calm*")
    assert "ollama serve" in _tagged(segs, "md_code")
    assert "calm" in _tagged(segs, "md_italic")
    assert "`" not in _text(segs)


if __name__ == "__main__":
    test_bold_is_tagged_and_markers_removed()
    test_headers_and_bullets()
    test_inline_code_and_italic()
    print("OK — markdown parser tests passed.")
