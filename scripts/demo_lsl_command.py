#!/usr/bin/env python3
"""Démonstration LSL : envoi de commandes cérébrales via Lab Streaming Layer.

Terminal 1 - Émetteur :
    set PYTHONPATH=src
    python scripts\demo_lsl_command.py --sender

Terminal 2 - Récepteur :
    set PYTHONPATH=src
    python scripts\demo_lsl_command.py --receiver
"""

import argparse
import time

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.remote_command.lsl_streamer import CommandLSLStreamer
from inclusive_maker.remote_command.lsl_receiver import CommandLSLReceiver
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


def run_sender(duration: float = 30.0):
    generator = EEGGenerator("IDLE")
    detector = MentalStateDetector()
    mapper = CommandMapper()
    streamer = CommandLSLStreamer()

    print(f"Stream LSL démarré - envoi pendant {duration}s...")
    start = time.time()
    step = 0
    states = ["OPEN", "IDLE", "CLOSE", "IDLE"]

    try:
        while time.time() - start < duration:
            state = states[step % len(states)]
            generator.set_state(state)
            eeg = generator.read_window(1.0)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            detected = detector.detect(features)
            cmd = mapper.map(detected)
            packet = CommandPacket(
                action=cmd["action"],
                value=cmd["value"],
                label=cmd["label"],
                timestamp=time.time(),
            )
            streamer.send(packet)
            print(f"[{state}] -> {detected} -> {packet.to_dict()}")
            step += 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nArrêt de l'émetteur.")


def run_receiver(duration: float = 30.0):
    receiver = CommandLSLReceiver()
    start = time.time()
    print("Récepteur en écoute...")
    try:
        while time.time() - start < duration:
            packet = receiver.receive()
            print(f"[REÇU] {packet.to_dict()}")
    except KeyboardInterrupt:
        print("\nArrêt du récepteur.")


def main():
    parser = argparse.ArgumentParser(description="Démo LSL commandes cérébrales")
    parser.add_argument("--sender", action="store_true", help="Mode émetteur")
    parser.add_argument("--receiver", action="store_true", help="Mode récepteur")
    parser.add_argument("--duration", type=float, default=30.0, help="Durée en secondes")
    args = parser.parse_args()

    if args.sender:
        run_sender(args.duration)
    elif args.receiver:
        run_receiver(args.duration)
    else:
        print("Utilise --sender ou --receiver")


if __name__ == "__main__":
    main()
