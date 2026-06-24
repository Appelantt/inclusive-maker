# Journal de bord - Inclousive Maker

## Phase 1 : Structure et analyse

### Objectifs
- [x] Analyser la documentation g.Pype et Unicorn Suite.
- [x] Définir le cas d'usage réaliste (démonstrateur BCI pour commande de main simplifiée).
- [x] Créer la structure GitHub complète.
- [x] Rédiger README, documentation d'architecture, setup, journal.
- [x] Implémenter les modules vides + démo synthétique.
- [ ] Créer le repo GitHub public et pousser le code.

### Décisions importantes
- Le projet est un **démonstrateur pédagogique**, pas un dispositif médical.
- L'acquisition directe Unicorn nécessite Windows + Unicorn Suite.
- La démo fonctionne sans matériel via un générateur synthétique.
- La communication à distance utilise **UDP + JSON** pour la simplicité.

## Phase 2 : Acquisition et traitement EEG

### TODO
- [ ] Tester `gp.HybridBlack` sur Windows.
- [ ] Implémenter l'enregistrement EEG vers CSV.
- [ ] Valider les filtres bandpass/notch.
- [ ] Améliorer l'extraction de features.

## Phase 3 : Algorithme de commande

### TODO
- [ ] Collecter des données annotées (OPEN / CLOSE / IDLE).
- [ ] Entraîner un classifieur scikit-learn.
- [ ] Remplacer le détecteur par règles par le classifieur entraîné.

## Phase 4 : Commande à distance et démonstrateur

### TODO
- [ ] Créer un client hardware pour Arduino / Raspberry Pi.
- [ ] Faire une interface web ou une maquette 3D de main.
- [ ] Stabiliser le protocole UDP et ajouter WebSocket optionnel.
