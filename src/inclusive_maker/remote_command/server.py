"""Serveur UDP de commande à distance."""

import socket
import json
import threading
from typing import Callable

from ..shared.logger import get_logger
from ..shared.constants import DEFAULT_UDP_IP, DEFAULT_UDP_PORT
from .protocol import CommandPacket

logger = get_logger(__name__)


class CommandServer:
    """Écoute les commandes UDP entrantes et les transmet au handler."""

    def __init__(
        self,
        ip: str = DEFAULT_UDP_IP,
        port: int = DEFAULT_UDP_PORT,
        handler: Callable[[CommandPacket], None] | None = None,
    ):
        self.ip = ip
        self.port = port
        self.handler = handler or self._default_handler
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def _default_handler(self, packet: CommandPacket) -> None:
        logger.info(f"Commande reçue : {packet.to_dict()}")

    def start(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self.ip, self.port))
        self._socket.settimeout(0.5)
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info(f"Serveur UDP démarré sur {self.ip}:{self.port}")

    def _listen(self) -> None:
        while self._running:
            try:
                data, addr = self._socket.recvfrom(1024)
                payload = json.loads(data.decode("utf-8"))
                packet = CommandPacket.from_dict(payload)
                self.handler(packet)
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"Paquet mal formé : {e}")
            except Exception as e:
                logger.error(f"Erreur serveur : {e}")

    def stop(self) -> None:
        self._running = False
        if self._socket:
            self._socket.close()
        if self._thread:
            self._thread.join()
        logger.info("Serveur UDP arrêté.")
