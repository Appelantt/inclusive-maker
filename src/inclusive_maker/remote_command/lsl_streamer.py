"""Streamer LSL pour envoyer les commandes détectées.

LSL (Lab Streaming Layer) permet de diffuser les commandes cérébrales vers
d'autres applications en temps réel (OpenVIBE, BCILAB, etc.).
"""

from pylsl import StreamInfo, StreamOutlet

from ..shared.constants import DEFAULT_LSL_STREAM_NAME
from .protocol import CommandPacket


class CommandLSLStreamer:
    """Diffuse les commandes sous forme de stream LSL."""

    def __init__(self, stream_name: str = DEFAULT_LSL_STREAM_NAME):
        info = StreamInfo(
            name=stream_name,
            type="Markers",
            channel_count=1,
            nominal_srate=0,
            channel_format="string",
            source_id="inclusive_maker_commands",
        )
        self.outlet = StreamOutlet(info)

    def send(self, packet: CommandPacket) -> None:
        """Envoie une commande sur le stream LSL."""
        payload = packet.to_json()
        self.outlet.push_sample([payload])
