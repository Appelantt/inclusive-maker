"""Client WebSocket pour envoyer les commandes détectées.

Utile pour une interface web, un dashboard navigateur, ou une communication
avec d'autres applications en local.
"""

import asyncio
import json

import websockets

from .protocol import CommandPacket


class CommandWebSocketClient:
    """Envoie les commandes vers un serveur WebSocket."""

    def __init__(self, uri: str = "ws://127.0.0.1:8765"):
        self.uri = uri
        self._websocket = None

    async def connect(self) -> None:
        self._websocket = await websockets.connect(self.uri)

    async def send(self, packet: CommandPacket) -> None:
        if self._websocket is None:
            await self.connect()
        await self._websocket.send(packet.to_json())

    async def close(self) -> None:
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

    def send_sync(self, packet: CommandPacket) -> None:
        """Version synchrone pratique depuis du code non-async."""
        asyncio.run(self.send(packet))
