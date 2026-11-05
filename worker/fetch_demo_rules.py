"""Fetch account-scoped strategy rules for a verified MT5 DEMO worker.

The worker sends only its already verified demo login and server plus the
staging worker token. No password or trade details are transmitted.
"""
import json
import math
import urllib.error
import urllib.request

from diagnose_fusion_demo import EXPECTED_SERVER, diagnose
from report_demo_heartbeat import settings

DEFAULT_RULES = {
    "enabled": False,
    "beThreshold": 1.0,
    "tpCount": 3,
    "tpPercents": [50, 25, 25],
    "tpTargetsR": [1, 2, 3],
}

def _validate(value):
    if not isinstance(value, dict) or value.get("enabled") is not False:
        raise RuntimeError("Réglages démo invalides")
    count = value.get("tpCount")
    percents = value.get("tpPercents")
    targets = value.get("tpTargetsR")
    threshold = value.get("beThreshold")
    if count not in (1, 2, 3) or not isinstance(percents, list) or not isinstance(targets, list):
        raise RuntimeError("Réglages TP invalides")
    if len(percents) != count or len(targets) != count:
        raise RuntimeError("Réglages TP incomplets")
    if (not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or
            threshold < 0.1 or threshold > 10):
        raise RuntimeError("Seuil break-even invalide")
    if (any(type(p) is not int or p <= 0 or p > 100 for p in percents) or
            sum(percents) != 100):
        raise RuntimeError("Pourcentages TP invalides")
    if (any(not isinstance(target, (int, float)) or not math.isfinite(target) or target < 0.1 or target > 30
            for target in targets) or any(targets[i] <= targets[i - 1] for i in range(1, len(targets)))):
        raise RuntimeError("Niveaux TP invalides")
    return {
        "enabled": False,
        "beThreshold": float(threshold),
        "tpCount": count,
        "tpPercents": list(percents),
        "tpTargetsR": [float(target) for target in targets],
    }

def fetch(opener=urllib.request.urlopen):
    result = diagnose()
    if result.get("status") != "demo_verified":
        raise RuntimeError("Compte démo non vérifié : réglages non chargés")
    login = str(result.get("account_login") or "")
    if not login.isdigit():
        raise RuntimeError("Identifiant du compte démo indisponible")
    base_url, token = settings()
    request = urllib.request.Request(
        base_url + "/api/worker/rules",
        headers={
            "X-MyFlowFX-Worker-Token": token,
            "X-MyFlowFX-Account-Login": login,
            "X-MyFlowFX-Account-Server": EXPECTED_SERVER,
        },
        method="GET",
    )
    try:
        with opener(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError("Réglages du compte démo refusés")
            return _validate(json.loads(response.read().decode("utf-8")).get("rules"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Réglages du compte démo non disponibles") from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("Réglages du staging indisponibles") from exc
