"""MyFlowFX staging heartbeat from a Fusion Markets MT5 DEMO terminal.

Sends only {demo: true, positionsCount: integer}. It never sends credentials,
account identifiers, prices, P&L, or order details, and cannot place trades.
Configure MYFLOWFX_STAGING_URL and MYFLOWFX_WORKER_TOKEN in the VPS session.
"""
import json
import os
import urllib.error
import urllib.request

from diagnose_fusion_demo import diagnose

MAX_TOKEN_LENGTH = 512

def settings(environ=os.environ):
    base_url = environ.get("MYFLOWFX_STAGING_URL", "").strip().rstrip("/")
    token = environ.get("MYFLOWFX_WORKER_TOKEN", "")
    if not base_url.startswith("https://") or len(base_url) > 200:
        raise RuntimeError("MYFLOWFX_STAGING_URL must be an HTTPS staging URL")
    if not (32 <= len(token) <= MAX_TOKEN_LENGTH):
        raise RuntimeError("MYFLOWFX_WORKER_TOKEN must be configured locally")
    return base_url, token

def build_payload(check=diagnose):
    result = check()
    if result.get("status") != "demo_verified":
        raise RuntimeError("MT5 demo verification failed; heartbeat not sent")
    count = result.get("positions_count")
    if type(count) is not int or count < 0:
        raise RuntimeError("MT5 returned an invalid position count")
    return {"demo": True, "positionsCount": count}

def report(opener=urllib.request.urlopen, environ=os.environ, check=diagnose):
    base_url, token = settings(environ)
    payload = json.dumps(build_payload(check), separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/api/worker/heartbeat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-MyFlowFX-Worker-Token": token,
        },
        method="POST",
    )
    try:
        with opener(request, timeout=10) as response:
            if response.status != 202:
                raise RuntimeError("Staging rejected the read-only heartbeat")
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Staging rejected the read-only heartbeat") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Staging endpoint unavailable") from exc
    return "accepted"

if __name__ == "__main__":
    try:
        print("STAGING_HEARTBEAT:", report())
        print("Lecture seule confirmée : aucun ordre envoyé.")
    except RuntimeError as exc:
        print("STAGING_HEARTBEAT: not_sent")
        print(str(exc))
