"""Vérifie que l'environnement est correctement installé."""

import sys


def check():
    print("=== Verification de l'environnement Inclusive Maker ===")

    checks = {
        "python_version": sys.version_info >= (3, 10),
        "numpy": False,
        "scipy": False,
        "scikit_learn": False,
        "pyyaml": False,
    }

    try:
        import numpy
        checks["numpy"] = True
        print(f"  numpy: {numpy.__version__}")
    except ImportError:
        print("  numpy: MANQUANT")

    try:
        import scipy
        checks["scipy"] = True
        print(f"  scipy: {scipy.__version__}")
    except ImportError:
        print("  scipy: MANQUANT")

    try:
        import sklearn
        checks["scikit_learn"] = True
        print(f"  scikit-learn: {sklearn.__version__}")
    except ImportError:
        print("  scikit-learn: MANQUANT")

    try:
        import yaml
        checks["pyyaml"] = True
        print("  pyyaml: OK")
    except ImportError:
        print("  pyyaml: MANQUANT")

    try:
        import inclusive_maker
        print(f"  inclusive_maker: OK (version {inclusive_maker.__version__})")
    except ImportError:
        print("  inclusive_maker: MANQUANT (utilise PYTHONPATH=src)")

    try:
        import gpype
        print(f"  gpype: OK (version {gpype.__version__})")
    except ImportError:
        print("  gpype: MANQUANT (optionnel, installez requirements-hardware.txt pour le casque Unicorn)")

    try:
        import PySide6
        print(f"  PySide6: OK")
    except ImportError:
        print("  PySide6: MANQUANT (optionnel, installez requirements-ui.txt ou utilisez l'interface Tkinter)")

    all_ok = all(checks.values()) and sys.version_info >= (3, 10)
    print("=" * 52)
    if all_ok:
        print("✅ Environnement pret")
    else:
        print("⚠️  Environnement incomplet - installe les dependances manquantes")
        sys.exit(1)


if __name__ == "__main__":
    check()
