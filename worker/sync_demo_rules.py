"""Read-only account-scoped rules synchronization for a connected demo terminal."""
import math


def read_demo_identity(terminal, terminal_path):
    if not terminal.initialize(path=terminal_path, portable=True, timeout=30000):
        raise RuntimeError("Terminal MT5 indisponible")
    try:
        account = terminal.account_info()
        info = terminal.terminal_info()
        if (account is None or info is None or not getattr(info, "connected", False)
                or getattr(account, "trade_mode", None) != terminal.ACCOUNT_TRADE_MODE_DEMO):
            raise RuntimeError("Compte démo connecté non vérifié")
        login = str(getattr(account, "login", ""))
        server = str(getattr(account, "server", "")).strip()
        if not login.isdigit() or not server:
            raise RuntimeError("Identité MT5 indisponible")
        return {"login": login, "server": server}
    finally:
        terminal.shutdown()


def validate_rules_response(response, identity):
    if not isinstance(response, dict) or response.get("executionEnabled") is not False:
        raise RuntimeError("Réglages reçus invalides")
    if (response.get("login") != identity["login"] or
            str(response.get("server", "")).casefold() != identity["server"].casefold()):
        raise RuntimeError("Réglages associés à un autre compte")
    rules = response.get("rules")
    if not isinstance(rules, dict) or rules.get("enabled") is not False:
        raise RuntimeError("Réglages démo invalides")
    count, levels, percents = rules.get("tpCount"), rules.get("tpTargetsR"), rules.get("tpPercents")
    threshold = rules.get("beThreshold")
    if (type(count) is not int or count not in (1, 2, 3) or
        not isinstance(levels, list) or not isinstance(percents, list) or
        len(levels) != count or len(percents) != count or
        type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0.1 <= threshold <= 10 or
        any(type(x) is not int or x <= 0 or x > 100 for x in percents) or sum(percents) != 100 or
        any(type(x) not in (int, float) or not math.isfinite(x) or x < 0.1 or x > 30 for x in levels) or
        any(levels[i] <= levels[i-1] for i in range(1, count))):
        raise RuntimeError("Réglages de gestion invalides")
    return rules


def fetch_rules(terminal, terminal_path, api_post, origin, token, worker_id):
    identity = read_demo_identity(terminal, terminal_path)
    result = api_post(origin, "/api/demo/worker/rules", token, worker_id, identity)
    return validate_rules_response(result, identity)
