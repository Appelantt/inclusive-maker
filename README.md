# Inclusive Maker

Projet étudiant de **commande cérébrale à distance**.

## 🎯 Objectif

Développer une preuve de concept de **Brain-Computer Interface (BCI)** permettant de commander à distance un actionneur de main simplifié à partir des signaux EEG du casque **Unicorn Hybrid Black**.

> ⚠️ Ce projet est un **démonstrateur pédagogique**. Il ne constitue pas un dispositif médical et ne prétend pas soigner la paralysie. Pour toute application clinique réelle, un encadrement médical et des dispositifs certifiés sont indispensables.

## 🧠 Cas d’usage

1. **Acquisition EEG** en temps réel via le casque Unicorn.
2. **Filtrage** et extraction de features cérébrales simples.
3. **Détection** de 3 états mentaux : **OPEN**, **CLOSE**, **IDLE**.
4. **Envoi d’une commande** à distance (UDP / WebSocket / LSL).
5. **Réception** par un client qui pilote un servomoteur, une orthèse didactique ou une interface de démonstration.

## 👥 Équipe

- **Membre 1** : Acquisition EEG & traitement du signal
- **Membre 2** : Algorithme de commande cérébrale
- **Membre 3** : Commande à distance & démonstrateur hardware/interface

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
├── README.md                 # Ce fichier
├── requirements.txt          # Dépendances Python
├── setup.py / pyproject.toml # Configuration du package
├── scripts/                  # Scripts exécutables
│   ├── install.sh            # Installation automatique macOS/Linux
│   ├── install.bat           # Installation automatique Windows
│   ├── check_env.py          # Vérification de l'environnement
│   ├── demo_alpha_command.py # Démo sans matériel
│   ├── run_server.py         # Serveur UDP de commandes
│   ├── record_eeg.py         # Enregistrement EEG
│   └── train_model.py        # Entraînement du classifieur
├── src/inclusive_maker/      # Code source Python
│   ├── acquisition/          # Connexion au casque / générateur
│   ├── signal_processing/    # Filtres et features EEG
│   ├── brain_algo/           # Détection d'état mental
│   ├── remote_command/       # Envoi/réception UDP
│   └── shared/               # Utilitaires
├── tests/                    # Tests automatiques
├── config/                   # Fichiers YAML de configuration
├── docs/                     # Documentation
├── notebooks/                # Exploration et prototypage
├── frontend/                 # Interface utilisateur (optionnel)
└── hardware/                 # Code embarqué (Arduino/Raspberry)
```

## 🚀 Démarrage rapide

Choisis ton système d'exploitation :

### macOS / Linux

```bash
# 1. Cloner le repo
git clone https://github.com/Appelantt/inclusive-maker.git
cd inclusive-maker

# 2. Installation automatique
bash scripts/install.sh

# 3. Vérifier l'environnement
PYTHONPATH=src python scripts/check_env.py

# 4. Lancer les tests
PYTHONPATH=src pytest tests/ -v
```

### Windows

```cmd
:: 1. Cloner le repo
git clone https://github.com/Appelantt/inclusive-maker.git
cd inclusive-maker

:: 2. Installation automatique
scripts\install.bat

:: 3. Vérifier l'environnement
set PYTHONPATH=src
python scripts\check_env.py

:: 4. Lancer les tests
pytest tests\ -v
```

### Installation manuelle (si le script automatique ne marche pas)

```bash
# 1. Cloner
git clone https://github.com/Appelantt/inclusive-maker.git
cd inclusive-maker

# 2. Environnement virtuel
python3 -m venv venv          # macOS/Linux
python -m venv venv           # Windows

# 3. Activer l'environnement
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows

# 4. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# 5. Lancer les tests
pytest tests/ -v              # macOS/Linux
pytest tests\ -v              # Windows
```

## 🎮 Tester sans matériel

### Option 1 : interface graphique (recommandée)

Lance l'application de tutoriel. Si **PySide6** est installé, elle s'ouvre avec une interface moderne. Sinon, elle bascule automatiquement sur **Tkinter** (natif Python).

```bash
# macOS / Linux
PYTHONPATH=src python run_app.py

# Windows
set PYTHONPATH=src
python run_app.py
```

L'interface comporte 4 étapes linéaires :
1. **Accueil** — présentation du système
2. **Calibration** — associer ses états mentaux aux commandes
3. **Entraînement** — s'exercer sur OPEN / CLOSE / IDLE
4. **Contrôle** — envoi en temps réel des commandes au gant simulé

### Option 2 : assistant en ligne de commande

```bash
# macOS / Linux
PYTHONPATH=src python scripts/calibration_assistant.py

# Windows
set PYTHONPATH=src
python scripts\calibration_assistant.py
```

### Option 3 : démo automatique du pipeline complet

```bash
# macOS / Linux
PYTHONPATH=src python scripts/demo_full_pipeline.py --duration 30

# Windows
set PYTHONPATH=src
python scripts\demo_full_pipeline.py --duration 30
```

### Option 4 : serveur UDP + générateur de commandes

**Terminal 1 - Serveur UDP** (reçoit les commandes) :

```bash
# macOS / Linux
PYTHONPATH=src python scripts/run_server.py

# Windows
set PYTHONPATH=src
python scripts\run_server.py
```

**Terminal 2 - Mock gant** (affichage visuel) :

```bash
# macOS / Linux
PYTHONPATH=src python hardware/mock_hand_server.py

# Windows
set PYTHONPATH=src
python hardware\mock_hand_server.py
```

**Terminal 3 - Générateur de commandes cérébrales** :

```bash
# macOS / Linux
PYTHONPATH=src python scripts/demo_alpha_command.py

# Windows
set PYTHONPATH=src
python scripts\demo_alpha_command.py
```

## 🔌 Utilisation avec le casque Unicorn Hybrid Black

L'acquisition directe du casque Unicorn via g.Pype nécessite :

- **Windows 10/11**
- **Unicorn Suite Hybrid Black** installé
- Le casque appairé en Bluetooth
- La librairie `UnicornPy` accessible (installée avec Unicorn Suite)

### Étapes

1. Allumer le casque et l'appairer en Bluetooth.
2. Vérifier que Unicorn Suite est installé dans `Documents\gtec\Unicorn Suite\Hybrid Black`.
3. Dans `config/default.yaml`, mettre :
   ```yaml
   eeg:
     device: "unicorn_hybrid_black"
     use_generator: false
   ```
4. Lancer l'enregistrement :
   ```bash
   PYTHONPATH=src python scripts/record_eeg.py
   ```

> 💡 Sous macOS ou Linux, tu peux quand même développer grâce au **mode démonstration** (`use_generator: true`) ou en recevant un flux LSL/UDP depuis une autre machine Windows.

## 🧪 Tests

Les tests peuvent être lancés sur n'importe quel OS sans matériel :

```bash
# macOS / Linux
PYTHONPATH=src pytest tests/ -v

# Windows
set PYTHONPATH=src
pytest tests\ -v
```

Résultat attendu : **11 passed**..

## 📚 Documentation

- [Guide des collaborateurs](docs/collaborators.md) — installation pas à pas pour le groupe
- [Contexte du projet Inclusiv'Maker](docs/project_context.md) — défi, équipe, planning
- [Guide d'interview](docs/interview_guide.md) — préparation de l'entretien avec Philippe
- [Architecture du système](docs/architecture.md) — schéma et flux de données
- [Cahier des charges](docs/requirements_spec.md) — objectifs et scénarios
- [Template Hackster.io](docs/hackster_template.md) — canevas de documentation finale
- [Guide d’installation matériel](docs/setup.md) — détails Unicorn et dépannage
- [Journal de bord](docs/journal.md) — suivi des phases du projet
- [Documentation externe et ressources](docs/external_resources.md) — liens officiels Unicorn, g.Pype, LSL, UDP, tutoriels

## 🤝 Contribuer

1. Tirer la dernière version avant de travailler :
   ```bash
   git pull origin main
   ```
2. Créer une branche pour ta fonctionnalité :
   ```bash
   git checkout -b ma-fonctionnalite
   ```
3. Faire tes modifications, puis commit et push :
   ```bash
   git add .
   git commit -m "feat: description de ma modification"
   git push origin ma-fonctionnalite
   ```
4. Ouvrir une **Pull Request** sur GitHub.

## 📜 Licence

MIT Licence — Projet académique.
