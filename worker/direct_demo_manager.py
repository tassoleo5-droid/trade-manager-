"""Demo-only MT5 position management. No opening orders.

The caller must supply validated account-scoped rules and explicitly activate
the desired actions. The state store persists original risk and pending orders.
"""
import math
import os
import tempfile
from pathlib import Path
import json
import time
from contextlib import contextmanager


@contextmanager
def execution_lock(state_path):
    lock_path = Path(str(state_path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Un autre gestionnaire est déjà actif") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Un autre gestionnaire est déjà actif") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def save_state(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".myflowfx-")
    try:
        with os.fdopen(fd, "w", encoding="utf8") as f:
            json.dump(state, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_state(path):
    try:
        with open(path, encoding="utf8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError("bad state")
        return state
    except FileNotFoundError:
        return {}
    except (ValueError, OSError) as exc:
        raise RuntimeError("État de gestion indisponible") from exc


def checked_account(mt5, login, server):
    account, terminal = mt5.account_info(), mt5.terminal_info()
    demo = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    if (type(demo) is not int or account is None or terminal is None
            or not getattr(terminal, "connected", False)
            or getattr(account, "trade_mode", None) != demo
            or str(getattr(account, "login", "")) != str(login)
            or str(getattr(account, "server", "")).casefold() != server.casefold()):
        raise RuntimeError("Compte MT5 démo non vérifié")


def finite_price(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def position_is_unchanged(mt5, pos, *, check_stop=False):
    current = mt5.positions_get(ticket=pos.ticket)
    if current is None or len(current) != 1:
        return False
    now = current[0]
    if (now.symbol != pos.symbol or now.type != pos.type or
            not math.isclose(float(now.volume), float(pos.volume), abs_tol=1e-8, rel_tol=0) or
            not math.isclose(float(now.price_open), float(pos.price_open), abs_tol=1e-10, rel_tol=0)):
        return False
    if check_stop and (float(now.sl or 0) != float(pos.sl or 0) or
                       float(now.tp or 0) != float(pos.tp or 0)):
        return False
    return True


def manage(mt5, identity, rules, state_path, *, auto_be=False, auto_tp=False):
    """Run one demo cycle. The caller owns the dedicated MT5 session."""
    with execution_lock(state_path):
        return _manage_locked(mt5, identity, rules, state_path, auto_be=auto_be, auto_tp=auto_tp)


def _manage_locked(mt5, identity, rules, state_path, *, auto_be=False, auto_tp=False):
    login, server = str(identity["login"]), str(identity["server"])
    checked_account(mt5, login, server)
    positions = mt5.positions_get()
    if positions is None:
        raise RuntimeError("Positions MT5 indisponibles")
    state = load_state(state_path)
    outcomes = []
    for pos in positions:
        if pos.type not in (mt5.POSITION_TYPE_BUY, mt5.POSITION_TYPE_SELL):
            continue
        side = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
        entry, stop = finite_price(pos.price_open), finite_price(pos.sl)
        volume = finite_price(pos.volume)
        tick = mt5.symbol_info_tick(pos.symbol)
        price = finite_price(getattr(tick, "bid" if side == "BUY" else "ask", None))
        tick_time = finite_price(getattr(tick, "time", None))
        info = mt5.symbol_info(pos.symbol)
        if (not entry or not volume or not price or info is None or not tick_time
                or time.time() - tick_time > 15 or tick_time - time.time() > 5):
            outcomes.append("Données de position indisponibles")
            continue
        key = f"{server.casefold()}:{login}:{pos.ticket}"
        record = state.get(key)
        if record is None:
            if not stop or not ((side == "BUY" and stop < entry) or (side == "SELL" and stop > entry)):
                outcomes.append("Stop-loss initial indisponible")
                continue
            record = {"entry": entry, "risk": abs(entry-stop), "original": volume,
                      "last_volume": volume, "done": [], "pending": None}
            state[key] = record
            save_state(state_path, state)
        if record.get("entry") != entry or record.get("pending"):
            outcomes.append("Position à vérifier avant nouvelle action")
            continue
        if not math.isclose(volume, float(record["last_volume"]), abs_tol=1e-8, rel_tol=0):
            outcomes.append("Volume modifié : vérification nécessaire")
            continue
        risk = finite_price(record.get("risk"))
        if risk is None:
            raise RuntimeError("Risque initial invalide")
        r_value = (price-entry)/risk if side == "BUY" else (entry-price)/risk
        if auto_be and r_value >= rules["beThreshold"]:
            # Never worsen an existing stop.
            improve = stop is not None and ((side == "BUY" and stop < entry) or (side == "SELL" and stop > entry))
            if improve:
                checked_account(mt5, login, server)
                if not position_is_unchanged(mt5, pos, check_stop=True):
                    outcomes.append("Position modifiée : break-even reporté")
                    continue
                result = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket,
                                         "symbol": pos.symbol, "sl": entry, "tp": float(pos.tp or 0)})
                if result is None or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
                    outcomes.append("Modification du stop-loss refusée")
                else:
                    outcomes.append("Break-even effectué")
        if not auto_tp:
            continue
        targets, percents = rules["tpTargetsR"], rules["tpPercents"]
        active_targets = {"targets": list(targets), "percents": list(percents)}
        if record["done"] and record.get("tp_rules") != active_targets:
            outcomes.append("Réglages TP modifiés après clôture : vérification nécessaire")
            continue
        if not record["done"] and record.get("tp_rules") != active_targets:
            record["tp_rules"] = active_targets
            save_state(state_path, state)
        for index, target in enumerate(targets):
            if index in record["done"] or r_value < target:
                continue
            desired = volume if index == len(targets)-1 else min(volume, record["original"]*percents[index]/100)
            step, minimum = finite_price(info.volume_step), finite_price(info.volume_min)
            if step is None or minimum is None:
                outcomes.append("Volume minimum indisponible")
                break
            requested = round(math.floor((desired + 1e-12)/step)*step, 8)
            remainder = round(volume-requested, 8)
            if requested < minimum or (remainder > 1e-8 and remainder < minimum):
                outcomes.append("Volume de clôture non compatible")
                break
            record["pending"] = {"tp": index, "volume_before": volume, "requested": requested}
            save_state(state_path, state)
            checked_account(mt5, login, server)
            if not position_is_unchanged(mt5, pos):
                record["pending"] = None
                save_state(state_path, state)
                outcomes.append("Position modifiée : clôture reportée")
                break
            result = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "position": pos.ticket,
                "symbol": pos.symbol, "volume": requested,
                "type": mt5.ORDER_TYPE_SELL if side == "BUY" else mt5.ORDER_TYPE_BUY,
                "price": price, "deviation": 20, "type_filling": mt5.ORDER_FILLING_IOC,
                "comment": "MyFlowFX DEMO TP"})
            if result is None or getattr(result, "retcode", None) != mt5.TRADE_RETCODE_DONE:
                outcomes.append("Clôture à vérifier : aucune nouvelle tentative")
                break
            # A success response alone is insufficient: verify the remaining position volume.
            fresh = mt5.positions_get(ticket=pos.ticket)
            if fresh is None or (len(fresh) > 1):
                outcomes.append("Résultat de clôture à vérifier")
                break
            actual = float(fresh[0].volume) if fresh else 0.0
            if not math.isclose(actual, remainder, abs_tol=1e-8, rel_tol=0):
                outcomes.append("Volume après clôture à vérifier")
                break
            record["last_volume"] = actual
            record["done"].append(index)
            record["pending"] = None
            save_state(state_path, state)
            outcomes.append(f"TP{index+1} effectué")
            break
    return outcomes
