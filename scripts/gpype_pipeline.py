#!/usr/bin/env python3
"""Pipeline BCI g.Pype pour Inclusive Maker - casque Unicorn Hybrid Black.

Chaine de traitement ENTIEREMENT en g.Pype (noeuds officiels), inspiree de
examples/example_devices_hybrid_black.py et example_composite_alpha_power.py :

  casque -> Bandpass 1-30 Hz + Notch 50/60 Hz  (EEG propre)
         -> selection du canal moteur C3
         -> puissance ALPHA (8-12 Hz) : Bandpass -> carre -> moyenne glissante
         -> puissance BETA  (13-30 Hz): Bandpass -> carre -> moyenne glissante
         -> commande = BETA - ALPHA   (>0 => fermer / concentration ;
                                        <0 => ouvrir / relaxation)
         -> affichage temps reel (ou enregistrement CSV)

Grace au monkeypatch officiel g.tec, tourne depuis n'importe quel terminal
(pas besoin de VS Code ni de licence Runtime).

Modes :
    (defaut)  : casque reel  -> pipeline BCI -> fenetre temps reel
    --sim     : signal simule -> meme pipeline -> fenetre temps reel
    --record  : casque reel   -> pipeline BCI -> CSV (sans fenetre), --seconds N

PREREQUIS casque : UnicornPy installe, casque allume/appaire, et
Unicorn Suite / LSL / Recorder FERMES.
"""

import argparse
import json
import os
import sys
import time

# UTF-8 obligatoire (sinon le thread de monitoring g.Pype plante en cp1252).
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gpype as gp  # noqa: E402

# Monkeypatch officiel g.tec : lance g.Pype hors IDE supporte.
from gpype.backend.core.node import Node  # noqa: E402
Node._is_executed_in_ide = lambda self: True

#: Casque par defaut : None = auto-detection du premier casque disponible
#: (evite de rester bloque si un casque precis est endormi/injoignable).
DEFAULT_SERIAL = None
# Disposition des electrodes du casque (index 0 a 7) :
#   0=Fz  1=C3  2=Cz  3=C4  4=Pz  5=PO7  6=PO8  7=Oz
# C3 (index 1) = cortex moteur gauche -> imagerie de la MAIN DROITE (controlateral).
# C4 (index 3) = cortex moteur droit -> main gauche.
MOTOR_CHANNEL = 1  # C3
#: Frequence d'echantillonnage du casque.
FS = 250.0
#: Fichier de calibration LDA (produit par scripts/calibrate.py).
CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json")


def load_calibration():
    """Charge la calibration LDA {wa, wb, bias} si presente, sinon None."""
    try:
        with open(CALIB_PATH, encoding="utf-8") as f:
            c = json.load(f)
        return float(c["wa"]), float(c["wb"]), float(c["bias"])
    except Exception:
        return None


def _setup_unicornpy():
    """Rend UnicornPy importable (meme logique que le noeud HybridBlack)."""
    try:
        from gpype.backend.sources.hybrid_black import _ensure_unicorn_path
        _ensure_unicorn_path()
        import UnicornPy
        return UnicornPy
    except Exception:
        return None


def list_serials(preferred):
    """Retourne la liste ordonnee des serials candidats SANS ouvrir de connexion.

    IMPORTANT : on n'ouvre volontairement PAS de connexion de pre-test ici.
    Une ouverture/fermeture prealable occupe le canal Bluetooth du casque
    pendant plusieurs secondes et fait echouer la connexion suivante du
    pipeline (DeviceException 4 « Couldn't connect »). On se contente donc de
    lister les devices visibles (GetAvailableDevices) et on laisse le pipeline
    faire la vraie connexion — avec retry si le premier candidat ne repond pas.
    """
    up = _setup_unicornpy()
    if up is None:
        return [preferred] if preferred else []
    try:
        devices = list(up.GetAvailableDevices(True) or [])
    except Exception:
        return [preferred] if preferred else []
    if not devices:
        return [preferred] if preferred else []
    order = ([preferred] if preferred in devices else []) + \
            [d for d in devices if d != preferred]
    return order


def make_source(mode: str, serial):
    if mode == "sim":
        print("Source : Generator interne g.Pype (simulation).")
        return gp.Generator(sampling_rate=FS, channel_count=8,
                            signal_frequency=10.0, signal_amplitude=30.0,
                            noise_amplitude=10.0)
    cible = serial if serial else "aucun casque detecte"
    print(f"Source : casque Unicorn Hybrid Black ({cible}).")
    print("  -> Unicorn Suite / LSL / Recorder doivent etre FERMES.")
    return gp.HybridBlack(serial=serial)


def _is_connect_error(exc):
    """True si l'exception est une erreur de connexion Bluetooth casque."""
    msg = str(exc).lower()
    return "couldn't connect" in msg or "no unicorn device" in msg


def build_features(p, source):
    """source -> EEG propre -> canal C3 -> puissances BRUTES alpha_avg et beta_avg.

    Renvoie (alpha_avg, beta_avg). Ce sont les 2 caracteristiques utilisees par
    la calibration LDA et par la commande.
    """
    # --- EEG propre : bandpass 1-30 Hz + notch secteur 50/60 Hz ---
    bandpass = gp.Bandpass(f_lo=1, f_hi=30)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    notch60 = gp.Bandstop(f_lo=58, f_hi=62)
    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    p.connect(notch50, notch60)

    # --- Selection du canal moteur C3 ---
    select_c3 = gp.Router(input_channels=gp.Router.ALL,
                          output_channels={"c3": [MOTOR_CHANNEL]})
    p.connect(notch60, select_c3)

    # --- Puissance ALPHA (8-12 Hz) : bande -> carre -> moyenne glissante 1 s ---
    alpha_band = gp.Bandpass(f_lo=8, f_hi=12)
    alpha_pow = gp.Equation("in**2")
    alpha_avg = gp.MovingAverage(window_size=250)
    p.connect(select_c3["c3"], alpha_band)
    p.connect(alpha_band, alpha_pow)
    p.connect(alpha_pow, alpha_avg)

    # --- Puissance BETA (13-30 Hz) ---
    beta_band = gp.Bandpass(f_lo=13, f_hi=30)
    beta_pow = gp.Equation("in**2")
    beta_avg = gp.MovingAverage(window_size=250)
    p.connect(select_c3["c3"], beta_band)
    p.connect(beta_band, beta_pow)
    p.connect(beta_pow, beta_avg)

    return alpha_avg, beta_avg


def build_calib_recorder(p, source):
    """Pipeline de calibration : sort les puissances BRUTES [alpha, beta] pour CSV."""
    alpha_avg, beta_avg = build_features(p, source)
    merger = gp.Router(input_channels={"alpha": [0], "beta": [0]},
                       output_channels=[gp.Router.ALL])
    p.connect(alpha_avg, merger["alpha"])
    p.connect(beta_avg, merger["beta"])
    return merger


def build_bci(p, source):
    """Chaine BCI complete -> merger [alpha%, beta%, commande, etat].

    L'etat utilise la calibration LDA si config/calibration.json existe,
    sinon un seuil generique (sign de la commande).
    """
    alpha_avg, beta_avg = build_features(p, source)

    # --- Puissances NORMALISEES [0,1] et COMMANDE [-1,1] (pour l'affichage) ---
    rel_alpha = gp.Equation("a / (a + b + 1)")
    rel_beta = gp.Equation("b / (a + b + 1)")
    command = gp.Equation("(b - a) / (a + b + 1)")
    for node in (rel_alpha, rel_beta, command):
        p.connect(alpha_avg, node["a"])
        p.connect(beta_avg, node["b"])

    # --- Etat BINAIRE : +1 = FERME, -1 = OUVERT ---
    calib = load_calibration()
    if calib is not None:
        wa, wb, bias = calib
        print(f"Calibration LDA chargee : etat = sign({wa:.4g}*alpha + {wb:.4g}*beta + {bias:.4g})")
        etat = gp.Equation(f"sign(({wa!r})*a + ({wb!r})*b + ({bias!r}))")
        p.connect(alpha_avg, etat["a"])
        p.connect(beta_avg, etat["b"])
    else:
        print("Pas de calibration (config/calibration.json absent) : etat = sign(commande).")
        etat = gp.Equation("sign(c)")
        p.connect(command, etat["c"])

    # --- Fusion pour l'affichage : alpha%, beta%, commande, etat ---
    merger = gp.Router(
        input_channels={"alpha": [0], "beta": [0], "commande": [0], "etat": [0]},
        output_channels=[gp.Router.ALL],
    )
    p.connect(rel_alpha, merger["alpha"])
    p.connect(rel_beta, merger["beta"])
    p.connect(command, merger["commande"])
    p.connect(etat, merger["etat"])
    return merger


#: Sentinel pour distinguer "mode sim" de "mode casque auto-detect" (None).
SIM_MODE = "__sim__"


def _run_pipeline_with_retry(build_fn, serial, run_label):
    """Construit et demarre un pipeline en essayant chaque casque candidat.

    serial peut etre :
      - SIM_MODE   : mode simulation, un seul essai direct (pas de Bluetooth).
      - None       : mode casque, auto-detection (scan Bluetooth des devices).
      - "UN-xxxx"  : mode casque, serial force, un seul essai direct.

    Si start() echoue avec une erreur de connexion, on nettoie et on
    reessaie le serial suivant. Renvoie le Pipeline demarre via build_fn,
    ou None si aucun casque n'a repondu.
    """
    if serial is SIM_MODE:
        candidates = [SIM_MODE]
    elif serial is None:
        candidates = list_serials(None)
        if not candidates:
            print("  Aucun casque Unicorn detecte. Lance avec --sim pour tester sans casque.")
            return None
    else:
        candidates = [serial]

    last_exc = None
    for sn in candidates:
        if sn is not SIM_MODE:
            print(f"  Tentative de connexion au casque {sn} ...")
        try:
            return build_fn(sn)
        except Exception as e:
            last_exc = e
            if _is_connect_error(e):
                print(f"  {sn} ne repond pas, essai suivant...")
                continue
            raise
    print("  Aucun casque n'a repondu apres avoir essaye tous les serials.")
    if last_exc:
        raise last_exc
    return None


def run_scope(mode: str, serial):
    app = gp.MainApp()

    def build_and_start(sn):
        p = gp.Pipeline()
        # En mode sim, sn == SIM_MODE -> make_source utilise Generator.
        source = make_source(mode, sn if sn is not SIM_MODE else None)
        merger = build_bci(p, source)
        scope = gp.TimeSeriesScope(amplitude_limit=1.5, time_window=10)
        p.connect(merger, scope)
        app.add_widget(scope)
        print("Fenetre temps reel : alpha%, beta%, commande, et ETAT.")
        print("  ETAT (courbe binaire) : +1 = FERME, -1 = OUVERT (2 fonctions seulement).")
        print("(ferme la fenetre pour arreter)")
        p.start()
        return p

    arg = SIM_MODE if mode == "sim" else serial
    p = _run_pipeline_with_retry(build_and_start, arg, "scope")
    if p is None:
        return
    app.run()
    p.stop()
    print("Pipeline arrete.")


def run_record(mode, serial, seconds, out_csv):
    def build_and_start(sn):
        p = gp.Pipeline()
        source = make_source(mode, sn if sn is not SIM_MODE else None)
        merger = build_bci(p, source)
        sink = gp.CsvWriter(file_name=out_csv)
        p.connect(merger, sink)
        p.start()
        print(f"Enregistrement (C3, alpha, beta, commande) pendant {seconds:.0f} s...")
        return p

    arg = SIM_MODE if mode == "sim" else serial
    p = _run_pipeline_with_retry(build_and_start, arg, "record")
    if p is None:
        return
    time.sleep(seconds)
    p.stop()
    print(f"[OK] Donnees ecrites (fichier horodate a cote de {out_csv}).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline BCI g.Pype Inclusive Maker")
    parser.add_argument("--sim", action="store_true", help="Signal simule")
    parser.add_argument("--record", action="store_true",
                        help="Enregistrer en CSV au lieu d'afficher")
    parser.add_argument("--serial", default=DEFAULT_SERIAL,
                        help=f"Numero de serie du casque (defaut {DEFAULT_SERIAL})")
    parser.add_argument("--seconds", type=float, default=10.0,
                        help="Duree en mode --record")
    args = parser.parse_args()

    mode = "sim" if args.sim else "casque"
    print("=" * 60)
    print(f"  Pipeline BCI g.Pype - {'ENREGISTREMENT' if args.record else 'AFFICHAGE'}"
          f" - source {mode.upper()}")
    print("=" * 60)

    try:
        if args.record:
            out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
            os.makedirs(out_dir, exist_ok=True)
            out_csv = os.path.abspath(os.path.join(out_dir, "gpype_bci.csv"))
            run_record(mode, args.serial, args.seconds, out_csv)
        else:
            run_scope(mode, args.serial)
        return 0
    except Exception as e:
        import traceback
        msg = str(e)
        print(f"\n[ERREUR] {type(e).__name__}: {msg}")
        print("----- trace complete -----")
        traceback.print_exc()
        print("--------------------------")
        if "couldn't connect" in msg.lower() or "device" in msg.lower():
            print("\n=> Casque injoignable : allume-le, FERME Unicorn Suite/LSL/Recorder,")
            print("   et si besoin fais un cycle Bluetooth (OFF/ON) ou rallume le casque.")
        return 1


if __name__ == "__main__":
    return_code = main()
    if return_code:
        print(f"\n(Termine avec le code {return_code}. Voir la trace ci-dessus.)")
