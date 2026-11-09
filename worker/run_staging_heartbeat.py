"""Continuous MyFlowFX staging monitor for a Fusion Markets MT5 DEMO VPS.

It always sends read-only telemetry. Automatic break-even is optional and runs
only when MYFLOWFX_DEMO_AUTO_BREAK_EVEN=1 is set locally on the Windows VPS.
It never opens positions. Demo TP closure requires explicit local activation.
Stop safely with Ctrl+C.
"""
import os
import time

from auto_demo_break_even import enabled as break_even_enabled, protect_positions
from auto_demo_position_manager import enabled as exit_enabled, manage_positions, preview_positions
from report_demo_heartbeat import report
from fetch_demo_rules import fetch as fetch_rules
from report_demo_positions import report_positions

DEFAULT_INTERVAL_SECONDS = 5
MIN_INTERVAL_SECONDS = 2
MAX_INTERVAL_SECONDS = 60


def poll_interval_from_environment():
    """Return a bounded polling delay chosen locally on the demo VPS."""
    raw_value = os.getenv("MYFLOWFX_POLL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
    try:
        interval = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS
    return min(MAX_INTERVAL_SECONDS, max(MIN_INTERVAL_SECONDS, interval))


def run(send=report, sleep=time.sleep, output=print, interval=None):
    if interval is None:
        interval = poll_interval_from_environment()
    if type(interval) is not int or not MIN_INTERVAL_SECONDS <= interval <= MAX_INTERVAL_SECONDS:
        raise ValueError(
            f"The interval must be an integer between {MIN_INTERVAL_SECONDS} and {MAX_INTERVAL_SECONDS} seconds"
        )
    automatic_break_even = break_even_enabled()
    automatic_exits = exit_enabled()
    output("MyFlowFX staging — surveillance continue")
    output(f"Fréquence de surveillance : toutes les {interval} secondes")
    output("MT5 : ouverture désactivée ; clôture démo " + ("activée" if automatic_exits else "désactivée"))
    output("Break-even automatique démo :", "ACTIVÉ" if automatic_break_even else "DÉSACTIVÉ")
    output("TP automatique démo :", "ACTIVÉ" if automatic_exits else "DÉSACTIVÉ")
    output("Simulation TP démo : ACTIVÉE (aucune clôture)")
    while True:
        try:
            rules = fetch_rules()
            # Capture the original SL risk before break-even can move the SL.
            # TP simulation stays strictly read-only.
            preview_positions(rules, output=output)
            if automatic_exits:
                manage_positions(rules, output=output)
            if automatic_break_even:
                protect_positions(output=output, threshold=rules["beThreshold"])
            send()
            report_positions()
            output("Réglages du compte démo appliqués. Signal et positions envoyés. Ouverture désactivée. " + ("TP démo automatique actif." if automatic_exits else "Clôture automatique désactivée."))
        except RuntimeError as exc:
            output("Cycle non terminé :", str(exc))
        try:
            sleep(interval)
        except KeyboardInterrupt:
            output("Surveillance arrêtée.")
            return


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Surveillance arrêtée.")
