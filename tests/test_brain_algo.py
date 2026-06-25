"""Tests de l'algorithme de commande cérébrale."""

from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.brain_algo.classifier import EEGStateClassifier, generate_training_data


def test_open_state_threshold():
    detector = MentalStateDetector(open_ratio=4.0, close_ratio=8.0, model_path="__none__")
    state = detector.detect({"alpha": 40.0, "beta": 1.0})
    assert state == "OPEN"
    assert detector.uses_ml is False


def test_close_state_threshold():
    detector = MentalStateDetector(open_ratio=4.0, close_ratio=8.0, model_path="__none__")
    state = detector.detect({"alpha": 1.0, "beta": 40.0})
    assert state == "CLOSE"


def test_idle_state_threshold():
    detector = MentalStateDetector(open_ratio=4.0, close_ratio=8.0, model_path="__none__")
    state = detector.detect({"alpha": 5.0, "beta": 5.0})
    assert state == "IDLE"


def test_command_mapper():
    mapper = CommandMapper()
    cmd = mapper.map("OPEN")
    assert cmd["action"] == "OPEN"
    assert cmd["value"] == 1.0


def test_classifier_train_save_load(tmp_path):
    X, y = generate_training_data(n_samples_per_class=50, window_duration=1.0, seed=42)
    model_path = tmp_path / "classifier.pkl"
    classifier = EEGStateClassifier(model_path=str(model_path))
    classifier.fit(X, y)
    classifier.save()

    loaded = EEGStateClassifier(model_path=str(model_path))
    assert loaded.is_trained()
    assert set(loaded.classes_) == {"OPEN", "CLOSE", "IDLE"}


def test_detector_uses_ml_when_model_exists(tmp_path):
    X, y = generate_training_data(n_samples_per_class=50, window_duration=1.0, seed=42)
    model_path = tmp_path / "classifier.pkl"
    classifier = EEGStateClassifier(model_path=str(model_path))
    classifier.fit(X, y)
    classifier.save()

    detector = MentalStateDetector(model_path=str(model_path))
    assert detector.uses_ml is True
    state = detector.detect({"alpha": 100.0, "beta": 1.0})
    assert state == "OPEN"
