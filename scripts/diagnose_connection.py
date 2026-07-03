#!/usr/bin/env python3
"""Diagnostic de connexion au casque Unicorn Hybrid Black.

Teste, l'un apres l'autre, les differents chemins de connexion et affiche un
verdict clair en francais indiquant lequel fonctionne (ou pourquoi aucun ne
marche). A lancer casque allume, avant de demarrer l'application principale.

Usage :
    venv\\Scripts\\python.exe scripts\\diagnose_connection.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Noms de processus qui, s'ils tournent, occupent le casque en Bluetooth et
# empechent la connexion directe (gtec-ble) de l'application.
UNICORN_PROCESSES = [
    "UnicornSuite.exe",
    "Unicorn Suite.exe",
    "UnicornRecorder.exe",
    "Unicorn Recorder.exe",
    "myUnicorn.exe",
    "Unicorn.exe",
]

LINE = "=" * 64


def title(text):
    print("\n" + LINE)
    print(f"  {text}")
    print(LINE)


def check_unicorn_processes():
    title("1. Logiciels Unicorn en cours d'execution")
    running = []
    try:
        import subprocess
        out = subprocess.run(
            ["tasklist"], capture_output=True, text=True, timeout=15
        ).stdout.lower()
        for proc in UNICORN_PROCESSES:
            if proc.lower() in out:
                running.append(proc)
    except Exception as e:
        print(f"  [?] Impossible de lister les processus : {e}")
        return None

    if running:
        print("  [!] Logiciel(s) Unicorn detecte(s) : " + ", ".join(running))
        print("      -> Ils occupent le casque en Bluetooth.")
        print("      -> Pour la connexion DIRECTE (gtec-ble), FERME-les d'abord.")
        print("      -> Pour le mode LSL, garde Unicorn Recorder ouvert ET active")
        print("         son streaming LSL.")
    else:
        print("  [OK] Aucun logiciel Unicorn detecte : le casque est libre pour")
        print("       une connexion Bluetooth directe.")
    return running


def test_gtec_ble():
    title("2. Connexion Bluetooth directe (gtec-ble)")
    try:
        import hashlib
        import uuid
        from gtec_ble.amplifier import Amplifier
    except ImportError as e:
        print(f"  [X] Package gtec-ble absent : {e}")
        return False

    mac = uuid.getnode()
    key = hashlib.sha256(f"{mac:012x}".encode()).hexdigest()
    try:
        Amplifier.register(key=key)
        print("  [OK] Cle de licence acceptee (machine autorisee).")
    except Exception as e:
        print(f"  [X] Enregistrement de la cle refuse : {e}")
        return False

    print("  ... Scan Bluetooth en cours (~6 s), casque allume et clignotant bleu...")
    try:
        devices = Amplifier.get_connected_devices()
    except Exception as e:
        print(f"  [X] Erreur pendant le scan Bluetooth : {e}")
        return False

    if devices:
        print(f"  [OK] Casque(s) detecte(s) : {devices}")
        print("       -> La connexion Bluetooth directe FONCTIONNE.")
        return True

    print("  [X] Aucun casque detecte en Bluetooth LOW ENERGY (BLE).")
    print("      NB : l'Unicorn Hybrid Black communique en Bluetooth CLASSIQUE")
    print("      (port COM serie), pas en BLE. Ce chemin ne marchera donc")
    print("      probablement JAMAIS pour ce casque -> utilise le mode LSL")
    print("      (etape 3, via l'application UnicornLSL.exe).")
    return False


def test_lsl():
    title("3. Stream LSL (Unicorn Recorder)")
    try:
        from pylsl import resolve_byprop
    except ImportError as e:
        print(f"  [X] Package pylsl absent : {e}")
        return False

    print("  ... Recherche d'un flux LSL de type EEG (~5 s)...")
    try:
        streams = resolve_byprop("type", "EEG", timeout=5.0)
    except Exception as e:
        print(f"  [X] Erreur de resolution LSL : {e}")
        return False

    if streams:
        s = streams[0]
        print(f"  [OK] Flux EEG LSL trouve : {s.name()} "
              f"({s.channel_count()} canaux, {s.nominal_srate()} Hz)")
        print("       -> Le mode LSL FONCTIONNE.")
        return True

    print("  [X] Aucun flux EEG LSL trouve.")
    print("      Pour l'activer : ouvre Unicorn Recorder, connecte le casque,")
    print("      puis active l'option de streaming LSL avant de relancer ce test.")
    return False


def verdict(running, ble_ok, lsl_ok):
    title("VERDICT")
    if lsl_ok:
        print("  >> Utilise le MODE LSL (recommande pour l'Unicorn Hybrid Black).")
        print("     Garde l'application Unicorn LSL ouverte avec le streaming actif,")
        print("     puis lance l'application (ou clique 'Reconnecter le casque').")
    elif ble_ok:
        print("  >> Connexion Bluetooth directe (BLE) disponible : lance l'appli,")
        print("     elle se connectera au casque automatiquement.")
    else:
        print("  >> Aucun chemin ne fonctionne pour l'instant.")
        print("     Action recommandee (chemin fiable pour ce casque) :")
        print("       1. Ouvre l'application 'Unicorn LSL' (UnicornLSL.exe) :")
        print("          Documents\\gtec\\Unicorn Suite\\Hybrid Black\\Unicorn LSL\\")
        print("       2. Selectionne le casque (UN-...) et clique Open puis Start.")
        print("       3. Relance ce diagnostic : l'etape 3 (LSL) doit passer au VERT.")
        if running:
            print("     NB : ferme d'abord les autres logiciels Unicorn (" +
                  ", ".join(running) + ") qui occupent le casque.")
        print("     En attendant, l'application fonctionne en mode SIMULATEUR.")
    print(LINE + "\n")


def main():
    print("\n  Diagnostic de connexion - Casque Unicorn Hybrid Black")
    running = check_unicorn_processes()
    ble_ok = test_gtec_ble()
    lsl_ok = test_lsl()
    verdict(running or [], ble_ok, lsl_ok)
    return 0 if (ble_ok or lsl_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
