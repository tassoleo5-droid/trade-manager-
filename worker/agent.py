"""MyFlowFX demo verification agent.

For a centrally managed Windows host with the MetaTrader 5 terminal installed.
This agent is read-only and cannot place, modify, or close trades.

Only connect to a trusted HTTPS Railway deployment. Set:
MYFLOWFX_API_URL, MYFLOWFX_WORKER_TOKEN, MYFLOWFX_WORKER_ID and
MYFLOWFX_MT5_TERMINAL_PATH (a dedicated portable MT5 installation).
"""
import json
import ntpath
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from mt5_adapter import AccountConfig, inspect_connection, LiveAccountError
from sync_demo_rules import fetch_rules

class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects with worker authorization or broker credentials."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


HTTPS_OPENER = urllib.request.build_opener(NoRedirect)



def validate_agent_config(api_url, token, worker_id):
    parsed = urllib.parse.urlsplit(api_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("MYFLOWFX_API_URL must be the origin of an HTTPS service")
    if not isinstance(token, str) or len(token) < 32 or any(ord(c) < 33 for c in token):
        raise ValueError("MYFLOWFX_WORKER_TOKEN must be a long secret")
    if not isinstance(worker_id, str) or not (3 <= len(worker_id) <= 64) or not all(c.isalnum() or c in "_-" for c in worker_id):
        raise ValueError("MYFLOWFX_WORKER_ID is invalid")


def api_post(origin, route, token, worker_id, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        origin.rstrip("/") + route,
        data=data, method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "X-Worker-ID": worker_id,
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
    )
    try:
        with HTTPS_OPENER.open(request, timeout=25) as response:
            if response.status == 204:
                return None
            return json.loads(response.read(16_384).decode("utf-8"))
    except urllib.error.HTTPError as e:
        # No response bodies or credentials in logs.
        raise RuntimeError("Worker API returned HTTP " + str(e.code)) from None


def verify_job(job, terminal=None, terminal_path=None):
    """No order_send calls. Only inspect a DEMO account and its open positions."""
    try:
        config = AccountConfig(
            login=int(job["login"]),
            server=job["server"],
            password=job["password"],
        )
        state = inspect_connection(config, terminal, terminal_path=terminal_path)
        if not state["demo_verified"]:
            return {
                "jobId": job["jobId"], "result": "rejected_live"
            }
        return {
            "jobId": job["jobId"], "result": "verified_demo",
            "accountLogin": state["login"],
        }
    except LiveAccountError:
        return {"jobId": job["jobId"], "result": "rejected_live"}
    except RuntimeError as exc:
        code = "ACCOUNT_MISMATCH" if "different account" in str(exc) else "TERMINAL_UNAVAILABLE"
        return {"jobId": job["jobId"], "result": "failed", "errorCode": code}
    except (KeyError, ValueError, TypeError):
        return {"jobId": job.get("jobId"), "result": "failed", "errorCode": "UNKNOWN"}


def validate_terminal_path(path):
    if not isinstance(path, str) or not ntpath.isabs(path) or ntpath.basename(path).lower() != "terminal64.exe":
        raise ValueError("Dedicated MT5 terminal64.exe path required")


def run_forever(api_url, token, worker_id, terminal_path):
    validate_agent_config(api_url, token, worker_id)
    validate_terminal_path(terminal_path)
    print("MyFlowFX DEMO verification worker started (READ ONLY)")
    last_rules = None
    next_sync = 0
    while True:
        try:
            job = api_post(api_url, "/api/demo/worker/claim", token, worker_id, {})
            if job:
                # The broker password is never displayed, written to disk, or put
                # in process command-line arguments.
                result = verify_job(job, terminal_path=terminal_path)
                api_post(api_url, "/api/demo/worker/result", token, worker_id, result)
                del job
            if time.monotonic() >= next_sync:
                # This connection is read-only. No orders or position changes.
                next_sync = time.monotonic() + 30
                import MetaTrader5 as terminal
                rules = fetch_rules(terminal, terminal_path, api_post, api_url, token, worker_id)
                if rules != last_rules:
                    print("Réglages du compte démo synchronisés (lecture seule).")
                    last_rules = rules
        except (RuntimeError, OSError, ValueError, ImportError) as exc:
            print("Worker cycle failed (" + type(exc).__name__ + "); retrying")
        time.sleep(5)


if __name__ == "__main__":
    run_forever(
        os.environ.get("MYFLOWFX_API_URL", ""),
        os.environ.get("MYFLOWFX_WORKER_TOKEN", ""),
        os.environ.get("MYFLOWFX_WORKER_ID", "demo-worker-01"),
        os.environ.get("MYFLOWFX_MT5_TERMINAL_PATH", ""),
    )
