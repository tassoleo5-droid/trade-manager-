"""MyFlowFX: read-only position monitoring on a Fusion Markets MT5 demo VPS.

Never submits, changes, or closes positions. Does not read or print passwords,
account login IDs, equity, P&L or complete position details.

Run with: py -3.12 watch_fusion_demo.py
"""
import time
from diagnose_fusion_demo import diagnose

INTERVAL_SECONDS = 3
DURATION_SECONDS = 90

def snapshot(terminal=None):
    status = diagnose(terminal)
    if status.get("status") != "demo_verified":
        raise RuntimeError("Diagnostic stopped: " + str(status.get("status", "unknown")))
    count = status.get("positions_count")
    if type(count) is not int or count < 0:
        raise RuntimeError("Invalid positions count from MT5")
    return count

def watch(check=snapshot, sleep=time.sleep, clock=time.monotonic,
          output=print, duration=DURATION_SECONDS, interval=INTERVAL_SECONDS):
    if duration <= 0 or interval <= 0:
        raise ValueError("Duration and interval must be positive")
    output("MyFlowFX DEMO - surveillance LECTURE SEULE")
    output("Ouverture, modification et clôture automatiques : DÉSACTIVÉES")
    deadline = clock() + duration
    last = None
    while clock() < deadline:
        count = check()  # Reconfirm broker server + demo trade mode on each cycle.
        if count != last:
            output("Positions ouvertes détectées : " + str(count))
            last = count
        if clock() + interval < deadline:
            sleep(interval)
        else:
            break
    output("Test terminé : aucun ordre envoyé.")

if __name__ == "__main__":
    try:
        watch()
    except KeyboardInterrupt:
        print("Surveillance arrêtée par utilisateur. Aucun ordre envoyé.")
    except (RuntimeError, OSError, ValueError) as exc:
        # The exception messages do not include credentials or account identifiers.
        print("Test interrompu :", str(exc))
