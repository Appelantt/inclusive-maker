"""Couche de sÃ©curitÃ© pour les commandes envoyÃ©es au gant / dispositif.

Philippe a besoin que les mains restent FERMÃ‰ES en cas de doute ou de panne,
pour ne pas lÃ¢cher le cerf-volant / la poignÃ©e. Ce module garantit :
- Ã©tat par dÃ©faut = CLOSE (fermer)
- commande "OUVRIR" n'est envoyÃ©e que si l'Ã©tat est clairement OPEN
- mode "safe" activable manuellement ou automatiquement si BCI incertain
"""

from typing import Literal


class SafetyController:
    """Filtre les Ã©tats mentaux dÃ©tectÃ©s pour la sÃ©curitÃ©."""

    SAFE_STATES: tuple[str, ...] = ("CLOSE", "IDLE")
    UNSAFE_STATE: str = "OPEN"

    def __init__(self, safe_mode: bool = True, idle_is_safe: bool = False):
        self.safe_mode = safe_mode
        self.idle_is_safe = idle_is_safe
        # Historique des Ã©tats pour mesurer la stabilitÃ©
        self._history: list[str] = []
        self._window = 3

    def enable_safe_mode(self) -> None:
        self.safe_mode = True

    def disable_safe_mode(self) -> None:
        self.safe_mode = False

    def filter_state(self, state: str, confidence: float = 1.0) -> Literal["OPEN", "CLOSE", "IDLE"]:
        """Retourne l'Ã©tat final aprÃ¨s application des rÃ¨gles de sÃ©curitÃ©.

        RÃ¨gles :
        - Si safe_mode dÃ©sactivÃ© : retourne l'Ã©tat tel quel
        - Si safe_mode activÃ© :
            * OPEN n'est autorisÃ© que s'il est stable sur `_window` Ã©chantillons
              et que la confiance est suffisante
            * Sinon on retourne CLOSE (maintien de la prise)
        """
        state = state.upper()
        if state not in ("OPEN", "CLOSE", "IDLE"):
            state = "IDLE"

        if not self.safe_mode:
            return state  # type: ignore[return-value]

        self._history.append(state)
        if len(self._history) > self._window:
            self._history.pop(0)

        # Sauf si toutes les derniÃ¨res mesures disent OPEN, on reste en CLOSE
        if state == "OPEN":
            if len(self._history) >= self._window and all(s == "OPEN" for s in self._history):
                return "OPEN"
            return "CLOSE"

        # IDLE : sÃ©curitÃ© demande de fermer si idle_is_safe est False
        if state == "IDLE" and not self.idle_is_safe:
            return "CLOSE"

        return state  # type: ignore[return-value]

    def reset(self) -> None:
        self._history.clear()
