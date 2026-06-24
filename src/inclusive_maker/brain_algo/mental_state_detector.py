"""Détecteur d'état mental simple pour la commande cérébrale.

Stratégie initiale basée sur la puissance alpha :
- alpha élevée → état relaxé → commande OPEN
- alpha faible → état concentré/actif → commande CLOSE
- sinon → IDLE

C'est un exemple pédagogique à remplacer par un vrai classifieur entraîné.
"""

from collections import deque
from typing import Literal

class MentalStateDetector:
    """Détecte un état mental parmi OPEN, CLOSE, IDLE."""

    STATES = ("OPEN", "CLOSE", "IDLE")

    def __init__(
        self,
        alpha_high_threshold: float = 1.5,
        alpha_low_threshold: float = 0.5,
        smoothing_window: int = 5,
    ):
        self.alpha_high = alpha_high_threshold
        self.alpha_low = alpha_low_threshold
        self._history: deque[str] = deque(maxlen=smoothing_window)

    def detect(self, features: dict[str, float]) -> Literal["OPEN", "CLOSE", "IDLE"]:
        """Retourne l'état mental détecté à partir des features."""
        alpha = features.get("alpha", 0.0)

        if alpha > self.alpha_high:
            state = "OPEN"
        elif alpha < self.alpha_low:
            state = "CLOSE"
        else:
            state = "IDLE"

        self._history.append(state)
        # Vote majoritaire pour lisser les transitions
        return max(set(self._history), key=self._history.count)

    def reset(self) -> None:
        """Réinitialise l'historique."""
        self._history.clear()
