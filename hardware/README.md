# Hardware - inclusive Maker

Code et schémas pour l'actionneur commandé à distance.

## Cible initiale

- Arduino ou Raspberry Pi Zero W recevant des commandes UDP.
- Servomoteur SG-90 simulant l'ouverture / fermeture d'une main.

## Commandes reçues

Format JSON sur UDP :

```json
{"action": "OPEN", "value": 1.0, "label": "open_hand"}
```

## TODO

- [ ] Sketch Arduino d'écoute UDP.
- [ ] Montage servomoteur + maquette de main.
- [ ] Test avec le client Python.
