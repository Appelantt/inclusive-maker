from setuptools import setup, find_packages

setup(
    name="inclousive-maker",
    version="0.1.0",
    description="Projet étudiant de commande cérébrale à distance",
    author="Inclousive Maker Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "gpype>=3.0.9",
        "pylsl>=1.16.0",
        "numpy>=1.24.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "viz": ["matplotlib>=3.7.0", "pyqtgraph>=0.13.0", "PySide6>=6.5.0"],
        "dev": ["pytest>=7.4.0"],
    },
)
