#!/usr/bin/env python3
"""Démonstration complète de la chaîne sans casque EEG.

Simule l'acquisition EEG, la classification et l'envoi UDP de commandes.
Usage : PYTHONPATH=src python scripts/demo_full_pipeline.py
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
    print("=" * 60)
    print(" Inclusive Maker - Démonstration complète sans casque")
    print("=" * 60)
    print(f"\nDuree : {duration}s | Intervalle : {interval}s")
    print("\nSequence : OPEN (5s) -> CLOSE (5s) -> IDLE (5s) ...\n")

    generator = EEGGenerator("IDLE")
    detector = MentalStateDetector()
    mapper = CommandMapper()
    client = CommandClient()

    sequence = ["OPEN", "CLOSE", "IDLE"]
    start = time.time()
    step = 0

    try:
        while time.time() - start < duration:
            state = sequence[step % len(sequence)]
            generator.set_state(state)
            detector.reset()

            eeg = generator.read_window(interval)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            detected = detector.detect(features)
            cmd = mapper.map(detected)
            packet = CommandPacket(
                action=cmd["action"],
                value=cmd["value"],
                label=cmd["label"],
                timestamp=time.time(),
            )
            client.send(packet)

            print(
                f"[SIMULE: {state:5}] "
                f"alpha={features['alpha']:6.1f} beta={features['beta']:6.1f} "
                f"-> [DETECTE: {detected:5}] -> {packet.to_dict()}"
            )

            step += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur.")
    finally:
        client.close()
        print("\nDémonstration terminee.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Démonstration complète sans casque")
    parser.add_argument("--duration", type=float, default=30.0, help="Duree de la demo en secondes")
    parser.add_argument("--interval", type=float, default=1.0, help="Intervalle entre commandes")
    args = parser.parse_args()
    run_demo(args.duration, args.interval)
