"""Détecteur d'état mental pour la commande cérébrale.

Deux stratégies sont disponibles :
1. **Machine Learning** : si un modèle entraîné existe dans
   `src/inclusive_maker/brain_algo/models/`, il est utilisé.
2. **Seuils ratio alpha/bêta** : fallback simple si aucun modèle n'est disponible.

Stratégie par ratio :
- ratio alpha/bêta élevé → OPEN (relaxation)
- ratio bêta/alpha élevé → CLOSE (concentration / effort)
- ratio intermédiaire → IDLE
"""

from collections import deque
from typing import Literal, Optional

from .classifier import EEGStateClassifier


class MentalStateDetector:
    """Détecte un état mental parmi OPEN, CLOSE, IDLE."""

    STATES = ("OPEN", "CLOSE", "IDLE")

    def __init__(
        self,
        open_ratio: float = 4.0,
        close_ratio: float = 8.0,
        smoothing_window: int = 3,
        model_path: Optional[str] = None,
    ):
        self.open_ratio = open_ratio
        self.close_ratio = close_ratio
        self._history: deque[str] = deque(maxlen=smoothing_window)
        self._classifier = EEGStateClassifier(model_path)
        self._use_ml = self._classifier.is_trained()

    def detect(self, features: dict[str, float]) -> Literal["OPEN", "CLOSE", "IDLE"]:
        """Retourne l'état mental détecté à partir des features."""
        if self._use_ml:
            state = self._classifier.predict(features)
        else:
            state = self._detect_threshold(features)

        self._history.append(state)
        # Vote majoritaire pour lisser les transitions
        return max(set(self._history), key=self._history.count)

    def _detect_threshold(self, features: dict[str, float]) -> str:
        """Détection par seuils de ratio (fallback)."""
        alpha = max(features.get("alpha", 0.0), 1e-9)
        beta = max(features.get("beta", 0.0), 1e-9)

        alpha_beta_ratio = alpha / beta
        beta_alpha_ratio = beta / alpha

        if alpha_beta_ratio >= self.open_ratio:
            return "OPEN"
        if beta_alpha_ratio >= self.close_ratio:
            return "CLOSE"
        return "IDLE"

    def reset(self) -> None:
        """Réinitialise l'historique."""
        self._history.clear()

    @property
    def uses_ml(self) -> bool:
        """True si le détecteur utilise le modèle ML entraîné."""
        return self._use_ml
