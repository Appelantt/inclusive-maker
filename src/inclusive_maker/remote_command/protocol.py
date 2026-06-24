"""Définition du protocole de commande à distance."""

import json
from dataclasses import dataclass, asdict
from typing import Literal


@dataclass
class CommandPacket:
    """Paquet de commande normalisé envoyé à distance."""

    action: Literal["OPEN", "CLOSE", "IDLE"]
    value: float
    label: str
    timestamp: float | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CommandPacket":
        return cls(**data)
