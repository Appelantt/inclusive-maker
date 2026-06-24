# Guide d'accessibilité - Inclusive Maker

Ce projet vise à être utilisable par des personnes en situation de handicap, notamment visuel. Cette page liste les règles appliquées à l'interface.

## 🎨 Palette adaptée aux troubles visuels

### Daltonisme

Ne jamais se fier seulement à la couleur. Toujours combiner :
- **Couleur**
- **Forme / icône**
- **Texte explicite**

### Palette de couleurs approuvée

| État | Couleur principale | Icône | Texte |
|---|---|---|---|
| OPEN (ouvrir) | Bleu clair `#4FC3F7` | Main ouverte ✋ | "OUVRIR" |
| CLOSE (fermer) | Orange `#FF9800` | Poing ✊ | "FERMER" |
| IDLE (neutre) | Gris neutre `#9E9E9E` | Pause ⏸ | "NEUTRE" |
| Actif / OK | Vert `#2E7D32` | Check ✓ | "PRÊT" |
| Alerte | Violet `#7B1FA2` | Warning ⚠ | "ATTENTION" |
| Erreur | Rouge vif `#D32F2F` | Croix ✕ | "ERREUR" |

> Le bleu et l'orange sont bien distingués par la plupart des daltoniens. Le rouge n'est utilisé que pour les erreurs, jamais seul.

## 🔠 Typographie

- Police sans-serif (Inter, Arial, ou système)
- Taille minimale : 16px pour le texte courant
- Titres : 24px minimum
- Boutons : 18px minimum
- Contraste minimum : 4.5:1 (texte), 3:1 (composants interactifs)

## 🖱️ Interface linéaire

- Pas de menus déroulants complexes
- Flux de haut en bas
- Une seule action principale par écran
- Étapes numérotées : 1 → 2 → 3

## 🔊 Retours multi-modaux

Chaque action importante doit avoir :
- Un retour visuel (changement de couleur, icône)
- Un retour textuel explicite
- Un retour sonore optionnel (beep)

## ⌨️ Navigation clavier

- Tous les boutons accessibles avec Tab
- Touche Espace ou Entrée pour valider
- Focus visible (contour épais)

## 🧪 Tests d'accessibilité recommandés

1. Vérifier les contrastes avec un outil en ligne
2. Tester avec un simulateur de daltonisme
3. Naviguer uniquement au clavier
4. Tester avec VoiceOver / NVDA
5. Vérifier la lisibilité à 2 mètres de distance
