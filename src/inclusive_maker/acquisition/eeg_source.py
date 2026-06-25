"""Source EEG unifiee pour le casque Unicorn ou le simulateur.

Expose une interface commune :
    - read_window(duration_seconds: float) -> np.ndarray
    - set_state(state: str)              -> change l'etat (simulateur uniquement)
    - is_native() -> bool
    - get_mode() -> str

Ordre de priorite :
1. Casque Unicorn via gpype (si DLL disponibles)
2. Stream LSL depuis Unicorn Recorder (si Unicorn Recorder tourne)
3. Simulateur interne EEGGenerator
"""

from typing import Optional

import numpy as np

from .generator import EEGGenerator
from .unicorn_connector import UnicornConnector
from .unicorn_lsl_source import UnicornLSLSource
from ..shared.constants import EEG_SAMPLING_RATE
from ..shared.logger import get_logger

logger = get_logger(__name__)


class UnifiedEEGSource:
    """Wrapper commun pour gp.HybridBlack, LSL Unicorn Recorder et EEGGenerator."""

    def __init__(self, force_generator: bool = False):
        self._source = None
        self._is_native = False
        self._mode = "simulateur"

        if not force_generator:
            # 1. Essayer gpype HybridBlack
            try:
                connector = UnicornConnector()
                connector.connect()
                if connector.is_native():
                    self._source = connector.get_source()
                    self._is_native = True
                    self._mode = "gpype"
                    logger.info("Source EEG : casque Unicorn via gpype.")
                    return
            except Exception as e:
                logger.warning(f"gpype Unicorn indisponible : {e}")

            # 2. Essayer LSL depuis Unicorn Recorder
            try:
                self._source = UnicornLSLSource()
                self._is_native = True
                self._mode = "lsl"
                logger.info("Source EEG : casque Unicorn via LSL (Unicorn Recorder).")
                return
            except Exception as e:
                logger.warning(f"LSL Unicorn indisponible : {e}")

        # 3. Fallback simulateur
        self._source = EEGGenerator("IDLE")
        self._is_native = False
        self._mode = "simulateur"
        logger.info("Source EEG : generateur synthetique interne.")

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Lit une fenetre EEG de duree donnee."""
        if self._mode == "gpype":
            n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
            data = self._source.get_data(n_samples)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            return data[:, :8] if data.shape[1] > 8 else data
        return self._source.read_window(duration_seconds)

    def set_state(self, state: str) -> None:
        """Change l'etat simule (uniquement pour le simulateur)."""
        if not self._is_native:
            self._source.set_state(state)

    def is_native(self) -> bool:
        return self._is_native

    def get_mode(self) -> str:
        return self._mode

    def disconnect(self) -> None:
        if self._source is not None:
            try:
                if self._mode != "gpype":
                    self._source.disconnect()
            except Exception as e:
                logger.warning(f"Erreur deconnexion source EEG : {e}")
        logger.info(f"Source EEG {self._mode} deconnectee.")
