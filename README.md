# inclusive Maker

Projet étudiant de commande cérébrale à distance.

## 🎯 Objectif

Développer une preuve de concept de **Brain-Computer Interface (BCI)** permettant de commander à distance un actionneur de main simplifié à partir des signaux EEG du casque **Unicorn Hybrid Black**.

> ⚠️ Ce projet est un **démonstrateur pédagogique**. Il ne constitue pas un dispositif médical et ne prétend pas soigner la paralysie. Pour toute application clinique réelle, un encadrement médical et des dispositifs certifiés sont indispensables.

## 🧠 Cas d’usage

1. Acquisition EEG en temps réel via le casque Unicorn.
2. Filtrage et extraction de features cérébrales simples.
3. Détection de 3 états mentaux : **OPEN**, **CLOSE**, **IDLE**.
4. Envoi d’une commande à distance (UDP / WebSocket / LSL).
5. Réception par un client qui pilote un servomoteur, une orthèse didactique ou une interface de démonstration.

## 👥 Équipe

- Membre 1 : Acquisition & signal
- Membre 2 : Algorithme de commande cérébrale
- Membre 3 : Commande à distance & démonstrateur

## 🛠️ Stack technique

- **Python 3.10+**
- **g.Pype** (SDK g.tec pour acquisition et traitement EEG)
- **pylsl** pour le streaming LSL
- **numpy**, **scipy**, **scikit-learn** pour le signal et le ML
- **pyyaml** pour la configuration
- Matériel : **Unicorn Hybrid Black** (8 canaux, 250 Hz)

## 📁 Structure du projet

```
inclusive-maker/
├── README.md
├── docs/               # Documentation et architecture
├── config/             # Fichiers de configuration
├── src/                # Code source Python
│   └── inclusive_maker/
│       ├── acquisition/
│       ├── signal_processing/
│       ├── brain_algo/
│       ├── remote_command/
│       └── shared/
├── scripts/            # Scripts exécutables
├── notebooks/          # Exploration & prototypage
├── tests/              # Tests automatiques
├── frontend/           # Interface utilisateur (optionnel)
└── hardware/           # Code embarqué (Arduino/Raspberry)
```

## 🚀 Démarrage rapide

Pour les collaborateurs, voir le [guide complet](docs/collaborators.md).

### Installation automatique (macOS / Linux)

```bash
git clone https://github.com/Appelantt/inclusive-maker.git
cd inclusive-maker
bash scripts/install.sh
```

### Vérifier l'environnement

```bash
PYTHONPATH=src python scripts/check_env.py
```

### Lancer la démo sans matériel

```bash
# Terminal 1 : serveur de commandes
PYTHONPATH=src python scripts/run_server.py

# Terminal 2 : générateur de commandes cérébrales
PYTHONPATH=src python scripts/demo_alpha_command.py
```

## 📚 Documentation

- [Guide des collaborateurs](docs/collaborators.md)
- [Architecture du système](docs/architecture.md)
- [Guide d’installation matériel](docs/setup.md)
- [Journal de bord](docs/journal.md)

## 📜 Licence

MIT Licence - Projet académique.
