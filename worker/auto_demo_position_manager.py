"""Account-configured automatic TP management for verified MT5 DEMO Forex positions.

Rules are received from MyFlowFX staging for the verified demo account. It can
only reduce or close existing Forex positions; it never sends entry orders.
It is intentionally disabled in the current staging phase. TP rules may be read and validated, but the worker must not close positions automatically.
"""
import json
import math
import os
from pathlib import Path

from diagnose_fusion_demo import EXPECTED_SERVER, diagnose

STATE_FILE = Path(__file__).with_name("demo_exit_state.json")
FOREX_CURRENCIES = {
    "AUD", "CAD", "CHF", "CNH", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF",
    "JPY", "MXN", "NOK", "NZD", "PLN", "SEK", "SGD", "TRY", "USD", "ZAR",
}

def enabled():
    """TP execution is not authorised in the current demo staging phase."""
    return False

def _load_state():
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_state(state):
    STATE_FILE.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")

def _price(terminal, position, side):
    tick = terminal.symbol_info_tick(position.symbol)
    price = float(getattr(tick, "bid" if side == "BUY" else "ask", 0) or 0)
    if not math.isfinite(price) or price <= 0:
        raise RuntimeError("Prix actuel indisponible")
    return price

def _close(terminal, position, side, volume):
    info = terminal.symbol_info(position.symbol)
    if info is None:
        raise RuntimeError("Instrument indisponible")
    minimum = float(getattr(info, "volume_min", 0) or 0)
    step = float(getattr(info, "volume_step", 0) or 0)
    rounded = round(math.floor((volume + 1e-12) / step) * step, 8) if step > 0 else 0
    if minimum <= 0 or rounded < minimum:
        raise RuntimeError("Volume partiel inférieur au minimum du broker")
    result = terminal.order_send({
        "action": terminal.TRADE_ACTION_DEAL,
        "position": position.ticket,
        "symbol": position.symbol,
        "volume": rounded,
        "type": terminal.ORDER_TYPE_SELL if side == "BUY" else terminal.ORDER_TYPE_BUY,
        "price": _price(terminal, position, side),
        "deviation": 20,
        "type_filling": terminal.ORDER_FILLING_IOC,
        "comment": "MyFlowFX DEMO TP",
    })
    if result is None or getattr(result, "retcode", None) != terminal.TRADE_RETCODE_DONE:
        raise RuntimeError("Clôture refusée: " + str(getattr(result, "retcode", "sans réponse")))
    return rounded

def _is_forex(terminal, symbol):
    info = terminal.symbol_info(symbol)
    base = str(getattr(info, "currency_base", "")).upper()
    quote = str(getattr(info, "currency_profit", "")).upper()
    return base in FOREX_CURRENCIES and quote in FOREX_CURRENCIES and base != quote

def _valid_initial_stop(side, entry, stop):
    return (side == "BUY" and stop < entry) or (side == "SELL" and stop > entry)

def manage_positions(rules, output=print):
    if not enabled():
        return ["TP automatique désactivé"]
    if diagnose().get("status") != "demo_verified":
        raise RuntimeError("Vérification MT5 démo échouée : aucune clôture")
    if not isinstance(rules, dict):
        raise RuntimeError("Réglages du compte démo absents : aucune clôture")
    targets = rules["tpTargetsR"]
    percents = rules["tpPercents"]
    import MetaTrader5 as terminal
    if not terminal.initialize():
        raise RuntimeError("Terminal MT5 indisponible : aucune clôture")
    state, outcomes = _load_state(), []
    output("TP_DEMO: analyse TP démarrée")
    try:
        account = terminal.account_info()
        if account is None or str(getattr(account, "server", "")).strip().casefold() != EXPECTED_SERVER.casefold():
            raise RuntimeError("Compte non démo détecté : aucune clôture")
        if getattr(account, "trade_mode", None) != getattr(terminal, "ACCOUNT_TRADE_MODE_DEMO", None):
            raise RuntimeError("Compte non démo détecté : aucune clôture")
        positions = terminal.positions_get()
        if positions is None:
            raise RuntimeError("Positions MT5 indisponibles : aucune clôture")
        output(f"TP_DEMO: {len(positions)} position(s) MT5 détectée(s)")
        active = {str(position.ticket) for position in positions}
        for key in list(state):
            if key not in active:
                del state[key]
        for position in positions:
            symbol = str(position.symbol).upper()
            if not _is_forex(terminal, position.symbol):
                outcomes.append(f"{symbol}: hors Forex, ignoré")
                continue
            side = "BUY" if position.type == terminal.POSITION_TYPE_BUY else "SELL"
            entry, stop = float(position.price_open), float(position.sl or 0)
            key = str(position.ticket)
            record = state.setdefault(key, {"done": []})
            if "risk" not in record:
                if not _valid_initial_stop(side, entry, stop):
                    outcomes.append(f"{symbol}: stop-loss initial requis avant le break-even")
                    continue
                record.update({"risk": abs(entry - stop), "originalVolume": float(position.volume)})
            risk = float(record["risk"])
            if not math.isfinite(risk) or risk <= 0:
                outcomes.append(f"{symbol}: risque initial invalide")
                continue
            price = _price(terminal, position, side)
            r_value = ((price - entry) / risk) if side == "BUY" else ((entry - price) / risk)
            outcomes.append(f"{symbol}: {side} · {r_value:.2f}R · TP configurés {targets}")
            for index, target_r in enumerate(targets):
                if index in record["done"] or r_value < target_r:
                    continue
                requested = float(position.volume) if index == len(targets) - 1 else float(record["originalVolume"]) * percents[index] / 100
                requested = min(requested, float(position.volume))
                amount = _close(terminal, position, side, requested)
                record["done"].append(index)
                outcomes.append(f"{symbol}: TP{index + 1} atteint à {target_r:.2f}R, {amount} fermé")
                _save_state(state)
                break
        _save_state(state)
        for line in outcomes:
            output("TP_DEMO:", line)
        return outcomes
    finally:
        terminal.shutdown()
