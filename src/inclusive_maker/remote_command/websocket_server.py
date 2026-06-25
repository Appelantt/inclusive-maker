"""Serveur WebSocket de réception des commandes.

Reçoit les CommandPacket et les affiche.  Peut être branché sur un handler
personnalisé pour piloter un matériel.
"""

import asyncio
import json

import websockets

from .protocol import CommandPacket
from ..shared.logger import get_logger

logger = get_logger(__name__)


class CommandWebSocketServer:
    """Écoute les commandes WebSocket entrantes."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._server = None

    async def _handler(self, websocket):
        async for message in websocket:
            try:
                data = json.loads(message)
                packet = CommandPacket.from_dict(data)
                logger.info(f"Commande WebSocket reçue : {packet.to_dict()}")
            except Exception as e:
                logger.warning(f"Message WebSocket invalide : {e}")

    async def start(self) -> None:
        self._server = await websockets.serve(self._handler, self.host, self.port)
        logger.info(f"Serveur WebSocket démarré sur ws://{self.host}:{self.port}")
        await asyncio.Future()  # run forever

    def start_sync(self) -> None:
        asyncio.run(self.start())
