"""Classifieur ML pour la commande cérébrale.

Entraîne un modèle scikit-learn sur des signaux EEG synthétiques générés
par EEGGenerator.  Le modèle extrait les puissances alpha/bêta et apprend
à classifier OPEN / CLOSE / IDLE.
"""

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "eeg_state_classifier.pkl"


def extract_features(data: np.ndarray) -> np.ndarray:
    """Extrait un vecteur de features d'une fenêtre EEG.

    Retourne [log(alpha), log(beta), alpha/beta, beta/alpha].
    """
    powers = compute_all_bandpowers(data, EEG_SAMPLING_RATE, BANDS)
    alpha = max(powers["alpha"], 1e-9)
    beta = max(powers["beta"], 1e-9)
    return np.array([
        np.log(alpha),
        np.log(beta),
        alpha / beta,
        beta / alpha,
    ])


def generate_training_data(
    n_samples_per_class: int = 200,
    window_duration: float = 1.0,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Génère un dataset synthétique avec EEGGenerator.

    Returns:
        X: array (n_samples, n_features)
        y: array (n_samples,) labels
    """
    rng = np.random.default_rng(seed)
    X, y = [], []
    states = ["OPEN", "CLOSE", "IDLE"]

    for state in states:
        generator = EEGGenerator(state, seed=int(rng.integers(0, 1_000_000)))
        for _ in range(n_samples_per_class):
            data = generator.read_window(window_duration)
            X.append(extract_features(data))
            y.append(state)

    return np.array(X), np.array(y)


class EEGStateClassifier:
    """Classifieur OPEN/CLOSE/IDLE basé sur scikit-learn."""

    def __init__(self, model_path: Optional[Path | str] = None):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.model: Optional[LogisticRegression] = None
        self.classes_: list[str] = []
        if str(model_path) != "__none__":
            self._load()

    def _load(self) -> None:
        """Charge le modèle depuis le disque s'il existe."""
        if self.model_path.exists():
            with open(self.model_path, "rb") as f:
                payload = pickle.load(f)
            self.model = payload["model"]
            self.classes_ = list(payload["classes"])

    def is_trained(self) -> bool:
        return self.model is not None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "EEGStateClassifier":
        """Entraîne le modèle."""
        self.model = LogisticRegression(max_iter=1000)
        self.model.fit(X, y)
        self.classes_ = list(self.model.classes_)
        return self

    def save(self) -> None:
        """Sauvegarde le modèle sur le disque."""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({"model": self.model, "classes": self.classes_}, f)

    def predict(self, features: dict[str, float]) -> str:
        """Prédit l'état mental à partir des bandpowers brutes."""
        if not self.is_trained():
            raise RuntimeError("Le modèle n'est pas entraîné.")
        alpha = max(features.get("alpha", 0.0), 1e-9)
        beta = max(features.get("beta", 0.0), 1e-9)
        x = np.array([[np.log(alpha), np.log(beta), alpha / beta, beta / alpha]])
        return self.model.predict(x)[0]
