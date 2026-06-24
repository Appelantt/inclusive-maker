"""Détecteur d'état mental simple pour la commande cérébrale.

Stratégie basée sur le ratio alpha/bêta :
- ratio alpha/bêta élevé → OPEN (relaxation)
- ratio bêta/alpha élevé → CLOSE (concentration / effort)
- ratio intermédiaire → IDLE

Cette approche par ratio est plus robuste aux variations d'amplitude globale.
"""

from collections import deque
from typing import Literal


class MentalStateDetector:
    """Détecte un état mental parmi OPEN, CLOSE, IDLE."""

    STATES = ("OPEN", "CLOSE", "IDLE")

    def __init__(
        self,
        open_ratio: float = 4.0,
        close_ratio: float = 8.0,
        smoothing_window: int = 3,
    ):
        self.open_ratio = open_ratio
        self.close_ratio = close_ratio
        self._history: deque[str] = deque(maxlen=smoothing_window)

    def detect(self, features: dict[str, float]) -> Literal["OPEN", "CLOSE", "IDLE"]:
        """Retourne l'état mental détecté à partir des features."""
        alpha = max(features.get("alpha", 0.0), 1e-9)
        beta = max(features.get("beta", 0.0), 1e-9)

        alpha_beta_ratio = alpha / beta
        beta_alpha_ratio = beta / alpha

        if alpha_beta_ratio >= self.open_ratio:
            state = "OPEN"
        elif beta_alpha_ratio >= self.close_ratio:
            state = "CLOSE"
        else:
            state = "IDLE"

        self._history.append(state)
        # Vote majoritaire pour lisser les transitions
        return max(set(self._history), key=self._history.count)

    def reset(self) -> None:
        """Réinitialise l'historique."""
        self._history.clear()
