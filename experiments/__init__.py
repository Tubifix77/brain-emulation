"""Experiment harness — the project's 'MVP diagnostic' as a reusable tool.

Compare pipeline configurations (conditions) over repeated runs, scored by pluggable
detectors. The goal is fidelity-of-emulation, so detectors measure *how* the output
behaves (does it hallucinate agency? does it read like a runbook?), not correctness.
"""
