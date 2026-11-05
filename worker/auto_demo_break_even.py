"""Automatic break-even protection for a verified Fusion Markets MT5 DEMO account.

This worker can only change an existing position's stop-loss to its entry price
after it reaches +1R. It never opens positions, closes positions, changes volume,
or changes take-profit. It is disabled unless MYFLOWFX_DEMO_AUTO_BREAK_EVEN=1.
"""
import math
import os

from diagnose_fusion_demo import EXPECTED_SERVER, diagnose

ENABLE_VALUE = "1"
MINIMUM_R = 1.0


def enabled():
    return os.environ.get("MYFLOWFX_DEMO_AUTO_BREAK_EVEN") == ENABLE_VALUE


def _current_price(terminal, position, side):
    price = float(getattr(position, "price_current", 0) or 0)
    if math.isfinite(price) and price > 0:
        return price
    tick = terminal.symbol_info_tick(position.symbol)
    field = "ask" if side == "BUY" else "bid"
    price = float(getattr(tick, field, 0) or 0)
    if not math.isfinite(price) or price <= 0:
        raise RuntimeError("Prix actuel indisponible")
    return price


def protect_positions(output=print, threshold=MINIMUM_R):
    """Move eligible DEMO positions to break-even. Returns a list of outcomes."""
    if not enabled():
        return ["automatisation désactivée"]
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold < 0.1:
        raise RuntimeError("Seuil break-even invalide : aucune modification")

    if diagnose().get("status") != "demo_verified":
        raise RuntimeError("Vérification MT5 démo échouée : aucune modification")

    import MetaTrader5 as terminal
    if not terminal.initialize():
        raise RuntimeError("Terminal MT5 indisponible : aucune modification")

    outcomes = []
    try:
        account = terminal.account_info()
        if account is None or str(getattr(account, "server", "")).strip().casefold() != EXPECTED_SERVER.casefold():
            raise RuntimeError("Compte non démo détecté : aucune modification")
        if getattr(account, "trade_mode", None) != getattr(terminal, "ACCOUNT_TRADE_MODE_DEMO", None):
            raise RuntimeError("Compte non démo détecté : aucune modification")

        positions = terminal.positions_get()
        if positions is None:
            raise RuntimeError("Positions MT5 indisponibles : aucune modification")

        for position in positions:
            side = "BUY" if position.type == terminal.POSITION_TYPE_BUY else "SELL"
            entry = float(position.price_open)
            stop = float(position.sl or 0)
            if not (math.isfinite(entry) and entry > 0 and math.isfinite(stop) and stop > 0):
                outcomes.append(f"{position.ticket}: stop-loss absent, ignoré")
                continue

            tolerance = max(0.00001, abs(entry) * 0.000001)
            if abs(stop - entry) <= tolerance:
                outcomes.append(f"{position.ticket}: break-even déjà confirmé")
                continue

            valid_stop = (side == "BUY" and stop < entry) or (side == "SELL" and stop > entry)
            if not valid_stop:
                outcomes.append(f"{position.ticket}: stop-loss non valide, ignoré")
                continue

            risk = abs(entry - stop)
            current = _current_price(terminal, position, side)
            r_value = (current - entry) / risk if side == "BUY" else (entry - current) / risk
            if r_value < threshold:
                outcomes.append(f"{position.ticket}: {r_value:.2f}R, break-even non atteint (seuil {threshold:.2f}R)")
                continue

            result = terminal.order_send({
                "action": terminal.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "symbol": position.symbol,
                "sl": entry,
                "tp": float(position.tp or 0),
                "comment": "MyFlowFX DEMO break-even",
            })
            success = result is not None and getattr(result, "retcode", None) == terminal.TRADE_RETCODE_DONE
            if success:
                outcomes.append(f"{position.ticket}: break-even placé à {entry}")
            else:
                code = getattr(result, "retcode", "sans réponse")
                outcomes.append(f"{position.ticket}: modification refusée ({code})")

        for outcome in outcomes:
            output("BREAK_EVEN_DEMO:", outcome)
        return outcomes
    finally:
        terminal.shutdown()


if __name__ == "__main__":
    try:
        if not enabled():
            print("BREAK_EVEN_DEMO: désactivé. Aucun ordre modifié.")
        else:
            protect_positions()
    except RuntimeError as exc:
        print("BREAK_EVEN_DEMO: arrêté.", str(exc))
