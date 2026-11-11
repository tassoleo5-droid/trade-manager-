"""MyFlowFX isolated MT5 diagnostic worker.

Run ONLY on a Windows host with a MetaTrader 5 terminal installed.
No orders are sent by this module. Never pass broker credentials in CLI flags.
"""
import os
from dataclasses import dataclass
from typing import Any, Optional


class LiveAccountError(RuntimeError):
    pass


@dataclass(frozen=True)
class AccountConfig:
    login: int
    server: str
    password: str

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("MT5_LOGIN", "")
        server = os.environ.get("MT5_SERVER", "").strip()
        password = os.environ.get("MT5_PASSWORD", "")
        if not raw.isdecimal() or not (0 < int(raw) < 2**63):
            raise ValueError("MT5_LOGIN must be a positive numeric account ID")
        if not server or len(server) > 200 or any(ord(c) < 32 for c in server):
            raise ValueError("MT5_SERVER is invalid")
        if not password:
            raise ValueError("MT5_PASSWORD is required")
        return cls(login=int(raw), server=server, password=password)


def inspect_connection(config: AccountConfig, terminal: Optional[Any] = None, terminal_path: Optional[str] = None) -> dict:
    """Read-only connectivity test; does not submit or modify trades."""
    if terminal is None:
        try:
            import MetaTrader5 as terminal
        except ImportError as exc:
            raise RuntimeError("Install MetaTrader5 package on Windows") from exc

    options = dict(login=config.login, password=config.password, server=config.server, timeout=30000)
    if terminal_path:
        options.update(path=terminal_path, portable=True)
    if not terminal.initialize(**options):
        # Do not log terminal errors verbatim as they can include environment data.
        raise RuntimeError("MT5 terminal initialization failed; check broker login, server, or Windows terminal")
    try:
        account = terminal.account_info()
        if account is None:
            raise RuntimeError("MT5 connected but account info unavailable")
        if int(account.login) != config.login:
            raise RuntimeError("MT5 returned a different account login")
        if str(account.server).casefold() != config.server.casefold():
            raise RuntimeError("MT5 returned a different account server")
        demo_mode = getattr(terminal, "ACCOUNT_TRADE_MODE_DEMO", None)
        if not isinstance(demo_mode, int) or getattr(account, "trade_mode", None) != demo_mode:
            raise LiveAccountError("Only verified demo MT5 accounts may be used")
        positions = terminal.positions_get()
        if positions is None:
            raise RuntimeError("MT5 positions unavailable")
        return {
            "connected": True,
            "login": str(account.login),
            "server": str(account.server),
            "currency": str(account.currency),
            "positions_count": len(positions),
            "demo_verified": True,
            "trading_actions_enabled": False,
        }
    finally:
        terminal.shutdown()


if __name__ == "__main__":
    # Intentionally read-only. Never print passwords, equity, or full positions.
    import json
    status = inspect_connection(AccountConfig.from_environment())
    print(json.dumps(status))
