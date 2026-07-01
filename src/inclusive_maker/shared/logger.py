"""Logger centralise avec sortie console ET fichier.

Tous les logs du package ``inclusive_maker`` sont ecrits a la fois sur la
console (stdout) et dans ``logs/inclusive_maker.log`` a la racine du projet.
Cela permet a un terminal dedie (``scripts/log_viewer.py``) d afficher les
logs en temps reel, meme quand l application graphique tourne.
"""

import logging
import sys
from pathlib import Path

# Racine du projet : src/inclusive_maker/shared/logger.py -> parents[3]
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "inclusive_maker.log"

_LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def get_log_file_path() -> Path:
    """Retourne le chemin absolu du fichier de log."""
    return _LOG_FILE


def _ensure_root_handlers() -> None:
    """Installe les handlers (console + fichier) sur le logger racine.

    Ne fait rien si les handlers sont deja en place, ce qui evite les doublons
    quand plusieurs modules appellent ``get_logger``.
    """
    root = logging.getLogger("inclusive_maker")
    if root.handlers:
        return

    root.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # 1. Sortie console (stdout)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # 2. Sortie fichier (append, UTF-8) pour le visualiseur temps reel
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception:
        # On ne plante jamais l app a cause du fichier de log
        pass


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Cree un logger avec format simple, sortie console et fichier."""
    _ensure_root_handlers()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
