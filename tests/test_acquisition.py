"""Tests du simulateur EEG et du connecteur Unicorn."""

import numpy as np

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.acquisition.unicorn_connector import UnicornConnector
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT


def test_generator_shape():
    gen = EEGGenerator("IDLE")
    eeg = gen.read_window(1.0)
    assert eeg.shape == (EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT)


def test_generator_state_change():
    gen = EEGGenerator("OPEN")
    open_data = gen.read_window(1.0)
    gen.set_state("CLOSE")
    close_data = gen.read_window(1.0)
    # OPEN a plus d'energie alpha brute que CLOSE dans notre simulateur
    assert np.std(open_data) > np.std(close_data)


def test_generator_unknown_state_raises():
    try:
        EEGGenerator("UNKNOWN")
    except ValueError:
        pass
    else:
        raise AssertionError("Un etat inconnu aurait du lever une ValueError")


def test_unicorn_connector_fallback_to_generator():
    connector = UnicornConnector(use_generator=False)
    source = connector.connect()
    assert source is not None
    assert isinstance(source, EEGGenerator)
    assert connector.is_native() is False
    connector.disconnect()
