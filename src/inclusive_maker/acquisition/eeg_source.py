"""Source EEG unifiee pour le casque Unicorn ou le simulateur.

Expose une interface commune :
    - read_window(duration_seconds: float) -> np.ndarray
    - set_state(state: str)              -> change l'etat (simulateur uniquement)
    - is_native() -> bool
"""

from typing import Optional

import numpy as np

from .generator import EEGGenerator
from .unicorn_connector import UnicornConnector
from ..shared.constants import EEG_SAMPLING_RATE


class UnifiedEEGSource:
    """Wrapper commun pour gp.HybridBlack et EEGGenerator."""

    def __init__(self, force_generator: bool = False):
        self.connector = UnicornConnector(use_generator=force_generator)
        self.connector.connect()
        self._source = self.connector.get_source()

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Lit une fenetre EEG de duree donnee."""
        n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
        if self.connector.is_native():
            # gp.HybridBlack expose generalement .get_data(n_samples)
            data = self._source.get_data(n_samples)
            # On garde uniquement les canaux EEG (8 premiers)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            return data[:, :8] if data.shape[1] > 8 else data
        return self._source.read_window(duration_seconds)

    def set_state(self, state: str) -> None:
        """Change l'etat simule (uniquement pour le simulateur)."""
        if not self.connector.is_native():
            self._source.set_state(state)

    def is_native(self) -> bool:
        return self.connector.is_native()

    def disconnect(self) -> None:
        self.connector.disconnect()
