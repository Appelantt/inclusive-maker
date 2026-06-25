#!/usr/bin/env python3
"""Entraîne un classifieur OPEN/CLOSE/IDLE sur des signaux EEG synthétiques.

Usage:
    set PYTHONPATH=src
    python scripts\train_model.py

Le modèle est sauvegardé dans :
    src/inclusive_maker/brain_algo/models/eeg_state_classifier.pkl
"""

from inclusive_maker.brain_algo.classifier import (
    EEGStateClassifier,
    generate_training_data,
)


def main() -> None:
    print("=" * 60)
    print(" Inclusive Maker - Entraînement du classifieur EEG")
    print("=" * 60)

    print("\nGénération du dataset synthétique...")
    X, y = generate_training_data(n_samples_per_class=500, window_duration=1.0)
    print(f"Dataset : {len(y)} échantillons ({len(set(y))} classes)")

    classifier = EEGStateClassifier()
    print("Entraînement du modèle LogisticRegression...")
    classifier.fit(X, y)

    # Score sur le dataset d'entraînement (synthétique, donc très bon)
    score = classifier.model.score(X, y)
    print(f"Accuracy (train) : {score:.3f}")

    classifier.save()
    print(f"\nModèle sauvegardé : {classifier.model_path}")
    print("Tu peux maintenant lancer run_app.py ou demo_full_pipeline.py")


if __name__ == "__main__":
    main()
