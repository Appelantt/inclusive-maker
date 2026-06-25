"""Classifieur ML robuste pour la commande cerebrale.

Entraine plusieurs modeles scikit-learn sur des signaux EEG synthetiques bruites.
Sauvegarde le meilleur modele, les metriques et une matrice de confusion.
"""

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "eeg_state_classifier.pkl"


def add_realistic_noise(data: np.ndarray, noise_factor: float = 0.15, seed: Optional[int] = None):
    """Ajoute du bruit blanc, des artefacts 50 Hz et des artefacts de mouvement."""
    rng = np.random.default_rng(seed)
    n_samples, n_channels = data.shape
    t = np.arange(n_samples) / EEG_SAMPLING_RATE
    noise = rng.normal(0, noise_factor, data.shape)
    mains_hum = 0.3 * noise_factor * np.sin(2 * np.pi * 50.0 * t).reshape(-1, 1)
    movement = np.zeros_like(data)
    if rng.random() < 0.2:
        start = rng.integers(0, max(1, n_samples - 20))
        length = rng.integers(10, 30)
        movement[start:start+length, :] = rng.normal(0, 5 * noise_factor, (min(length, n_samples-start), n_channels))
    return data + noise + mains_hum + movement


def extract_features(data: np.ndarray):
    """Extrait un vecteur de features d'une fenetre EEG."""
    powers = compute_all_bandpowers(data, EEG_SAMPLING_RATE, BANDS)
    alpha = max(powers["alpha"], 1e-9)
    beta = max(powers["beta"], 1e-9)
    return np.array([np.log(alpha), np.log(beta), alpha / beta, beta / alpha, powers.get("theta", 0.0)])


def generate_training_data(
    n_samples_per_class: int = 300,
    window_duration: float = 1.0,
    noise_factor: float = 0.15,
    seed: int = 42,
):
    """Genere un dataset synthetique avec bruit realiste."""
    rng = np.random.default_rng(seed)
    X, y = [], []
    states = ["OPEN", "CLOSE", "IDLE"]
    for state in states:
        generator = EEGGenerator(state, seed=int(rng.integers(0, 1_000_000)))
        for _ in range(n_samples_per_class):
            data = generator.read_window(window_duration)
            data = add_realistic_noise(data, noise_factor=noise_factor, seed=int(rng.integers(0, 1_000_000)))
            X.append(extract_features(data))
            y.append(state)
    return np.array(X), np.array(y)


class EEGStateClassifier:
    AVAILABLE_MODELS = {
        "logistic_regression": LogisticRegression(max_iter=2000, C=1.0),
        "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "gradient_boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
    }

    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.model = None
        self.model_name = ""
        self.classes_ = []
        self.metrics = {}
        if str(model_path) != "__none__":
            self._load()

    def _load(self):
        if self.model_path.exists():
            with open(self.model_path, "rb") as f:
                payload = pickle.load(f)
            self.model = payload["model"]
            self.model_name = payload.get("model_name", "unknown")
            self.classes_ = list(payload["classes"])
            self.metrics = payload.get("metrics", {})

    def is_trained(self):
        return self.model is not None

    def fit(self, X, y, model_name="logistic_regression"):
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Modele inconnu : {model_name}. Choix : {list(self.AVAILABLE_MODELS)}")
        self.model = self.AVAILABLE_MODELS[model_name]
        self.model_name = model_name
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self.model, X, y, cv=cv)
        self.model.fit(X, y)
        self.classes_ = list(self.model.classes_)
        y_pred = self.model.predict(X)
        self.metrics = {
            "model_name": model_name,
            "cv_accuracy_mean": float(np.mean(cv_scores)),
            "cv_accuracy_std": float(np.std(cv_scores)),
            "train_accuracy": float(accuracy_score(y, y_pred)),
            "classification_report": classification_report(y, y_pred, output_dict=True),
            "confusion_matrix": confusion_matrix(y, y_pred, labels=self.classes_).tolist(),
        }
        return self

    def save(self):
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "model_name": self.model_name,
                "classes": self.classes_,
                "metrics": self.metrics,
            }, f)

    def predict(self, features):
        if not self.is_trained():
            raise RuntimeError("Le modele n'est pas entraine.")
        alpha = max(features.get("alpha", 0.0), 1e-9)
        beta = max(features.get("beta", 0.0), 1e-9)
        theta = features.get("theta", 0.0)
        x = np.array([[np.log(alpha), np.log(beta), alpha / beta, beta / alpha, theta]])
        return self.model.predict(x)[0]
