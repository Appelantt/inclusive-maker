"""Traduit un état mental détecté en commande à envoyer."""

from typing import Any

from ..shared.constants import DEFAULT_UDP_IP, DEFAULT_UDP_PORT


class CommandMapper:
    """Associe un état mental à une payload de commande."""

    DEFAULT_COMMANDS = {
        "OPEN": {
            "action": "OPEN",
            "value": 1.0,
            "label": "open_hand",
        },
        "CLOSE": {
            "action": "CLOSE",
            "value": -1.0,
            "label": "close_hand",
        },
        "IDLE": {
            "action": "IDLE",
            "value": 0.0,
            "label": "idle",
        },
    }

    def __init__(self, commands: dict[str, dict[str, Any]] | None = None):
        self.commands = commands or self.DEFAULT_COMMANDS

    def map(self, state: str) -> dict[str, Any]:
        """Retourne la commande associée à l'état."""
        return self.commands.get(state, self.commands["IDLE"]).copy()
