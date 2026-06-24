# Documentation externe et ressources

Ce document regroupe toutes les ressources officielles et communautaires utiles pour le projet **Inclusive Maker**.

## 🧠 Casque Unicorn Hybrid Black

### Site officiel

- **Unicorn Brain Interface** — https://www.unicorn-bi.com/
  - Page produit officielle du casque EEG sans fil Unicorn Hybrid Black.

### Dépôt GitHub officiel

- **Unicorn Suite Hybrid Black** — https://github.com/unicorn-bi/Unicorn-Suite-Hybrid-Black
  - Contient les APIs officielles : Python, .NET, C/C++ Windows, C/C++ Linux, C/C++ Raspberry Pi Zero W.
  - Exemples de streaming UDP et LSL.
  - Documentation du protocole Bluetooth.
  - Tutoriels vidéo pour chaque API et outil.

### Vidéos tutoriels officielles (chaîne Unicorn)

| Tutoriel | Lien |
|---|---|
| Unicorn Suite | https://youtu.be/LOfIr2F7-Tc |
| Hardware Setup and Handling | https://youtu.be/UVVUJTwvGnw |
| Unicorn Recorder | https://youtu.be/s6mOv4nyBHk |
| Unicorn Speller | https://youtu.be/aB60zmmTLq0 |
| Unicorn Speller - Painting add-on | https://youtu.be/b60qF-tX5vY |
| Unicorn Speller - Sphero add-on | https://youtu.be/FmSKfg4SZq0 |
| Unicorn Blondy Check | https://youtu.be/RkLV8xzerfg |
| Unicorn Bandpower | https://youtu.be/_VtA9E0hgUA |
| **Python API** | https://youtu.be/N0d_B0jergs |
| Simulink Interface | https://youtu.be/erYtpEJ_dYc |
| Dev Tools - C API | https://youtu.be/ylbpKTY1Awg |
| Dev Tools - .NET API | https://youtu.be/U8xWlIyY4DI |
| Android API | https://youtu.be/2Oi7AAHapNw |
| **Lab Streaming Layer (LSL)** | https://youtu.be/l18lJ7MGU38 |
| **User Datagram Protocol (UDP)** | https://youtu.be/Wh_C299mCyU |
| Speller Unity Interface | https://youtu.be/fAVcfhJZksc |
| Unity Interface | https://youtu.be/rzqhs7_-RgI |

### FAQ et support

- **Unicorn FAQs** — https://www.unicorn-bi.com/faq/
- **Unicorn Suite Issues** — https://github.com/unicorn-bi/Unicorn-Suite-1.18/issues

## 🐍 SDK g.Pype

### Documentation officielle

- **g.Pype Docs** — https://gpype.gtec.at/
  - Documentation complète du SDK Python BCI de g.tec.
  - Basic Concepts, Training, SDK Reference, FAQ, Troubleshooting.

### Dépôt GitHub

- **g.Pype GitHub** — https://github.com/gtec-medical-engineering/gpype
  - Code source et exemples prêts à l’emploi.
  - Exemples pour HybridBlack, LSL, UDP, filtres, visualisation, paradigmes.

### Exemples g.Pype clés pour notre projet

| Exemple | Fichier dans le repo g.Pype | Usage |
|---|---|---|
| Acquisition Unicorn | `examples/example_devices_hybrid_black.py` | Connecter le casque et visualiser l’EEG |
| Envoi UDP | `examples/example_basic_udp_send.py` | Streamer données + événements en UDP |
| Réception UDP | `examples/example_basic_udp_receive.py` | Recevoir et visualiser un flux UDP |
| Envoi LSL | `examples/example_basic_lsl_send.py` | Streamer via Lab Streaming Layer |
| Réception LSL | `examples/example_basic_lsl_receive.py` | Recevoir un flux LSL |
| Puissance alpha | `examples/example_composite_alpha_power.py` | Extraction de puissance alpha |

## 🌐 Protocoles de streaming

### Lab Streaming Layer (LSL)

- **Site officiel LSL** — https://labstreaminglayer.org/
- **LSL sur GitHub** — https://github.com/sccn/liblsl
- Standard de facto pour le streaming temps réel en neuroscience.

### UDP (User Datagram Protocol)

- Protocole réseau rapide et léger utilisé par Unicorn et g.Pype.
- Format binaire `float32` pour Unicorn, `float64` pour g.Pype `UDPSender`.

## 📚 Ressources pédagogiques BCI

### Chaînes et communautés

- **g.tec medical engineering** — https://www.gtec.at/
  - Éditeur du Unicorn Hybrid Black et de g.Pype.
- **BR41N.IO Hackathon** — https://www.youtube.com/c/BR41NIO
  - Vidéos d’inspiration de hackathons BCI.

### Concepts EEG utiles

| Bande | Fréquence | Association |
|---|---|---|
| Delta | 0.5 – 4 Hz | Sommeil profond |
| Theta | 4 – 8 Hz | Somnolence, méditation |
| Alpha | 8 – 13 Hz | Relaxation, yeux fermés |
| Beta | 13 – 30 Hz | Concentration, activité motrice |
| Gamma | > 30 Hz | Traitement cognitif avancé |

## 🔧 Outils complémentaires

| Outil | Lien | Usage |
|---|---|---|
| Python | https://www.python.org/ | Langage principal du projet |
| NumPy | https://numpy.org/ | Calcul numérique |
| SciPy | https://scipy.org/ | Traitement du signal |
| scikit-learn | https://scikit-learn.org/ | Machine learning |
| PyYAML | https://pyyaml.org/ | Configuration YAML |
| pytest | https://docs.pytest.org/ | Tests automatiques |

---

> 💡 **Conseil** : si vous débutez, regardez d’abord les tutoriels YouTube **Python API**, **LSL** et **UDP** du Unicorn Hybrid Black, puis suivez les exemples g.Pype `example_devices_hybrid_black.py` et `example_composite_alpha_power.py`.
