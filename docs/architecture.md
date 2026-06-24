# Architecture du système

## Vue d'ensemble

inclusive Maker est composé de 4 modules principaux :

```
+---------------+      +----------------------+      +----------------+      +------------------+
|  Acquisition  | -> |  Signal Processing   | -> |   Brain Algo   | -> |  Remote Command  |
|   EEG         |      |  (filtres/features)  |      | (décision BCI) |      | (UDP/WebSocket)  |
+---------------+      +----------------------+      +----------------+      +------------------+
        |                                                                               |
        |                        Flux de données temps réel                              |
        v                                                                               v
  Unicorn Hybrid Black                                                    Actionneur / Client / UI
```

## Modules

### 1. Acquisition (`src/inclusive_maker/acquisition/`)

Responsabilité : obtenir les données EEG brutes.

- `unicorn_connector.py` : connecte le casque Unicorn via g.Pype, ou un générateur synthétique.
- Peut aussi recevoir un flux LSL/UDP externe.

### 2. Traitement du signal (`src/inclusive_maker/signal_processing/`)

Responsabilité : nettoyer le signal et extraire des features.

- Filtrage passe-bande, notch 50/60 Hz.
- Extraction de bandes de puissance (delta, theta, alpha, beta).
- Future : CSP, imagerie motrice, ERP, SSVEP.

### 3. Algorithme de commande (`src/inclusive_maker/brain_algo/`)

Responsabilité : décider d'une commande.

- `mental_state_detector.py` : règles simples sur les features.
- `command_mapper.py` : associe état → commande.
- `classifier.py` : futur classifieur ML (scikit-learn).

### 4. Commande à distance (`src/inclusive_maker/remote_command/`)

Responsabilité : transporter la commande vers un client.

- `protocol.py` : format normalisé `CommandPacket` (JSON).
- `client.py` : envoie UDP.
- `server.py` : reçoit UDP et appelle un handler.

## Flux de données

1. **Acquisition** produit des trames EEG (8 canaux × 250 Hz).
2. **Signal** filtre et calcule les features toutes les **N secondes**.
3. **Brain Algo** détermine l'état mental (OPEN / CLOSE / IDLE).
4. **Remote Command** sérialise et envoie la commande.

## Formats de données

### Paquet de commande (UDP / WebSocket)

```json
{
  "action": "OPEN",
  "value": 1.0,
  "label": "open_hand",
  "timestamp": 1710000000.123
}
```

### Configuration

Toute la configuration est en YAML dans `config/`.

## Limites et contraintes

- g.Pype `HybridBlack` nécessite **Windows + Unicorn Suite installé**.
- Sous macOS/Linux, on utilise le **générateur** ou un flux LSL/UDP externe.
- L'approche alpha est un **démonstrateur** ; pour du vrai contrôle fin, il faudrait un classifieur entraîné.
- Le projet est **non médical** et ne prétend pas traiter la paralysie.
