"""Détecteur d'état mental simple pour la commande cérébrale.

Stratégie basée sur les puissances alpha et bêta :
- forte puissance alpha / faible bêta → OPEN (relaxation)
- forte puissance bêta / faible alpha → CLOSE (concentration / effort)
- entre les deux → IDLE

C'est un exemple pédagogique à remplacer par un vrai classifieur entraîné.
"""

from collections import deque
from typing import Literal


class MentalStateDetector:
    """Détecte un état mental parmi OPEN, CLOSE, IDLE."""

    STATES = ("OPEN", "CLOSE", "IDLE")

    def __init__(
        self,
        alpha_high_threshold: float = 30.0,
        beta_high_threshold: float = 10.0,
        smoothing_window: int = 5,
    ):
        self.alpha_high = alpha_high_threshold
        self.beta_high = beta_high_threshold
        self._history: deque[str] = deque(maxlen=smoothing_window)

    def detect(self, features: dict[str, float]) -> Literal["OPEN", "CLOSE", "IDLE"]:
        """Retourne l'état mental détecté à partir des features."""
        alpha = features.get("alpha", 0.0)
        beta = features.get("beta", 0.0)

        if alpha > self.alpha_high and beta < self.beta_high:
            state = "OPEN"
        elif beta > self.beta_high and alpha < self.alpha_high:
            state = "CLOSE"
        else:
            state = "IDLE"

        self._history.append(state)
        # Vote majoritaire pour lisser les transitions
        return max(set(self._history), key=self._history.count)

    def reset(self) -> None:
        """Réinitialise l'historique."""
        self._history.clear()
