#!/usr/bin/env python3
"""Calibration BCI sur le cerveau de l'utilisateur (FP1 + FC3 du cahier des charges).

Protocole guide : l'utilisateur imagine tour a tour FERMER puis OUVRIR la main
droite. Pendant ce temps, le pipeline g.Pype calcule les puissances alpha (8-12 Hz)
et beta (13-30 Hz) sur C3. On entraine ensuite un classifieur LINEAIRE (LDA) sur
ces deux caracteristiques, et on sauvegarde les poids dans config/calibration.json.

Le pipeline principal (gpype_pipeline.py) charge ensuite ces poids : l'etat
OUVERT/FERME devient adapte a TON cerveau (au lieu d'un seuil generique).

Usage :
    venv\\Scripts\\python.exe scripts\\calibrate.py           # casque reel
    venv\\Scripts\\python.exe scripts\\calibrate.py --sim      # test mecanique sans casque
    venv\\Scripts\\python.exe scripts\\calibrate.py --blocks 8 # plus d'essais = plus fiable
"""

import argparse
import glob
import json
import os
import sys
import time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np  # noqa: E402
import gpype as gp  # noqa: E402
from gpype.backend.core.node import Node  # noqa: E402
Node._is_executed_in_ide = lambda self: True

# On reutilise le pipeline principal pour garantir des caracteristiques identiques.
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "gpype_pipeline", os.path.join(os.path.dirname(__file__), "gpype_pipeline.py"))
gpp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gpp)

CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json")
SETTLE = 1.5  # s a ignorer en debut de consigne (le temps que la moyenne 1 s se remplisse)


def big(msg):
    print("\n" + "=" * 56)
    print(f"   {msg}")
    print("=" * 56, flush=True)


def run(serial, mode, blocks, cue_dur, rest_dur, prep_dur):
    """Enregistre les puissances pendant le protocole. Renvoie (csv_path, schedule)."""
    p = gp.Pipeline()
    source = gpp.make_source(mode, serial)
    merger = gpp.build_calib_recorder(p, source)
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.abspath(os.path.join(out_dir, "calib_rec.csv"))
    p.connect(merger, gp.CsvWriter(file_name=base))

    schedule = []  # (t_start, t_end, label)  label: 1=FERMER, 0=OUVRIR
    p.start()
    t0 = time.time()

    def wait(sec):
        time.sleep(sec)

    big("CALIBRATION - reste immobile, regarde l'ecran")
    print("Prepare-toi... (respire calmement)")
    wait(prep_dur)

    for b in range(blocks):
        # --- FERMER ---
        big(f"Bloc {b+1}/{blocks}  >>> IMAGINE FERMER LA MAIN DROITE <<<")
        print("(imagine serrer le poing, sans bouger)")
        ts = time.time() - t0
        wait(cue_dur)
        schedule.append((ts + SETTLE, time.time() - t0, 1))
        big("... repos ...")
        wait(rest_dur)
        # --- OUVRIR ---
        big(f"Bloc {b+1}/{blocks}  <<< IMAGINE OUVRIR LA MAIN DROITE >>>")
        print("(imagine ouvrir grand la main, sans bouger)")
        ts = time.time() - t0
        wait(cue_dur)
        schedule.append((ts + SETTLE, time.time() - t0, 0))
        big("... repos ...")
        wait(rest_dur)

    p.stop()
    big("Enregistrement termine.")
    csv_path = sorted(glob.glob(base.replace(".csv", "*.csv")), key=os.path.getmtime)[-1]
    return csv_path, schedule


def label_data(csv_path, schedule):
    """Retourne X (n,2) = [alpha, beta] et y (n,) = 1 fermer / 0 ouvrir."""
    import csv
    rows = list(csv.reader(open(csv_path)))
    data = np.array([[float(v) for v in r] for r in rows[1:]])  # Time, alpha, beta
    t, alpha, beta = data[:, 0], data[:, 1], data[:, 2]
    X, y = [], []
    for (ts, te, label) in schedule:
        mask = (t >= ts) & (t < te)
        idx = np.where(mask)[0]
        # sous-echantillonnage a ~4 Hz pour reduire l'autocorrelation
        for j in idx[::62]:
            X.append([alpha[j], beta[j]])
            y.append(label)
    return np.array(X), np.array(y)


def train_and_save(X, y):
    from sklearn.preprocessing import StandardScaler
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.model_selection import cross_val_score

    if len(np.unique(y)) < 2 or len(y) < 10:
        print("[X] Pas assez de donnees exploitables (2 classes requises).")
        return None

    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    lda = LinearDiscriminantAnalysis()
    try:
        cv = cross_val_score(lda, Xs, y, cv=min(5, np.bincount(y).min()))
        acc = float(np.mean(cv))
    except Exception:
        acc = float("nan")
    lda.fit(Xs, y)

    # Replier scaler + LDA en poids sur les puissances BRUTES :
    #   decision(x) = coef . (x-mean)/scale + intercept  =  wa*alpha + wb*beta + bias
    coef = lda.coef_[0]
    wa = float(coef[0] / scaler.scale_[0])
    wb = float(coef[1] / scaler.scale_[1])
    bias = float(lda.intercept_[0]
                 - coef[0] * scaler.mean_[0] / scaler.scale_[0]
                 - coef[1] * scaler.mean_[1] / scaler.scale_[1])

    print(f"\nPrecision (validation croisee) : {acc*100:.0f} %  sur {len(y)} echantillons")
    print(f"Poids appris : etat = sign({wa:.4g}*alpha + {wb:.4g}*beta + {bias:.4g})")
    if not np.isnan(acc) and acc < 0.65:
        print("[!] Precision faible : verifie le contact des electrodes (C3) et refais la calibration.")

    os.makedirs(os.path.dirname(CALIB_PATH), exist_ok=True)
    with open(CALIB_PATH, "w", encoding="utf-8") as f:
        json.dump({"wa": wa, "wb": wb, "bias": bias,
                   "accuracy": acc, "n_samples": int(len(y)),
                   "channel": "C3", "features": ["alpha_power", "beta_power"]},
                  f, indent=2)
    print(f"[OK] Calibration sauvegardee : {os.path.abspath(CALIB_PATH)}")
    return acc


def main():
    ap = argparse.ArgumentParser(description="Calibration BCI (LDA) sur le casque")
    ap.add_argument("--sim", action="store_true", help="Sans casque (test mecanique)")
    ap.add_argument("--serial", default=gpp.DEFAULT_SERIAL)
    ap.add_argument("--blocks", type=int, default=6, help="Nombre d'essais par classe")
    ap.add_argument("--cue", type=float, default=5.0, help="Duree d'une consigne (s)")
    ap.add_argument("--rest", type=float, default=3.0, help="Duree de repos (s)")
    ap.add_argument("--prep", type=float, default=3.0, help="Duree de preparation (s)")
    args = ap.parse_args()
    mode = "sim" if args.sim else "casque"

    total = args.prep + args.blocks * 2 * (args.cue + args.rest)
    print(f"Protocole : {args.blocks} essais x 2 classes, ~{total:.0f} s au total.")
    try:
        csv_path, schedule = run(args.serial, mode, args.blocks,
                                 args.cue, args.rest, args.prep)
        X, y = label_data(csv_path, schedule)
        print(f"Echantillons etiquetes : {len(y)} "
              f"(fermer={int(np.sum(y==1))}, ouvrir={int(np.sum(y==0))})")
        train_and_save(X, y)
        print("\nLance maintenant le pipeline : il utilisera automatiquement ta calibration.")
        return 0
    except Exception as e:
        import traceback
        print(f"\n[ERREUR] {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
