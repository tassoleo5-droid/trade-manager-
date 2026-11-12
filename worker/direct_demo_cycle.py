"""A single, explicitly enabled demo management cycle."""
import os
from pathlib import Path
from sync_demo_rules import read_demo_identity, validate_rules_response
from direct_demo_manager import manage


def run_cycle(mt5, terminal_path, api_post, origin, token, worker_id, state_path):
    auto_be = os.getenv("MYFLOWFX_DEMO_AUTO_BREAK_EVEN") == "1"
    auto_tp = os.getenv("MYFLOWFX_DEMO_AUTO_EXIT") == "1"
    allowed_login = os.getenv("MYFLOWFX_DEMO_MANAGE_ACCOUNT", "")
    if not (auto_be or auto_tp):
        return ["Gestion automatique démo désactivée"]
    if not allowed_login.isdigit():
        raise RuntimeError("Compte démo local non configuré")
    identity = read_demo_identity(mt5, terminal_path)
    if identity["login"] != allowed_login:
        raise RuntimeError("Compte connecté différent du compte autorisé")
    response = api_post(origin, "/api/demo/worker/rules", token, worker_id, identity)
    rules = validate_rules_response(response, identity)
    if not mt5.initialize(path=terminal_path, portable=True, timeout=30000):
        raise RuntimeError("Terminal MT5 indisponible")
    try:
        return manage(mt5, identity, rules, Path(state_path), auto_be=auto_be, auto_tp=auto_tp)
    finally:
        mt5.shutdown()
