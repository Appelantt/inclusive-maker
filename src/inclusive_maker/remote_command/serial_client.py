"""Client série (Serial/COM) pour envoyer des commandes à un Arduino.

Format simple : une ligne JSON par commande.
"""

import json
from typing import Optional

import serial

from ..shared.logger import get_logger
from .protocol import CommandPacket

logger = get_logger(__name__)


class CommandSerialClient:
    """Envoie les CommandPacket sur un port série (UART/USB)."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._ser: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Ouvre le port série."""
        self._ser = serial.Serial(self.port, self.baudrate, timeout=1)
        logger.info(f"Port série {self.port} ouvert à {self.baudrate} bauds.")

    def send(self, packet: CommandPacket) -> None:
        """Envoie une commande sur le port série."""
        if self._ser is None:
            self.connect()
        line = packet.to_json() + "\n"
        self._ser.write(line.encode("utf-8"))
        logger.debug(f"Envoyé sur série : {packet.to_dict()}")

    def close(self) -> None:
        if self._ser:
            self._ser.close()
            self._ser = None
