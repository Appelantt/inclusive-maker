"""Lance le serveur UDP de réception des commandes."""

import time

from inclusive_maker.remote_command.server import CommandServer
from inclusive_maker.remote_command.protocol import CommandPacket


def on_command(packet: CommandPacket) -> None:
    """Handler appelé à chaque commande reçue."""
    print(f"[REÇU] {packet.to_dict()}")


def main() -> None:
    server = CommandServer(handler=on_command)
    server.start()
    print("Serveur en écoute. Ctrl+C pour arrêter.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
