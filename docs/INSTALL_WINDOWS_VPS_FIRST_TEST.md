# Premier diagnostic MT5 — VPS Windows / Fusion Markets

**Phase en lecture seule.** Vérifie le compte MT5 démo déjà connecté sur le
VPS, sans ressaisir le mot de passe et sans envoyer d'ordres.

## 1. Installer Python 3.12 x64
Sur le VPS Windows, ouvrir la page officielle
https://www.python.org/downloads/release/python-31210/
et choisir **Windows installer (64-bit)**.
Pendant l'installation, activer **Add Python to PATH** si proposé.

Ouvrir PowerShell en session utilisateur Windows et vérifier :

```powershell
py -3.12 --version
```

## 2. Installer le connecteur MetaTrader5

```powershell
py -3.12 -m pip install --upgrade MetaTrader5
```

Le package officiel fournit des roues Windows 64-bit pour Python 3.12.
Garder MT5 ouvert et connecté à **FusionMarkets-Demo**.

## 3. Télécharger et exécuter uniquement le diagnostic

```powershell
New-Item -ItemType Directory -Force -Path C:\MyFlowFX | Out-Null
Set-Location C:\MyFlowFX
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tassoleo5-droid/trade-manager-/0582eb2d0aeb76087577ad15ff0cd2fd5a698855/worker/diagnose_fusion_demo.py" -OutFile "diagnose_fusion_demo.py"
py -3.12 .\diagnose_fusion_demo.py
```

Résultat attendu :

```
MYFLOWFX_DIAGNOSTIC: demo_verified
Serveur : FusionMarkets-Demo
Positions détectées : 0
Ordres automatiques : DÉSACTIVÉS
```

Si `positions_count` est > 0, le script n'effectue aucune action sur ces
positions.

## À ne pas faire
- Ne pas installer l'agent d'exécution MyFlowFX ni activer le trading automatique.
- Ne pas saisir de mots de passe MT5 dans le terminal PowerShell ou dans le chat.
- Ne pas connecter de comptes réels au diagnostic.
- Ne pas déployer sur Railway en production : la phase d'intégration a besoin
  d'un environnement test isolé et de tests supplémentaires.

## Prochaine étape
Après le statut `demo_verified` : isoler l'environnement Railway de test,
configurer la communication sécurisée et effectuer des essais en **lecture seule**
de la détection des positions, avant les tests de BE/TP sur démo.
