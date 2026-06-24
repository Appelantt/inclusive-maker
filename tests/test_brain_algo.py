"""Tests de l'algorithme de commande cérébrale."""

from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper


def test_open_state():
    detector = MentalStateDetector(alpha_high_threshold=1.0, alpha_low_threshold=0.2)
    state = detector.detect({"alpha": 2.0})
    assert state == "OPEN"


def test_close_state():
    detector = MentalStateDetector(alpha_high_threshold=1.0, alpha_low_threshold=0.2)
    state = detector.detect({"alpha": 0.1})
    assert state == "CLOSE"


def test_idle_state():
    detector = MentalStateDetector(alpha_high_threshold=1.0, alpha_low_threshold=0.2)
    state = detector.detect({"alpha": 0.5})
    assert state == "IDLE"


def test_command_mapper():
    mapper = CommandMapper()
    cmd = mapper.map("OPEN")
    assert cmd["action"] == "OPEN"
    assert cmd["value"] == 1.0
