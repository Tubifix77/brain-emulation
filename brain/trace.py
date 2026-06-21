"""The cognitive trace: the audit trail of what each region saw and said.

Serialises to the {Input, Trace, Final_Output} shape so any run can be inspected
(or, later, streamed to a web UI) to find the single weak node when output is off.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class NodeTrace:
    key: str
    name: str
    inspiration: str
    system: str
    output: str


@dataclass
class CognitiveTrace:
    user_input: str
    nodes: List[NodeTrace] = field(default_factory=list)
    final_output: str = ""

    def add(self, node, output: str) -> None:
        self.nodes.append(
            NodeTrace(
                key=node.key,
                name=node.name,
                inspiration=node.inspiration,
                system=node.system,
                output=output,
            )
        )

    def to_dict(self) -> Dict:
        return {
            "Input": self.user_input,
            "Trace": {f"{n.name}_Output": n.output for n in self.nodes},
            "Final_Output": self.final_output,
        }
