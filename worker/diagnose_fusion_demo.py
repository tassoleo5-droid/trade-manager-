"""MyFlowFX: Fusion Markets DEMO read-only terminal diagnostic.

Attach to the already signed-in MT5 terminal on Windows. No password prompt,
no account credentials persisted, no order submission or modification.
"""
from typing import Any, Optional

EXPECTED_SERVER = "FusionMarkets-Demo"


def diagnose(terminal: Optional[Any] = None) -> dict:
    if terminal is None:
        try:
            import MetaTrader5 as terminal
        except ImportError as exc:
            raise RuntimeError("Module MetaTrader5 non installé") from exc
    if not terminal.initialize():
        return {"status": "terminal_unavailable"}
    try:
        account = terminal.account_info()
        if account is None:
            return {"status": "account_unavailable"}

        if str(getattr(account, "server", "")).strip().casefold() != EXPECTED_SERVER.casefold():
            return {"status": "wrong_server", "expected_server": EXPECTED_SERVER}

        demo_value = getattr(terminal, "ACCOUNT_TRADE_MODE_DEMO", None)
        if not isinstance(demo_value, int):
            return {"status": "demo_mode_unverifiable"}
        if getattr(account, "trade_mode", None) != demo_value:
            return {"status": "not_demo"}

        positions = terminal.positions_get()
        if positions is None:
            return {"status": "positions_unavailable"}

        return {
            "status": "demo_verified",
            "server": EXPECTED_SERVER,
            "account_login": str(getattr(account, "login", "")),
            "positions_count": len(positions),
            "order_execution_enabled": False,
        }
    finally:
        terminal.shutdown()


if __name__ == "__main__":
    try:
        result = diagnose()
        print("MYFLOWFX_DIAGNOSTIC:", result["status"])
        if result["status"] == "demo_verified":
            print("Serveur :", result["server"])
            print("Positions détectées :", result["positions_count"])
            print("Ordres automatiques : DÉSACTIVÉS")
        elif result["status"] == "wrong_server":
            print("Serveur attendu :", result["expected_server"])
        else:
            print("Vérification non réussie. Vérifier que MT5 est ouvert et connecté au compte démo.")
    except RuntimeError as exc:
        print("ERREUR :", str(exc))
