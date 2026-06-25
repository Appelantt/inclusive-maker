# Installation du SDK Unicorn Hybrid Black sous Windows

Ce guide explique comment installer le logiciel g.tec nécessaire au casque EEG **Unicorn Hybrid Black** sur Windows.

> ⚠️ Cette installation doit être faite manuellement par un administrateur Windows. Le casque Unicorn Hybrid Black nécessite le SDK propriétaire **g.Pype** et/ou **Unicorn Suite Hybrid Black** de g.tec.

---

## 1. Prérequis

- **Windows 10 ou 11** (64 bits)
- **Droits administrateur** sur le PC
- Casque **Unicorn Hybrid Black** chargé et à proximité
- Bluetooth activé sur l’ordinateur

---

## 2. Télécharger Unicorn Suite Hybrid Black

1. Se rendre sur le site officiel g.tec :
   - https://www.gtec.at/downloads/
   - ou directement : recherche "Unicorn Suite Hybrid Black download"
2. Télécharger **Unicorn Suite Hybrid Black** pour Windows.
3. L’installation inclut généralement :
   - l’application Unicorn Suite
   - le SDK **g.Pype**
   - les pilotes Bluetooth et les DLL natives (`gtec_gds`, etc.)

> 💡 Selon ta licence académique ou commerciale, un compte g.tec peut être nécessaire pour télécharger.

---

## 3. Installer le logiciel

1. Lancer l’installateur en tant qu’administrateur (clic droit → *Exécuter en tant qu’administrateur*).
2. Suivre l’assistant d’installation.
3. Redémarrer l’ordinateur si demandé.

Emplacements habituels après installation :

```
C:\Users\<ton_user>\Documents\gtec\Unicorn Suite\Hybrid Black\
```

ou

```
C:\Program Files\gtec\
```

---

## 4. Vérifier l’installation

Après redémarrage, vérifier que les fichiers suivants existent :

```
C:\Users\<ton_user>\Documents\gtec\Unicorn Suite\Hybrid Black\Unicorn.exe
```

Puis tester le casque avec l’application Unicorn fournie :

1. Allumer le casque Unicorn Hybrid Black (bouton latéral).
2. L’appairer en Bluetooth depuis Windows.
3. Ouvrir **Unicorn Suite** et vérifier que le signal EEG apparaît.

---

## 5. Installer la librairie Python g.Pype

Ouvrir un terminal dans le projet Inclusive Maker, activer le venv, puis :

```cmd
venv\Scripts\activate.bat
pip install gpype==3.0.9
```

Cela installe également les dépendances g.tec (`gtec_gds`, `gtec_ble`, etc.).

---

## 6. Tester avec Inclusive Maker

Configurer le projet pour utiliser le vrai casque :

Éditer `config/default.yaml` :

```yaml
eeg:
  device: "unicorn_hybrid_black"  # au lieu de generator
```

Puis lancer l’enregistrement :

```cmd
set PYTHONPATH=src
python scripts\record_eeg.py --device unicorn --duration 30
```

Si le SDK est correctement installé, `inclusive_maker.acquisition.unicorn_connector` se connectera au casque.

---

## 7. Si la connexion échoue

Symptômes possibles :
- `gtec_gds_wrapper.Initialize failed to load either header or DLL`
- `Execution outside supported IDEs detected`
- `Permission denied` sur Git

Actions :
1. Vérifier que **Unicorn Suite** est bien installé.
2. Vérifier que le casque est allumé et appairé en Bluetooth.
3. Relancer le terminal après l’installation du SDK.
4. S’assurer d’utiliser Python 64 bits (g.Pype ne supporte pas 32 bits).
5. En dernier recours, le connecteur Inclusive Maker bascule automatiquement sur le générateur synthétique.

---

## 8. Licence

Le SDK Unicorn Suite et g.Pype sont propriétaires de g.tec. Inclusive Maker reste compatible avec le mode simulateur si tu ne possèdes pas encore le matériel.
