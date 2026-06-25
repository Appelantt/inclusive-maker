# Installation du SDK Unicorn Hybrid Black sous Windows

Ce guide explique comment installer le logiciel g.tec nécessaire au casque EEG **Unicorn Hybrid Black** sur Windows.

> ⚠️ Cette installation doit être faite manuellement par un administrateur Windows. Le casque Unicorn Hybrid Black nécessite le SDK propriétaire **g.Pype** et/ou **Unicorn Suite Hybrid Black** de g.tec.

---

## 1. Prérequis

- [ ] **Windows 10 ou 11** (64 bits)
- [ ] **Droits administrateur** sur le PC
- [ ] Casque **Unicorn Hybrid Black** chargé et à proximité
- [ ] Bluetooth activé sur l’ordinateur
- [ ] Avoir téléchargé **Unicorn Suite Hybrid Black** depuis g.tec

---

## 2. Télécharger Unicorn Suite Hybrid Black

1. Se rendre sur le site officiel g.tec :
   - Page produit : https://www.gtec.at/product/unicorn-suite/
   - Page downloads : https://www.gtec.at/downloads/
2. Se connecter ou créer un compte g.tec si demandé.
3. Télécharger **Unicorn Suite Hybrid Black** pour Windows.
4. L’installation inclut généralement :
   - l’application Unicorn Suite
   - le SDK **g.Pype**
   - les pilotes Bluetooth et les DLL natives (`gtec_gds`, etc.)

> 💡 Selon ta licence académique ou commerciale, un compte g.tec peut être nécessaire pour télécharger.

---

## 3. Installer le logiciel

1. [ ] Fermer toutes les applications.
2. [ ] Faire un clic droit sur l’installateur `.exe` → **Exécuter en tant qu’administrateur**.
3. [ ] Cliquer **Oui** si Windows demande l’autorisation.
4. [ ] Choisir la langue (Français ou English).
5. [ ] Accepter la licence.
6. [ ] Choisir l’installation **complète** (ne pas changer le dossier d’installation).
7. [ ] Attendre la fin de l’installation.
8. [ ] **Redémarrer l’ordinateur** (même si ce n’est pas demandé).

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

1. [ ] Allumer le casque Unicorn Hybrid Black (bouton latéral, LED bleue).
2. [ ] L’appairer en Bluetooth depuis Windows (Paramètres → Bluetooth → Ajouter un appareil).
3. [ ] Ouvrir **Unicorn Suite Hybrid Black**.
4. [ ] Vérifier que le signal EEG apparaît à l’écran.

---

## 5. Vérifier l’environnement Python

Ouvrir un terminal dans le projet Inclusive Maker :

```cmd
cd C:\Users\Admin\Desktop\inclusive-maker
venv\Scripts\activate.bat
set PYTHONPATH=src
python scripts\check_unicorn_sdk.py
```

Résultat attendu si tout est OK :
```text
[OK] gpype version : 3.0.9
[OK] Connexion au casque Unicorn réussie !
```

Si le SDK n’est pas encore installé :
```text
[INFO] Unicorn Suite non trouvé aux emplacements habituels.
[INFO] Basculement sur le générateur synthétique (casque non connecté / SDK manquant).
```

---

## 6. Tester avec le dashboard Inclusive Maker

Une fois le SDK installé et le casque appairé :

```cmd
cd C:\Users\Admin\Desktop\inclusive-maker
venv\Scripts\activate.bat
set PYTHONPATH=src
python run_app.py
```

Dans l’interface dashboard, regarde l’indicateur en haut :
- **Source : CASQUE UNICORN** → le vrai casque est connecté
- **Source : SIMULATEUR** → le simulateur interne est actif

---

## 7. Si la connexion échoue

Symptômes possibles :
- `gtec_gds_wrapper.Initialize failed to load either header or DLL`
- `Execution outside supported IDEs detected`
- Le casque n’apparaît pas dans Windows Bluetooth

Actions de diagnostic :

1. [ ] Vérifier que **Unicorn Suite Hybrid Black** est bien installé.
2. [ ] Vérifier que le casque est allumé et appairé en Bluetooth.
3. [ ] Relancer le terminal après l’installation du SDK.
4. [ ] S’assurer d’utiliser Python 64 bits (g.Pype ne supporte pas 32 bits).
5. [ ] Désactiver temporairement le pare-feu Windows qui bloquerait g.tec.
6. [ ] Exécuter l’application en tant qu’administrateur.
7. [ ] En dernier recours, le connecteur Inclusive Maker bascule automatiquement sur le générateur synthétique.

---

## 8. Licence

Le SDK Unicorn Suite et g.Pype sont propriétaires de g.tec. Inclusive Maker reste compatible avec le mode simulateur si tu ne possèdes pas encore le matériel.

