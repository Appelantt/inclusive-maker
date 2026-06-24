"""Tests de la commande à distance."""

import json
import time

from inclousive_maker.remote_command.protocol import CommandPacket
from inclousive_maker.remote_command.server import CommandServer
from inclousive_maker.remote_command.client import CommandClient


def test_command_packet_roundtrip():
    packet = CommandPacket(action="OPEN", value=1.0, label="open_hand", timestamp=time.time())
    payload = packet.to_json()
    restored = CommandPacket.from_dict(json.loads(payload))
    assert restored.action == packet.action
    assert restored.value == packet.value


def test_udp_server_client():
    received = []

    def handler(packet):
        received.append(packet)

    server = CommandServer(ip="127.0.0.1", port=56001, handler=handler)
    server.start()

    client = CommandClient(ip="127.0.0.1", port=56001)
    packet = CommandPacket(action="CLOSE", value=-1.0, label="close_hand", timestamp=time.time())
    client.send(packet)

    # Attendre la réception
    time.sleep(0.5)

    server.stop()
    client.close()

    assert len(received) == 1
    assert received[0].action == "CLOSE"
