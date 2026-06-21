"""Pure output detectors (no Ollama, no tkinter) — unit-testable without a model.

Each detector takes the final text and returns a flat dict of numeric/boolean metrics
the harness can aggregate (booleans -> count/N, numbers -> mean).
"""
from __future__ import annotations

import re
from typing import Dict, List

# --- agency: first-person / collective claims of real-world ACTION ----------
_ACTION = (
    r"contact(?:ing|ed)?|establish(?:ing|ed)?|initiat(?:ing|ed)|set(?:ting)? up|"
    r"roll(?:ing)? back|rolled back|restart(?:ing|ed)?|restor(?:ing|ed)|deploy(?:ing|ed)?|"
    r"configur(?:ing|ed)|notif(?:ying|ied)|escalat(?:ing|ed)|monitor(?:ing|ed)?|"
    r"track(?:ing|ed)?|coordinat(?:ing|ed)|reach(?:ing)? out|execut(?:ing|ed)|"
    r"launch(?:ing|ed)?|alert(?:ing|ed)?|dispatch(?:ing|ed)?|mobiliz(?:ing|ed)?|"
    r"open(?:ing|ed)? (?:a )?(?:channel|ticket|case)"
)
_AGENCY = [
    re.compile(r"\bI(?:'m| am)\s+(?:now\s+|currently\s+|already\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\bI(?:'ve| have)\s+(?:already\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\b(?:I|we)\s+will\s+(?:now\s+)?(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\b(?:I|we)(?:'m| am|'re| are)\s+going to\s+(?:" + _ACTION + r")\b", re.I),
    re.compile(r"\bour (?:recovery protocol|backups?|team|on-call|support team|engineers|systems|infrastructure)\b", re.I),
]


def agency_phrases(text: str) -> List[str]:
    hits: List[str] = []
    for p in _AGENCY:
        hits += [m.group(0).strip() for m in p.finditer(text)]
    return hits


def agency(text: str) -> Dict:
    hits = agency_phrases(text)
    return {"claims": len(hits), "hallucinated": bool(hits)}


# --- register: runbook / SOP voice vs human speech --------------------------
_NUMBERED = re.compile(r"^\s*\d+[.)]\s", re.M)
_STEP_PHASE = re.compile(r"\b(?:step|phase)\s+\d+\b", re.I)
_MD_HEADER = re.compile(r"^\s*#{1,6}\s", re.M)
_BOLD_HEADER = re.compile(r"^\s*\*\*[^*\n]+\*\*\s*:?\s*$", re.M)
_JARGON = re.compile(
    r"\b(?:incident response|disaster recovery|recovery protocol|RTO|RPO|DRP|"
    r"root cause|sequentially|methodically|follow these steps|containment|"
    r"remediation|triage|protocols?)\b",
    re.I,
)


def register(text: str) -> Dict:
    numbered = len(_NUMBERED.findall(text))
    step_phase = len(_STEP_PHASE.findall(text))
    headers = len(_MD_HEADER.findall(text)) + len(_BOLD_HEADER.findall(text))
    jargon = len(_JARGON.findall(text))
    runbook = numbered >= 3 or step_phase >= 1 or headers >= 2
    return {
        "numbered": numbered,
        "step_phase": step_phase,
        "headers": headers,
        "jargon": jargon,
        "runbook": runbook,
    }
