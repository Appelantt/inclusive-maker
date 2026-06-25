"""Source EEG basee sur le stream LSL de Unicorn Recorder.

Quand Unicorn Suite / Unicorn Recorder est installe mais que gpype ne trouve pas
les DLL natives, on peut recuperer les donnees EEG via le protocole Lab Streaming
Layer (LSL). Unicorn Recorder peut streamer en LSL par defaut.
"""

from typing import Optional

import numpy as np
from pylsl import StreamInlet, resolve_byprop

from ..shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT
from ..shared.logger import get_logger

logger = get_logger(__name__)


class UnicornLSLSource:
    """Connecte au stream EEG LSL emis par Unicorn Recorder."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._inlet: Optional[StreamInlet] = None
        self._info = None
        self._connect()

    def _connect(self) -> None:
        logger.info("Recherche d'un stream EEG LSL de Unicorn Recorder...")
        try:
            streams = resolve_byprop("type", "EEG", timeout=self.timeout)
        except Exception as e:
            logger.warning(f"Erreur lors de la resolution LSL : {e}")
            streams = []

        if not streams:
            raise RuntimeError("Aucun stream EEG LSL trouve. Verifie qu'Unicorn Recorder est ouvert et streaming.")

        # Choisir le premier stream EEG (on suppose qu'il n'y en a qu'un)
        self._info = streams[0]
        self._inlet = StreamInlet(self._info)
        logger.info(
            f"Stream EEG LSL connecte : {self._info.name()} "
            f"({self._info.channel_count()} canaux, {self._info.nominal_srate()} Hz)"
        )

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Lit une fenetre EEG de duree donnee depuis le stream LSL."""
        n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
        data, _ = self._inlet.pull_chunk(timeout= duration_seconds + 1.0, max_samples=n_samples)
        arr = np.array(data)
        if arr.size == 0:
            return np.zeros((n_samples, EEG_CHANNEL_COUNT))
        # Garder uniquement les 8 canaux EEG
        if arr.shape[1] > EEG_CHANNEL_COUNT:
            arr = arr[:, :EEG_CHANNEL_COUNT]
        # Pad si pas assez d'echantillons
        if arr.shape[0] < n_samples:
            pad = np.zeros((n_samples - arr.shape[0], arr.shape[1]))
            arr = np.vstack([arr, pad])
        return arr

    def set_state(self, state: str) -> None:
        """Inactif pour le stream LSL reel (l'etat est determine par l'utilisateur)."""
        pass

    def is_native(self) -> bool:
        return True

    def disconnect(self) -> None:
        # StreamInlet n'a pas de methode close() dans pylsl;
        # il est libere automatiquement lors du garbage collection.
        self._inlet = None
        logger.info("Stream EEG LSL deconnecte.")
