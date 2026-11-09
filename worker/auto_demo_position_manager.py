"""Account-configured automatic TP management for verified MT5 DEMO Forex positions.

Rules are received from MyFlowFX staging for the verified demo account. It can
only reduce or close existing Forex positions; it never sends entry orders.
Execution requires an explicit local opt-in and a verified demo account.
"""
import json
import math
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from diagnose_fusion_demo import EXPECTED_SERVER, diagnose

SHARED_DIR = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "MyFlowFX" / "demo-tp"
STATE_FILE = SHARED_DIR / "demo_exit_state.json"
LEGACY_STATE_FILE = Path(__file__).with_name("demo_exit_state.json")
PREVIEW_STATE_FILE = Path(__file__).with_name("demo_tp_preview_state.json")
LOCK_FILE = SHARED_DIR / "demo_exit.lock"
FOREX_CURRENCIES = {
    "AUD", "CAD", "CHF", "CNH", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF",
    "JPY", "MXN", "NOK", "NZD", "PLN", "SEK", "SGD", "TRY", "USD", "ZAR",
}

def enabled():
    """Explicit local opt-in; account checks remain mandatory before execution."""
    return os.getenv("MYFLOWFX_DEMO_AUTO_EXIT") == "1"

def _load_state():
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("État TP invalide : aucune clôture")
        return value
    except FileNotFoundError:
        if LEGACY_STATE_FILE.exists():
            raise RuntimeError("Ancien état TP détecté : vérification nécessaire avant toute clôture")
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError("État TP illisible : aucune clôture") from exc

def _save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".demo-exit-", dir=str(STATE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, STATE_FILE)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def _load_preview_state():
    try:
        value = json.loads(PREVIEW_STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_preview_state(state):
    PREVIEW_STATE_FILE.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")

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
    remainder = round(float(position.volume) - rounded, 8)
    if remainder > 0 and remainder < minimum:
        raise RuntimeError("Volume restant inférieur au minimum du broker")
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

def preview_positions(rules, output=print):
    """Read-only TP check. It never calls order_send or changes MT5."""
    verification = diagnose()
    if verification.get("status") != "demo_verified":
        raise RuntimeError("Vérification MT5 démo échouée : simulation TP indisponible")
    if not isinstance(rules, dict):
        raise RuntimeError("Réglages du compte démo absents : simulation TP indisponible")
    targets = rules["tpTargetsR"]
    percents = rules["tpPercents"]
    import MetaTrader5 as terminal
    if not terminal.initialize():
        raise RuntimeError("Terminal MT5 indisponible : simulation TP indisponible")
    try:
        positions = terminal.positions_get()
        if positions is None:
            raise RuntimeError("Positions MT5 indisponibles : simulation TP indisponible")
        output(f"TP_SIMULATION: {len(positions)} position(s) MT5 détectée(s)")
        state = _load_preview_state()
        active = {str(position.ticket) for position in positions}
        for key in list(state):
            if key not in active:
                del state[key]
        for position in positions:
            symbol = str(position.symbol).upper()
            if not _is_forex(terminal, position.symbol):
                output(f"TP_SIMULATION: {symbol}: hors Forex, ignoré")
                continue
            side = "BUY" if position.type == terminal.POSITION_TYPE_BUY else "SELL"
            entry, stop = float(position.price_open), float(position.sl or 0)
            key = str(position.ticket)
            record = state.setdefault(key, {"announced": [], "account": str(verification.get("account_login")), "entry": entry, "originalVolume": float(position.volume)})
            if "risk" not in record:
                if not _valid_initial_stop(side, entry, stop):
                    output(f"TP_SIMULATION: {symbol}: risque initial indisponible pour cette position")
                    continue
                record["risk"] = abs(entry - stop)
            risk = float(record["risk"])
            price = _price(terminal, position, side)
            r_value = ((price - entry) / risk) if side == "BUY" else ((entry - price) / risk)
            newly_reached = [
                index for index, target in enumerate(targets)
                if r_value >= target and index not in record["announced"]
            ]
            if newly_reached:
                labels = ", ".join(
                    f"TP{i + 1} ({percents[i]}% à {targets[i]:.2f}R)" for i in newly_reached
                )
                record["announced"].extend(newly_reached)
                output(f"TP_SIMULATION: {symbol}: {side} · {r_value:.2f}R · {labels} atteint · aucune clôture")
            else:
                output(f"TP_SIMULATION: {symbol}: {side} · {r_value:.2f}R · aucun nouveau TP · aucune clôture")
        _save_preview_state(state)
    finally:
        terminal.shutdown()

@contextmanager
def _execution_lock():
    """Lock the shared state across processes; OS releases it on process exit."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Un autre gestionnaire TP est déjà actif") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Un autre gestionnaire TP est déjà actif") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

def manage_positions(rules, output=print):
    if not enabled():
        return ["TP automatique désactivé"]
    with _execution_lock():
        return _manage_positions_locked(rules, output)

def _manage_positions_locked(rules, output=print):
    if not enabled():
        return ["TP automatique désactivé"]
    verification = diagnose()
    if verification.get("status") != "demo_verified":
        raise RuntimeError("Vérification MT5 démo échouée : aucune clôture")
    if not isinstance(rules, dict):
        raise RuntimeError("Réglages du compte démo absents : aucune clôture")
    targets = rules["tpTargetsR"]
    percents = rules["tpPercents"]
    import MetaTrader5 as terminal
    if not terminal.initialize():
        raise RuntimeError("Terminal MT5 indisponible : aucune clôture")
    try:
        state, outcomes = _load_state(), []
        output("TP_DEMO: analyse TP démarrée")
        account = terminal.account_info()
        if account is None or str(getattr(account, "server", "")).strip().casefold() != EXPECTED_SERVER.casefold():
            raise RuntimeError("Compte non démo détecté : aucune clôture")
        if getattr(account, "trade_mode", None) != getattr(terminal, "ACCOUNT_TRADE_MODE_DEMO", None):
            raise RuntimeError("Compte non démo détecté : aucune clôture")
        login = str(getattr(account, "login", ""))
        if not login.isdigit() or login != str(verification.get("account_login", "")):
            raise RuntimeError("Compte MT5 différent du compte vérifié : aucune clôture")
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
            if "risk" in record and record.get("account") != login:
                raise RuntimeError("État TP associé à un autre compte : aucune clôture")
            if record.get("pending"):
                outcomes.append(f"{symbol}: clôture précédente à vérifier dans MT5 ; aucune nouvelle tentative")
                continue
            if "lastVolume" in record and not math.isclose(float(position.volume), float(record["lastVolume"]), rel_tol=0, abs_tol=1e-8):
                outcomes.append(f"{symbol}: volume modifié hors du gestionnaire ; vérification nécessaire")
                continue
            if "risk" not in record:
                preview = _load_preview_state().get(key, {})
                saved_risk = preview.get("risk") if preview.get("account") == login and preview.get("entry") == entry else None
                if saved_risk is None and not _valid_initial_stop(side, entry, stop):
                    outcomes.append(f"{symbol}: stop-loss initial requis avant le break-even")
                    continue
                record.update({"account": login, "risk": saved_risk if saved_risk is not None else abs(entry - stop), "originalVolume": float(preview.get("originalVolume", position.volume)) if saved_risk is not None else float(position.volume)})
                _save_state(state)
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
                record["pending"] = {"stage": index, "volume_before": float(position.volume), "requested": requested}
                _save_state(state)
                amount = _close(terminal, position, side, requested)
                record["done"].append(index)
                del record["pending"]
                record["lastVolume"] = round(float(position.volume) - amount, 8)
                outcomes.append(f"{symbol}: TP{index + 1} atteint à {target_r:.2f}R, {amount} fermé")
                _save_state(state)
                break
        _save_state(state)
        for line in outcomes:
            output("TP_DEMO:", line)
        return outcomes
    finally:
        terminal.shutdown()
