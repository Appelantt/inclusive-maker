#!/usr/bin/env python3
"""Serveur simulé de reception des commandes pour le gant.

Ce script remplace l'Arduino/RPi pendant les tests sans matériel.
Il recoit les commandes UDP et affiche l'action correspondante.
"""

import socket
import json
import time

from inclusive_maker.shared.constants import DEFAULT_UDP_IP, DEFAULT_UDP_PORT


ACTION_SYMBOLS = {
    "OPEN": "✋  MAIN OUVERTE",
    "CLOSE": "✊  MAIN FERMEE",
    "IDLE": "⏸  POSITION MAINTENUE",
}


def run_mock_server(ip: str = DEFAULT_UDP_IP, port: int = DEFAULT_UDP_PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    sock.settimeout(1.0)

    print(f"[MOCK HAND] En ecoute sur {ip}:{port}")
    print("Appuyez sur Ctrl+C pour quitter.\n")

    last_action = None
    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue

            try:
                packet = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                print(f"[ERREUR] Paquet invalide recu : {data}")
                continue

            action = packet.get("action", "UNKNOWN")
            value = packet.get("value", 0.0)
            label = packet.get("label", "unknown")
            timestamp = packet.get("timestamp", time.time())

            if action != last_action:
                symbol = ACTION_SYMBOLS.get(action, f"[{action}]")
                print(f"{symbol} | valeur={value:+.1f} | label={label} | ts={timestamp:.3f}")
                last_action = action

    except KeyboardInterrupt:
        print("\n[MOCK HAND] Arret.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_mock_server()
