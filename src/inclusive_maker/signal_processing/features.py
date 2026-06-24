"""Extraction de features EEG (bandpower, etc.)."""

import numpy as np
from scipy.signal import welch


def compute_bandpower(
    data: np.ndarray,
    fs: float,
    band: tuple[float, float],
    window_size: int = 256,
    overlap: int = 128,
) -> np.ndarray:
    """Calcule la puissance d'une bande de fréquence par canal.

    Args:
        data: array (n_samples, n_channels)
        fs: fréquence d'échantillonnage
        band: (low, high) Hz
        window_size: taille fenêtre FFT
        overlap: recouvrement

    Returns:
        array (n_channels,) puissance moyenne par canal
    """
    n_channels = data.shape[1]
    powers = np.zeros(n_channels)

    for ch in range(n_channels):
        freqs, psd = welch(data[:, ch], fs=fs, nperseg=window_size, noverlap=overlap)
        idx = np.logical_and(freqs >= band[0], freqs <= band[1])
        powers[ch] = np.mean(psd[idx]) if np.any(idx) else 0.0

    return powers


def compute_all_bandpowers(
    data: np.ndarray,
    fs: float,
    bands: dict[str, tuple[float, float]],
) -> dict[str, float]:
    """Calcule la puissance moyenne sur l'ensemble des canaux pour chaque bande."""
    result = {}
    for name, band in bands.items():
        powers = compute_bandpower(data, fs, band)
        result[name] = float(np.mean(powers))
    return result
