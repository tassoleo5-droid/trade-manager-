"""Automatic TP management for explicitly configured MT5 DEMO positions.

Only USDCAD and USDJPY positions are eligible. At TP1 it closes 50% of the
original volume; at final TP it closes the remainder. No entry order is ever sent.
Requires MYFLOWFX_DEMO_AUTO_EXIT=1 and a verified Fusion Markets DEMO terminal.
"""
import json
import math
import os
from pathlib import Path

from diagnose_fusion_demo import EXPECTED_SERVER, diagnose

STATE_FILE = Path(__file__).with_name("demo_exit_state.json")
RULES = {
    "USDCAD": {"tp1": 1.40156, "tpFinal": 1.40195, "tp1Percent": 50},
    "USDJPY": {"tp1": 157.610, "tpFinal": 157.521, "tp1Percent": 50},
}

def enabled():
    return os.environ.get("MYFLOWFX_DEMO_AUTO_EXIT") == "1"

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

def _hit(side, price, target):
    return price >= target if side == "BUY" else price <= target

def _rule_for(symbol):
    normalized = str(symbol).upper()
    for name, rule in RULES.items():
        if normalized.startswith(name):
            return name, rule
    return None, None

def _close(terminal, position, side, volume):
    info = terminal.symbol_info(position.symbol)
    if info is None:
        raise RuntimeError("Instrument indisponible")
    minimum = float(getattr(info, "volume_min", 0) or 0)
    step = float(getattr(info, "volume_step", 0) or 0)
    if minimum <= 0 or step <= 0:
        raise RuntimeError("Volume MT5 invalide")
    rounded = math.floor((volume + 1e-12) / step) * step
    rounded = round(rounded, 8)
    if rounded < minimum:
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

def manage_positions(output=print):
    if not enabled():
        return ["TP automatique désactivé"]
    if diagnose().get("status") != "demo_verified":
        raise RuntimeError("Vérification MT5 démo échouée : aucune clôture")
    import MetaTrader5 as terminal
    if not terminal.initialize():
        raise RuntimeError("Terminal MT5 indisponible : aucune clôture")
    state = _load_state()
    outcomes = []
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
        active = {str(p.ticket) for p in positions}
        for key in list(state):
            if key not in active:
                del state[key]
        for position in positions:
            symbol = str(position.symbol).upper()
            rule_name, rule = _rule_for(symbol)
            if not rule:
                outcomes.append(f"{symbol}: aucune règle TP configurée")
                continue
            side = "BUY" if position.type == terminal.POSITION_TYPE_BUY else "SELL"
            entry = float(position.price_open)
            if (side == "BUY" and not (rule["tp1"] > entry and rule["tpFinal"] > rule["tp1"])) or \
               (side == "SELL" and not (rule["tp1"] < entry and rule["tpFinal"] < rule["tp1"])):
                outcomes.append(f"{symbol}: TP incompatibles avec le sens {side}, ignoré")
                continue
            key = str(position.ticket)
            record = state.setdefault(key, {"tp1Done": False})
            price = _price(terminal, position, side)
            outcomes.append(f"{rule_name}: {side} · prix {price:.5f} · TP1 {rule['tp1']:.5f} · final {rule['tpFinal']:.5f}")
            if not record["tp1Done"] and _hit(side, price, rule["tp1"]):
                original = float(position.volume)
                amount = _close(terminal, position, side, original * rule["tp1Percent"] / 100)
                record["tp1Done"] = True
                outcomes.append(f"{symbol}: TP1 atteint, {amount} fermé")
                _save_state(state)
                continue
            if record["tp1Done"] and _hit(side, price, rule["tpFinal"]):
                amount = _close(terminal, position, side, float(position.volume))
                outcomes.append(f"{symbol}: TP final atteint, {amount} fermé")
                _save_state(state)
        _save_state(state)
        for line in outcomes:
            output("TP_DEMO:", line)
        return outcomes
    finally:
        terminal.shutdown()
