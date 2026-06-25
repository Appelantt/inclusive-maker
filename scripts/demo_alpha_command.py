"""Démonstration : signaux synthétiques -> features -> commande UDP.

Ce script simule une chaîne complète sans matériel, pour tester la structure
du projet sur n'importe quelle machine.

Il utilise le générateur EEG du projet (EEGGenerator) qui produit des
signaux réalistes par état mental (OPEN = fort alpha, CLOSE = fort beta,
IDLE = neutre), puis les envoie en UDP.
"""

import time
import argparse

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.client import CommandClient
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


def run_demo(duration: float = 30.0, interval: float = 1.0):
    detector = MentalStateDetector(
        open_ratio=4.0,
        close_ratio=8.0,
        smoothing_window=3,
    )
    mapper = CommandMapper()
    client = CommandClient()
    generator = EEGGenerator("IDLE")

    print("Démonstration inclusive Maker - appuyez sur Ctrl+C pour arrêter")
    print("-" * 60)

    states_cycle = ["OPEN", "IDLE", "CLOSE", "IDLE"]
    start = time.time()
    step = 0

    try:
        while time.time() - start < duration:
            state = states_cycle[step % len(states_cycle)]
            generator.set_state(state)
            detector.reset()

            eeg = generator.read_window(interval)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            detected = detector.detect(features)
            command = mapper.map(detected)
            packet = CommandPacket(
                action=command["action"],
                value=command["value"],
                label=command["label"],
                timestamp=time.time(),
            )
            client.send(packet)
            print(
                f"[{state:5}] alpha={features['alpha']:6.1f} beta={features['beta']:6.1f} "
                f"-> {detected:5} -> {packet.to_dict()}"
            )
            step += 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Démonstration alpha/beta -> commande UDP")
    parser.add_argument("--duration", type=float, default=30.0, help="Durée de la démo en secondes")
    parser.add_argument("--interval", type=float, default=1.0, help="Durée de chaque fenêtre EEG en secondes")
    args = parser.parse_args()
    run_demo(args.duration, args.interval)


if __name__ == "__main__":
    main()
