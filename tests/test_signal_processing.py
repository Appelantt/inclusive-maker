"""Tests du traitement du signal."""

import numpy as np
from inclousive_maker.signal_processing.features import compute_bandpower, compute_all_bandpowers


def test_compute_bandpower_shape():
    fs = 250.0
    t = np.arange(fs) / fs
    signal = np.sin(2 * np.pi * 10 * t).reshape(-1, 1)
    powers = compute_bandpower(signal, fs, (8, 13))
    assert powers.shape == (1,)
    assert powers[0] > 0


def test_compute_all_bandpowers():
    fs = 250.0
    t = np.arange(fs) / fs
    signal = np.sin(2 * np.pi * 10 * t).reshape(-1, 1)
    bands = {"alpha": (8, 13), "beta": (13, 30)}
    result = compute_all_bandpowers(signal, fs, bands)
    assert "alpha" in result
    assert "beta" in result
    assert result["alpha"] > 0
