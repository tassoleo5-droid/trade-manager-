"""Continuous MyFlowFX staging monitor for a Fusion Markets MT5 DEMO VPS.

It always sends read-only telemetry. Automatic break-even is optional and runs
only when MYFLOWFX_DEMO_AUTO_BREAK_EVEN=1 is set locally on the Windows VPS.
It never opens or closes positions.
Stop safely with Ctrl+C.
"""
import time

from auto_demo_break_even import enabled as break_even_enabled, protect_positions
from auto_demo_position_manager import enabled as exit_enabled, manage_positions
from report_demo_heartbeat import report
from fetch_demo_rules import fetch as fetch_rules
from report_demo_positions import report_positions

INTERVAL_SECONDS = 60

def run(send=report, sleep=time.sleep, output=print, interval=INTERVAL_SECONDS):
    if type(interval) is not int or interval < 30:
        raise ValueError("The interval must be at least 30 seconds")
    automatic_break_even = break_even_enabled()
    automatic_exits = exit_enabled()
    output("MyFlowFX staging — surveillance continue")
    output("MT5 : ouverture et clôture DÉSACTIVÉES")
    output("Break-even automatique démo :", "ACTIVÉ" if automatic_break_even else "DÉSACTIVÉ")
    output("TP automatique démo :", "ACTIVÉ" if automatic_exits else "DÉSACTIVÉ")
    while True:
        try:
            rules = fetch_rules() if (automatic_break_even or automatic_exits) else None
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
