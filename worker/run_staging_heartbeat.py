"""Continuous read-only MyFlowFX staging monitor for a Fusion Markets MT5 DEMO VPS.

Every minute it sends only the demo flag and the number of open positions.
It never sends credentials, account identifiers, pricing data or orders.
Stop safely with Ctrl+C.
"""
import time

from report_demo_heartbeat import report

INTERVAL_SECONDS = 60

def run(send=report, sleep=time.sleep, output=print, interval=INTERVAL_SECONDS):
    if type(interval) is not int or interval < 30:
        raise ValueError("The interval must be at least 30 seconds")
    output("MyFlowFX staging — surveillance continue LECTURE SEULE")
    output("Ordres MT5 : ouverture, modification et clôture DÉSACTIVÉES")
    while True:
        try:
            send()
            output("Signal staging envoyé. Aucun ordre envoyé.")
        except RuntimeError as exc:
            output("Signal non envoyé :", str(exc))
        try:
            sleep(interval)
        except KeyboardInterrupt:
            output("Surveillance arrêtée. Aucun ordre envoyé.")
            return

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Surveillance arrêtée. Aucun ordre envoyé.")
