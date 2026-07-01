#!/usr/bin/env python3
r"""Visualiseur de logs en temps reel pour Inclusive Maker.

Affiche en continu le contenu du fichier logs/inclusive_maker.log dans un
terminal dedie, avec coloration par niveau (INFO / WARNING / ERROR).

Usage:
    set PYTHONPATH=src
    python scripts/log_viewer.py

Le script attend que le fichier de log existe s il n est pas encore cree,
puis suit les nouvelles lignes au fur et a mesure (facon tail -f).
Appuyez sur Ctrl+C pour quitter.
"""

import os
import sys
import time
from pathlib import Path

# Forcer stdout en UTF-8 pour supporter les accents et symboles sous Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Activer le support des codes ANSI dans le terminal Windows 10+
if sys.platform == "win32":
    os.system("")

# Racine du projet : scripts/log_viewer.py -> parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = PROJECT_ROOT / "logs" / "inclusive_maker.log"


# Codes couleurs ANSI
class c:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    BG_CYAN = "\033[46m"


LEVEL_COLORS = {
    "DEBUG": c.GRAY,
    "INFO": c.CYAN,
    "WARNING": c.YELLOW,
    "ERROR": c.RED,
    "CRITICAL": c.RED,
}


def colorize_line(line: str) -> str:
    """Colore une ligne de log selon son niveau."""
    line = line.rstrip("\n\r")
    # Lignes speciales (bannieres)
    if line.startswith("===") or "Inclusive Maker" in line[:40]:
        return f"{c.BOLD}{c.GREEN}{line}{c.RESET}"

    for level, color in LEVEL_COLORS.items():
        if f"| {level} |" in line:
            if level in ("ERROR", "CRITICAL"):
                return f"{c.RED}{c.BOLD}{line}{c.RESET}"
            if level == "WARNING":
                return f"{c.YELLOW}{line}{c.RESET}"
            return f"{color}{line}{c.RESET}"
    return line


def print_banner() -> None:
    """Affiche la banniere du visualiseur."""
    bar = "=" * 62
    print(f"{c.BG_CYAN}{c.BOLD}  Inclusive Maker - Logs en temps reel  {c.RESET}")
    print(bar)
    print(f"  Fichier : {LOG_FILE}")
    print(bar)
    print()


def wait_for_file() -> None:
    """Attend que le fichier de log existe."""
    if LOG_FILE.exists():
        return
    print(f"{c.YELLOW}[EN ATTENTE] Fichier de log pas encore cree...{c.RESET}")
    print(f"    ({LOG_FILE})")
    print()
    while not LOG_FILE.exists():
        time.sleep(0.5)
    print(f"{c.GREEN}[OK] Fichier de log cree ! Demarrage du suivi.{c.RESET}")
    print()


def tail_forever() -> None:
    """Suit le fichier de log en temps reel (tail -f)."""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        # Se positionner pres de la fin pour afficher un peu d historique
        f.seek(0, os.SEEK_END)
        size = f.tell()
        start = max(0, size - 8000)
        f.seek(start)
        # Sauter la premiere ligne (potentiellement partielle)
        if start > 0:
            f.readline()

        print(f"{c.DIM}--- Historique recent ---{c.RESET}")
        while True:
            line = f.readline()
            if line:
                sys.stdout.write(colorize_line(line) + "\n")
                sys.stdout.flush()
            else:
                # Pas de nouvelle ligne : on attend un peu
                time.sleep(0.2)


def main() -> None:
    print_banner()
    try:
        wait_for_file()
        print(f"{c.GREEN}[OK] Suivi en temps reel actif - Ctrl+C pour quitter.{c.RESET}")
        print()
        tail_forever()
    except KeyboardInterrupt:
        print(f"\n{c.YELLOW}Visualiseur de logs arrete.{c.RESET}")


if __name__ == "__main__":
    main()
