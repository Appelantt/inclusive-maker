"""Fonctions utilitaires."""

import yaml
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    """Charge un fichier YAML de configuration."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(path: str | Path, data: dict[str, Any]) -> None:
    """Sauvegarde un dictionnaire dans un fichier YAML."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
