# Guide des collaborateurs

Ce guide explique comment installer le projet sur n'importe quel PC (macOS, Windows, Linux) pour commencer à travailler.

## Prérequis

- **Git** installé
- **Python 3.10 ou plus** installé
- Un éditeur de code (VS Code recommandé)

## 1. Cloner le repo

```bash
git clone https://github.com/Appelantt/inclusive-maker.git
cd inclusive-maker
```

## 2. Créer un environnement virtuel

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

## 3. Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Note : `gpype` est sous licence non commerciale (GNCL). Pour l'acquisition réelle du casque Unicorn, il faut Windows + Unicorn Suite installé. Sans cela, le projet fonctionne en mode **démonstration synthétique**.

## 4. Vérifier que tout fonctionne

```bash
PYTHONPATH=src pytest tests/ -v
```

Tu dois voir **8 passed**.

## 5. Lancer la démo

Cette démo fonctionne sans casque. Elle génère des signaux synthétiques et envoie des commandes UDP.

**Terminal 1 - serveur de commandes :**
```bash
PYTHONPATH=src python scripts/run_server.py
```

**Terminal 2 - générateur de commandes cérébrales :**
```bash
PYTHONPATH=src python scripts/demo_alpha_command.py
```

Tu dois voir dans le terminal 1 les commandes `OPEN`, `CLOSE`, `IDLE` arriver.

## 6. Structure des responsabilités

| Membre | Module principal | Fichiers clés |
|---|---|---|
| Acquisition & Signal | `src/inclusive_maker/acquisition/`, `src/inclusive_maker/signal_processing/` | `unicorn_connector.py`, `features.py` |
| Algo BCI | `src/inclusive_maker/brain_algo/` | `mental_state_detector.py`, `classifier.py` |
| Commande à distance & démo | `src/inclusive_maker/remote_command/`, `frontend/`, `hardware/` | `server.py`, `client.py`, `protocol.py` |

## 7. Workflow Git

Avant chaque session de travail :
```bash
git pull origin main
```

Après avoir fait des modifications :
```bash
git add .
git commit -m "description claire de ce que tu as fait"
git push origin main
```

Si plusieurs personnes travaillent en même temps, utilise des **branches** :
```bash
git checkout -b ma-branche
# travaille...
git add .
git commit -m "mon travail"
git push origin ma-branche
```

Puis crée une **Pull Request** sur GitHub pour fusionner.

## 8. Résolution des problèmes courants

### `ModuleNotFoundError: No module named 'inclusive_maker'`
Solution : n'oublie pas le `PYTHONPATH=src` devant les commandes.

### `gpype` ne s'installe pas
Solution : ce n'est pas bloquant pour la phase actuelle. Le projet fonctionne sans `gpype` en mode démo.

### Impossible de pousser sur GitHub
Solution : demande à être ajouté comme collaborateur sur le repo GitHub, ou utilise une Pull Request.
