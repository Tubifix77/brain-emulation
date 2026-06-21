"""Unit tests for the experiment detectors — pure, no Ollama, no display."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.detectors import agency, register  # noqa: E402


def test_agency_flags_first_person_action():
    t = "I am establishing communication channels and I will restart the server."
    assert agency(t)["hallucinated"] is True
    assert agency(t)["claims"] >= 2


def test_agency_ignores_advice_to_the_user():
    t = "You should contact your DBA and restart the server yourself once it's safe."
    assert agency(t)["hallucinated"] is False


def test_register_flags_runbook():
    t = "Step 1: Isolate.\n\n1. Check logs\n2. Verify backups\n3. Restore service\n\n## Recovery"
    assert register(t)["runbook"] is True


def test_register_passes_conversational_prose():
    t = (
        "Okay, first things first — take a breath. Is it still down? The money you can "
        "reconstruct later from the logs; right now it's about getting back up, and if "
        "you've got recent backups that's your lifeline. Don't try to do this alone."
    )
    assert register(t)["runbook"] is False


if __name__ == "__main__":
    test_agency_flags_first_person_action()
    test_agency_ignores_advice_to_the_user()
    test_register_flags_runbook()
    test_register_passes_conversational_prose()
    print("OK — detector tests passed.")
