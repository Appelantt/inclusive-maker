#!/usr/bin/env python3
"""Entraine et compare plusieurs classifieurs OPEN/CLOSE/IDLE.

Usage:
    set PYTHONPATH=src
    python scripts\train_model.py [--model logistic_regression|random_forest|gradient_boosting]

Le meilleur modele est sauvegarde dans :
    src/inclusive_maker/brain_algo/models/eeg_state_classifier.pkl
"""

import argparse

from inclusive_maker.brain_algo.classifier import (
    EEGStateClassifier,
    generate_training_data,
)


def main():
    parser = argparse.ArgumentParser(description="Entrainement classifieur EEG")
    parser.add_argument(
        "--model",
        type=str,
        default="logistic_regression",
        choices=list(EEGStateClassifier.AVAILABLE_MODELS),
        help="Modele scikit-learn a entrainer",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.15,
        help="Facteur de bruit realiste (0.0 = signaux parfaits)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=300,
        help="Echantillons par classe",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" Inclusive Maker - Entrainement du classifieur EEG")
    print("=" * 60)

    print(f"\nGeneration du dataset synthetique (bruit={args.noise})...")
    X, y = generate_training_data(
        n_samples_per_class=args.samples,
        window_duration=1.0,
        noise_factor=args.noise,
        seed=42,
    )
    print(f"Dataset : {len(y)} echantillons ({len(set(y))} classes)")

    classifier = EEGStateClassifier()
    print(f"Entrainement du modele {args.model}...")
    classifier.fit(X, y, model_name=args.model)

    metrics = classifier.metrics
    print(f"\n--- Metriques ---")
    print(f"Modele            : {metrics['model_name']}")
    print(f"CV accuracy       : {metrics['cv_accuracy_mean']:.3f} (+/- {metrics['cv_accuracy_std']:.3f})")
    print(f"Train accuracy    : {metrics['train_accuracy']:.3f}")
    print(f"Confusion matrix  : {metrics['confusion_matrix']}")

    classifier.save()
    print(f"\nModele sauvegarde : {classifier.model_path}")


if __name__ == "__main__":
    main()
