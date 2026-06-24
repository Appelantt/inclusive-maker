"""Client UDP pour envoyer des commandes à distance."""

import socket
import json

from ..shared.logger import get_logger
from ..shared.constants import DEFAULT_UDP_IP, DEFAULT_UDP_PORT
from .protocol import CommandPacket

logger = get_logger(__name__)


class CommandClient:
    """Envoie des CommandPacket vers un serveur UDP."""

    def __init__(self, ip: str = DEFAULT_UDP_IP, port: int = DEFAULT_UDP_PORT):
        self.ip = ip
        self.port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, packet: CommandPacket) -> None:
        """Envoie un paquet de commande."""
        payload = packet.to_json().encode("utf-8")
        self._socket.sendto(payload, (self.ip, self.port))
        logger.debug(f"Envoyé : {packet.to_dict()}")

    def close(self) -> None:
        self._socket.close()
