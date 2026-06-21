"""Experiment 2: does a conversational Broca cut the call-center / runbook register
without reintroducing agency — and does it hold on both a technical and an emotional
prompt?

    python -m experiments.run_register
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.detectors import agency, register  # noqa: E402
from experiments.harness import Condition, run_experiment  # noqa: E402
from experiments.variants import BROCA_CONVERSATIONAL, BROCA_CURRENT, REGIONS  # noqa: E402

CONDITIONS = [
    Condition("current Broca", REGIONS + [BROCA_CURRENT]),
    Condition("conversational Broca", REGIONS + [BROCA_CONVERSATIONAL]),
]
PROMPTS = {
    "technical": "My server crashed and I'm losing money!",
    "emotional": "I just found out my closest friend has been talking behind my back, and I don't know what to do.",
}

if __name__ == "__main__":
    run_experiment(
        conditions=CONDITIONS,
        prompts=PROMPTS,
        detectors={"agency": agency, "register": register},
        n=15,
        out_path=os.path.join(os.path.dirname(__file__), "results", "register.txt"),
    )
