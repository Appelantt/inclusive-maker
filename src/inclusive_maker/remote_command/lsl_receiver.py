"""Récepteur LSL pour recevoir les commandes détectées.

Utile pour le côté client qui pilote le gant ou une interface de démonstration.
"""

from pylsl import StreamInlet, resolve_byprop

from ..shared.constants import DEFAULT_LSL_STREAM_NAME
from .protocol import CommandPacket


class CommandLSLReceiver:
    """Reçoit les commandes depuis un stream LSL."""

    def __init__(self, stream_name: str = DEFAULT_LSL_STREAM_NAME, timeout: float = 5.0):
        print(f"Recherche du stream LSL '{stream_name}'...")
        streams = resolve_byprop("name", stream_name, timeout=timeout)
        if not streams:
            raise RuntimeError(f"Stream LSL '{stream_name}' non trouvé.")
        self.inlet = StreamInlet(streams[0])
        print("Stream LSL connecté.")

    def receive(self) -> CommandPacket:
        """Bloque jusqu'à réception d'une commande."""
        sample, _ = self.inlet.pull_sample()
        payload = sample[0]
        return CommandPacket.from_dict(__import__("json").loads(payload))
