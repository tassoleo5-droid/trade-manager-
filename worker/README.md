# Windows MT5 connector — Phase 1 (read-only)

This adapter is deliberately **not** connected to Railway or browser login fields yet.
It connects to the MT5 desktop terminal on Windows using a broker account's login,
server, and password, and inspects positions without submitting any trade orders.

## Local DEMO test on Windows
1. Install MetaTrader 5 and ensure broker server is available.
2. Install Python and `pip install MetaTrader5`.
3. Provide `MT5_LOGIN`, `MT5_SERVER`, `MT5_PASSWORD` in your Windows process environment (never in Git or a command line argument).
4. Run `python worker/mt5_adapter.py` from the repository root.
5. Run unit tests with `cd worker && python -m unittest discover -s tests -v`.

Do not use live account credentials before the backend's secret storage,
worker identity, encrypted transport, and explicit user authorization are
implemented and independently tested.

## Next implementation gates
- Authenticated Railway -> Windows worker communication.
- AES-256-GCM encrypted account credentials stored on Railway with a dedicated key.
- Per-user account authorization and revoke/delete.
- Engine job persistence, per-position locking, idempotency & broker confirmation.
- Demo-only activation of position modify/partial close before live rollout.
- Healthchecks, restart recovery, audit trail, worker monitoring.
