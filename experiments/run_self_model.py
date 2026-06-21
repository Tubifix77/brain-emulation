"""Experiment 1 (formalised from the original scratch run): does an upstream
self-model node suppress agency-hallucination as well as the Broca grounding tweak?

    python -m experiments.run_self_model
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.detectors import agency, register  # noqa: E402
from experiments.harness import Condition, run_experiment  # noqa: E402
from experiments.variants import BROCA_CURRENT, BROCA_PLAIN, REGIONS, SELF_MODEL  # noqa: E402

CONDITIONS = [
    Condition("A baseline (plain Broca)", REGIONS + [BROCA_PLAIN]),
    Condition("B self-model only", [SELF_MODEL] + REGIONS + [BROCA_PLAIN]),
    Condition("C Broca grounding (current)", REGIONS + [BROCA_CURRENT]),
]
PROMPTS = {"server_crash": "My server crashed and I'm losing money!"}

if __name__ == "__main__":
    run_experiment(
        conditions=CONDITIONS,
        prompts=PROMPTS,
        detectors={"agency": agency, "register": register},
        n=10,
        out_path=os.path.join(os.path.dirname(__file__), "results", "self_model.txt"),
    )
