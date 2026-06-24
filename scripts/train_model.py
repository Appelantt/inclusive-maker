"""Script d'entraînement du classifieur (placeholder pour la phase 2)."""

from pathlib import Path


def main() -> None:
    print("Entraînement du modèle de commande cérébrale.")
    print("TODO:")
    print("  1. Charger les données EEG annotées depuis data/processed/")
    print("  2. Extraire les features")
    print("  3. Entraîner un classifieur scikit-learn")
    print("  4. Sauvegarder le modèle dans src/inclusive_maker/brain_algo/models/")

    model_dir = Path("src/inclusive_maker/brain_algo/models")
    model_dir.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
