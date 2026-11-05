"""Send a minimal read-only snapshot of MT5 DEMO positions to MyFlowFX staging."""
import json
import math
import urllib.error
import urllib.request

from diagnose_fusion_demo import EXPECTED_SERVER, diagnose
from report_demo_heartbeat import settings

def snapshot_positions():
    if diagnose().get("status") != "demo_verified":
        raise RuntimeError("MT5 demo verification failed; positions not sent")
    import MetaTrader5 as terminal
    if not terminal.initialize():
        raise RuntimeError("MT5 terminal unavailable")
    try:
        account = terminal.account_info()
        if account is None or str(getattr(account, "server", "")).strip().casefold() != EXPECTED_SERVER.casefold():
            raise RuntimeError("MT5 demo verification failed; positions not sent")
        positions = terminal.positions_get()
        if positions is None:
            raise RuntimeError("MT5 positions unavailable")
        buy_type = terminal.POSITION_TYPE_BUY
        snapshot = []
        for position in positions:
            side = "BUY" if position.type == buy_type else "SELL"
            current_price = float(getattr(position, "price_current", 0) or 0)
            if not math.isfinite(current_price) or current_price <= 0:
                tick = terminal.symbol_info_tick(position.symbol)
                current_price = float(
                    getattr(tick, "ask" if side == "BUY" else "bid", 0) or 0
                )
            if not math.isfinite(current_price) or current_price <= 0:
                raise RuntimeError("Prix actuel indisponible; positions non envoyées")
            snapshot.append({
                "id": str(position.ticket),
                "symbol": str(position.symbol).upper(),
                "side": side,
                "volume": float(position.volume),
                "openPrice": float(position.price_open),
                "currentPrice": current_price,
                "stopLoss": float(position.sl or 0),
            })
        return {"positions": snapshot}
    finally:
        terminal.shutdown()

def report_positions(opener=urllib.request.urlopen):
    base_url, token = settings()
    payload = json.dumps(snapshot_positions(), separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/api/worker/positions", data=payload,
        headers={"Content-Type": "application/json", "X-MyFlowFX-Worker-Token": token},
        method="POST"
    )
    try:
        with opener(request, timeout=10) as response:
            if response.status != 202:
                raise RuntimeError("Staging rejected the read-only positions")
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Staging rejected the read-only positions") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Staging endpoint unavailable") from exc
    return "accepted"

if __name__ == "__main__":
    try:
        print("STAGING_POSITIONS:", report_positions())
        print("Lecture seule confirmée : aucun ordre envoyé.")
    except RuntimeError as exc:
        print("STAGING_POSITIONS: not_sent")
        print(str(exc))
