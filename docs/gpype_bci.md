# Pipeline BCI g.Pype + calibration

Ce document décrit la chaîne de traitement **100 % g.Pype** qui lit le casque
Unicorn Hybrid Black en temps réel et produit une décision binaire **OUVRIR /
FERMER**, ainsi que la **calibration** sur le cerveau de l'utilisateur.

Scripts concernés :
- [`scripts/gpype_pipeline.py`](../scripts/gpype_pipeline.py) — le pipeline (affichage / enregistrement)
- [`scripts/calibrate.py`](../scripts/calibrate.py) — la calibration LDA
- [`scripts/diagnose_connection.py`](../scripts/diagnose_connection.py) — diagnostic de connexion casque

---

## 1. Architecture du pipeline

```
casque Unicorn (HybridBlack, UnicornPy / Bluetooth)
   │
   ├─ Bandpass 1–30 Hz            → retire dérive DC et bruit HF
   ├─ Bandstop 48–52 Hz + 58–62 Hz → retire le secteur 50/60 Hz
   │
   ├─ sélection du canal moteur C3 (index 1)
   │
   ├─ branche ALPHA (8–12 Hz)  : Bandpass → carré (in²) → moyenne glissante 1 s
   ├─ branche BÊTA  (13–30 Hz) : Bandpass → carré (in²) → moyenne glissante 1 s
   │
   ├─ commande = (bêta − alpha) / (alpha + bêta)   ∈ [-1, 1]
   │        > 0 → concentration (FERMER)   |   < 0 → relaxation (OUVRIR)
   │
   └─ ÉTAT binaire :
        • sans calibration : sign(commande)
        • avec calibration : sign(wa·alpha + wb·bêta + biais)   ← LDA appris sur l'utilisateur
```

Le tout est construit avec des **nœuds g.Pype officiels** (`HybridBlack`,
`Bandpass`, `Bandstop`, `Router`, `Equation`, `MovingAverage`, `TimeSeriesScope`,
`CsvWriter`). g.Pype interdit les nœuds « maison » (contrôle d'intégrité), d'où le
choix de tout exprimer avec des `Equation`.

**Disposition des électrodes** (index 0→7) : `Fz C3 Cz C4 Pz PO7 PO8 Oz`.
`C3` (index 1) = cortex moteur gauche → **main droite** ; `C4` (index 3) = main gauche.

**État binaire** : le système n'a que **2 fonctions** (gant piloté par une carte
Arduino), donc pas d'état « repos » — à chaque instant c'est OUVRIR ou FERMER.

**Moyenne glissante 1 s** (`window_size=250` à 250 Hz) : privilégie la **stabilité**
(un gant ne doit pas se gonfler/dégonfler en rafale) au prix d'un peu de latence.

---

## 2. Prérequis

- **Windows 10/11**.
- **Unicorn Suite** installé, **avec le module « Unicorn Python » (UnicornPy)**.
  Il s'installe depuis l'application Unicorn Suite et se trouve dans
  `Documents\gtec\Unicorn Suite\Hybrid Black\Unicorn Python\Lib\UnicornPy.pyd`.
- Casque **allumé**, **appairé** en Bluetooth.
- **Unicorn Suite / Unicorn LSL / Unicorn Recorder FERMÉS** : le casque ne peut être
  ouvert que par un seul logiciel à la fois.

### Le monkeypatch g.tec (pas de licence Runtime)

g.Pype refuse par défaut de s'exécuter hors d'un IDE supporté. L'exemple officiel
g.tec fournit le contournement, que nos scripts appliquent :

```python
from gpype.backend.core.node import Node
Node._is_executed_in_ide = lambda self: True
```

Résultat : g.Pype tourne depuis **n'importe quel terminal**, sans licence Runtime.

### Encodage UTF-8

Les scripts forcent l'UTF-8 (`sys.stdout.reconfigure(...)`), sinon un thread de
monitoring de g.Pype plante en `cp1252` sous Windows.

---

## 3. Lancer le pipeline

Casque porté et libre (aucune app Unicorn ouverte) :

```powershell
cd inclusive-maker
$env:PYTHONPATH="src"; venv\Scripts\python.exe scripts\gpype_pipeline.py
```

Fenêtre temps réel avec 4 courbes : **alpha%**, **bêta%**, **commande**, **ÉTAT**.

| Option | Effet |
|---|---|
| *(aucune)* | Casque réel → affichage temps réel |
| `--sim` | Signal simulé (sans casque) → affichage |
| `--record --seconds 10` | Casque réel → enregistrement CSV (`data/raw/gpype_bci_*.csv`) |
| `--serial UN-2022.01.08` | Choisir un casque précis |

---

## 4. Calibration (adaptée à l'utilisateur)

Sans calibration, l'état repose sur un seuil générique. La calibration entraîne un
**classifieur LDA** sur les vraies données de l'utilisateur (FP1 + FC3 du CdC).

```powershell
$env:PYTHONPATH="src"; venv\Scripts\python.exe scripts\calibrate.py
```

Déroulé (≈ 2 min, casque porté, immobile) :
1. Le script affiche tour à tour **« IMAGINE FERMER LA MAIN DROITE »** et
   **« IMAGINE OUVRIR LA MAIN DROITE »** (6 essais par classe).
2. Il enregistre les puissances alpha/bêta sur C3 pendant chaque consigne.
3. Il entraîne un LDA, affiche la **précision** (validation croisée) et sauvegarde
   `config/calibration.json`.

Le pipeline charge ensuite cette calibration **automatiquement**.

Options : `--blocks 8` (plus d'essais = plus fiable), `--sim` (test mécanique sans casque).

> Si la précision est **< 65 %** : vérifier le contact des électrodes (surtout C3),
> rester immobile, et refaire. Si *ouvrir vs fermer de la même main* reste trop
> subtil, envisager le paradigme **C3 vs C4** (imaginer main droite vs gauche),
> beaucoup plus séparable.

---

## 5. Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| `g.Pype Runtime is required` | Le monkeypatch n'est pas appliqué — utiliser nos scripts (ils l'appliquent). |
| `UnicornPy` introuvable | Installer le module « Unicorn Python » depuis Unicorn Suite. |
| `Couldn't connect to device` (err. 4) | Casque occupé (fermer Unicorn Suite/LSL/Recorder) ou endormi (l'éteindre/rallumer). |
| `Couldn't initialize Bluetooth lookup service` (err. 3) | Pile Bluetooth figée : Bluetooth Windows OFF/ON, ou redémarrer le PC. |
| Courbes plates | Casque non porté ou mauvais contact d'électrode (C3). |
| `buffer underrun` / peu de données | Ne pas fixer `frame_size` sur `HybridBlack` (laisser la valeur par défaut). |
| Le casque se déconnecte tout seul | Mise en veille automatique après inactivité → le rallumer. |

Lancer le diagnostic pour un état des lieux :

```powershell
$env:PYTHONPATH="src"; venv\Scripts\python.exe scripts\diagnose_connection.py
```

---

## 6. Étapes suivantes

- **Pilotage du gant** : envoyer l'ÉTAT vers la carte Arduino (liaison série) + anti-rebond.
- **Sécurité (FC4)** : mode fail-safe si signal perdu > 1 s ou batterie faible.
- **Paradigme C3 vs C4** si la calibration ouvrir/fermer sépare mal.
- **Étiquettes de courbes** et tableau de bord unifié pour la démo.
