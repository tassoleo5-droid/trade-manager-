"""Dedicated, explicitly enabled demo management process.

This process never verifies or logs into other accounts. It must use its own
portable terminal directory, distinct from the account-verification terminal.
"""
import ntpath
import os
import time
from agent import api_post, validate_agent_config, validate_terminal_path
from direct_demo_cycle import run_cycle


def validate_config(api_url, token, worker_id, terminal_path, verifier_path, account):
    validate_agent_config(api_url, token, worker_id)
    validate_terminal_path(terminal_path)
    validate_terminal_path(verifier_path)
    if ntpath.normcase(ntpath.normpath(terminal_path)) == ntpath.normcase(ntpath.normpath(verifier_path)):
        raise ValueError("Le terminal de gestion doit être distinct du terminal de vérification")
    if not account.isdigit():
        raise ValueError("Compte démo local non configuré")
    if not (os.getenv("MYFLOWFX_DEMO_AUTO_BREAK_EVEN") == "1" or
            os.getenv("MYFLOWFX_DEMO_AUTO_EXIT") == "1"):
        raise ValueError("Gestion automatique démo désactivée")


def run():
    api_url = os.getenv("MYFLOWFX_API_URL", "")
    token = os.getenv("MYFLOWFX_WORKER_TOKEN", "")
    worker_id = os.getenv("MYFLOWFX_WORKER_ID", "demo-manager-01")
    terminal_path = os.getenv("MYFLOWFX_MT5_TERMINAL_PATH", "")
    verifier_path = os.getenv("MYFLOWFX_VERIFIER_TERMINAL_PATH", "")
    account = os.getenv("MYFLOWFX_DEMO_MANAGE_ACCOUNT", "")
    validate_config(api_url, token, worker_id, terminal_path, verifier_path, account)
    import MetaTrader5 as terminal
    state_path = os.path.join(os.getenv("LOCALAPPDATA") or os.path.expanduser("~"),
                              "MyFlowFX", "direct-demo", account, "management-state.json")
    print("Gestion MT5 démo démarrée ; ouverture automatique désactivée.")
    previous = None
    while True:
        try:
            outcome = run_cycle(terminal, terminal_path, api_post, api_url, token, worker_id, state_path)
            if outcome != previous:
                for line in outcome:
                    print("GESTION_DEMO:", line, flush=True)
                previous = outcome
        except (RuntimeError, OSError, ValueError) as exc:
            message = "Gestion démo interrompue (" + type(exc).__name__ + ")."
            if previous != [message]:
                print(message, flush=True)
                previous = [message]
        time.sleep(2)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Gestion démo arrêtée.")
