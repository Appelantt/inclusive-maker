"""Tests de l'algorithme de commande cérébrale."""

from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper


def test_open_state():
    detector = MentalStateDetector(alpha_high_threshold=10.0, beta_high_threshold=10.0)
    state = detector.detect({"alpha": 20.0, "beta": 1.0})
    assert state == "OPEN"


def test_close_state():
    detector = MentalStateDetector(alpha_high_threshold=10.0, beta_high_threshold=10.0)
    state = detector.detect({"alpha": 1.0, "beta": 20.0})
    assert state == "CLOSE"


def test_idle_state():
    detector = MentalStateDetector(alpha_high_threshold=10.0, beta_high_threshold=10.0)
    state = detector.detect({"alpha": 5.0, "beta": 5.0})
    assert state == "IDLE"


def test_command_mapper():
    mapper = CommandMapper()
    cmd = mapper.map("OPEN")
    assert cmd["action"] == "OPEN"
    assert cmd["value"] == 1.0
