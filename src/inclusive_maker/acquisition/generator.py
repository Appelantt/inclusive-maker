"""Simulateur EEG pour le développement sans casque Unicorn.

Ce module génère des signaux EEG synthétiques avec des signatures
alpha/bêta différentes pour chaque état mental simulé :

- OPEN  : forte puissance alpha (yeux fermés / relaxation)
- CLOSE : forte puissance bêta (concentration / effort moteur)
- IDLE  : signal neutre
"""

import time
import numpy as np

from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT


class EEGGenerator:
    """Générateur de signaux EEG synthétiques par état mental.

    Args:
        state: État mental cible parmi "OPEN", "CLOSE", "IDLE".
        seed: Graine aléatoire pour la reproductibilité.
    """

    STATE_PROFILES = {
        "OPEN": {"alpha_power": 35.0, "beta_power": 5.0, "theta_power": 10.0},
        "CLOSE": {"alpha_power": 5.0, "beta_power": 35.0, "theta_power": 8.0},
        "IDLE": {"alpha_power": 12.0, "beta_power": 12.0, "theta_power": 8.0},
    }

    def __init__(self, state: str = "IDLE", seed: int = 42):
        self.state = state.upper()
        if self.state not in self.STATE_PROFILES:
            raise ValueError(f"État inconnu : {state}. Choix : {list(self.STATE_PROFILES)}")
        self.rng = np.random.default_rng(seed)
        self._last_time = time.time()

    def set_state(self, state: str):
        """Change l'état mental simulé."""
        state = state.upper()
        if state not in self.STATE_PROFILES:
            raise ValueError(f"État inconnu : {state}")
        self.state = state

    def read(self, n_samples: int) -> np.ndarray:
        """Génère n_samples d'EEG simulé.

        Returns:
            Tableau numpy de forme (n_samples, EEG_CHANNEL_COUNT).
        """
        profile = self.STATE_PROFILES[self.state]
        t = np.arange(n_samples) / EEG_SAMPLING_RATE

        data = np.zeros((n_samples, EEG_CHANNEL_COUNT))
        for ch in range(EEG_CHANNEL_COUNT):
            # Bruit de base
            noise = self.rng.normal(0, 1.0, n_samples)

            # Bande alpha ~10 Hz
            alpha = profile["alpha_power"] * np.sin(2 * np.pi * 10.0 * t + self.rng.random() * 2 * np.pi)

            # Bande bêta ~20 Hz
            beta = profile["beta_power"] * np.sin(2 * np.pi * 20.0 * t + self.rng.random() * 2 * np.pi)

            # Bande theta ~6 Hz
            theta = profile["theta_power"] * np.sin(2 * np.pi * 6.0 * t + self.rng.random() * 2 * np.pi)

            data[:, ch] = alpha + beta + theta + noise

        return data

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Génère une fenêtre d'EEG d'une durée donnée.

        Args:
            duration_seconds: Durée en secondes.
        """
        n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
        return self.read(n_samples)

    def is_native(self) -> bool:
        return False

    def disconnect(self) -> None:
        """Aucune ressource à libérer pour le simulateur (no-op)."""
        pass
