# Cahier des charges - Inclusive Maker (Fork 4 Commande cérébrale)

## 1. Présentation

**Projet** : Système de commande cérébrale pour contrôler l'ouverture/fermeture de gants.

**Équipe** : Flavien, Aurélien, Tadedo (rôles Prog / Hard / Doc à répartir).

**Utilisateur référence** : Philippe Oulevay (paralysie des mains, bras et parole conservés).

**Événement** : Inclusiv'Maker, juin-juillet 2026.

## 2. Objectifs fonctionnels

### 2.1 Objectif principal (MVP)

Commander à distance l'ouverture et la fermeture d'un gant motorisé grâce à l'activité cérébrale captée par un casque EEG non invasif.

### 2.2 Commandes attendues

| Commande | Effet |
|---|---|
| **OPEN** | Ouvrir la main / gant |
| **CLOSE** | Fermer la main / gant |
| **IDLE** | Maintenir la position actuelle / ne rien faire |

### 2.3 Degré de liberté

**1 DOF** : ouverture / fermeture.

## 3. Architecture du système

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  Casque EEG     │────▶│  Logiciel Python │────▶│  Actionneur   │
│  Unicorn        │     │  Acquisition     │     │  Gant / Servo │
│  Hybrid Black   │     │  Traitement      │     │               │
└─────────────────┘     │  Classification  │     └───────────────┘
                        │  Commande UDP    │            ▲
                        └──────────────────┘            │
                                   │                    │
                                   └────────────────────┘
                                          Retour visuel
```

## 4. Modules logiciels

### 4.1 Acquisition EEG

- Support du casque **Unicorn Hybrid Black** (Windows + Unicorn Suite)
- Mode **générateur synthétique** pour développement sans matériel
- Streaming possible via **LSL** ou **UDP**

### 4.2 Traitement du signal

- Filtrage passe-bande (1-30 Hz)
- Notch 50 Hz / 60 Hz
- Extraction de features en temps réel (bandpower alpha/bêta)

### 4.3 Classification / commande

- Détecteur simple par seuil (phase 1)
- Classifieur scikit-learn entraîné (phase 2)
- Lissage temporel pour éviter les commandes parasites

### 4.4 Commande à distance

- Protocole **UDP JSON**
- Format : `{"action": "OPEN|CLOSE|IDLE", "value": float, "label": str, "timestamp": float}`

### 4.5 Interface graphique

- **Dashboard temps réel** : état détecté, dernière commande, signal EEG
- **Assistant de calibration** : guide l'utilisateur pour associer ses états mentaux aux commandes
- **Tutoriel d'entraînement** : sessions guidées

### 4.6 Actionneur (hardware)

- Réception des commandes UDP
- Contrôle d'un servomoteur ou gants motorisés
- Sécurité : bouton d'arrêt, limitation de course

## 5. Contraintes

### 5.1 Techniques

- Python 3.10+
- g.Pype nécessite Windows pour acquisition réelle
- Développement possible sur macOS/Linux en mode démo

### 5.2 Utilisateur

- Utilisateur paralysé des mains mais capable de parler
- Interface accessible, simple, avec retours visuels/sonores clairs
- Sécurité primordiale (pas de mouvement intempestif dangereux)

### 5.3 Projet

- Livrable open-source sur GitHub
- Documentation sur Hackster.io
- Tests utilisateurs avec Philippe
- Showroom final le 9 juillet 2026

## 6. Scénarios d'usage

### Scénario nominal

1. Philippe met le casque EEG.
2. Il lance le logiciel et suit le tutoriel d'entraînement.
3. L'interface affiche l'état détecté.
4. Philippe pense à "ouvrir" → le gant s'ouvre.
5. Philippe pense à "fermer" → le gant se ferme.

### Scénario sans système

Philippe doit demander de l'aide à une tierce personne pour enfiler/utiliser ses gants.

### Scénario pire cas

Le système détecte une fausse commande → le gant se ferme au mauvais moment.

**Mitigation** :
- Seuil de confiance élevé
- Commande IDLE par défaut
- Bouton d'arrêt d'urgence
- Limitation de la force/vitesse du mouvement

## 7. Tests et validation

### Tests techniques

- Tests unitaires sur les modules Python (8 tests de base)
- Démo sans matériel (UDP + signaux synthétiques)
- Test de latence commande → action

### Tests utilisateurs

- Session avec Philippe
- Mesure du taux de réussite des commandes
- Recueil du ressenti et des améliorations possibles

## 8. Livrables

| Livrable | Responsable | Échéance |
|---|---|---|
| Architecture logicielle | Prog | 02/07 |
| Acquisition EEG réelle | Prog / Hard | 03/07 |
| Algorithme de commande | Prog | 06/07 |
| Interface graphique | Prog / Doc | 06/07 |
| Prototype gant/actionneur | Hard | 07/07 |
| Tutoriel d'entraînement | Doc / Prog | 07/07 |
| Documentation Hackster | Doc | 09/07 |
| Présentation showroom | Tous | 09/07 |
