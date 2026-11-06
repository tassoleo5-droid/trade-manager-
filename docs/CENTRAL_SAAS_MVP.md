# MyFlowFX — central MT5 demo onboarding MVP (November 2026)

## Design goal
Clients use Mac, Windows, iOS, or Android, with **no personal VPS**. They open
positions manually in MT5. MyFlowFX will manage those existing positions based
on their preferences once the execution engine has passed the demo validation
program. MyFlowFX must NOT open new trades.

## Implemented in the development branch
- Railway/Express: authenticated demo-account registration, list, deletion.
- Per-user broker credential storage encrypted using AES-256-GCM with user/account
  context, random nonce and integrity tag.
- Database-backed verification queue with row locks, worker claims, leases,
  attempt limits and constrained result states.
- HTTPS-only diagnostic agent that connects to Windows MetaTrader 5, verifies
  the expected login, ensures DEMO trade mode, and reads position count.
- Server-saved break-even and TP split preferences. Engine is explicitly
  disabled.
- `/accounts` UI for account management and saved trading rules.
- Legacy MetaApi trading endpoints disabled on this branch.
- Automated tests for credential encryption, request input, MT5 connection,
  read-only break-even and TP planning.

## NOT implemented / NOT ready for production
- No Windows VPS has been provisioned, so the bridge cannot connect to a real
  terminal from this environment.
- No live position observation loop or per-account terminal isolation.
- No execution (TP partial closes/SL changes) via MT5, broker order
  confirmation, recovery or incident alerts.
- No persistent per-position initial risk capture, order idempotency runner,
  stop/freeze checks, or synchronization across broker restarts.
- No billing/subscriptions, account tier limits, alert delivery, security review,
  load test or broker/prop-firm approval.
- Legacy main branch on Railway is unchanged. **DO NOT MERGE** until reviewed.

## Railway secrets required BEFORE deploying new branch
Generate locally or in a secure secret manager. Do NOT commit credentials,
paste them in chat, or put them in frontend JavaScript.

- `DATABASE_URL`: a Railway PostgreSQL URL.
- `JWT_SECRET`: existing strong random signing secret (>=32 chars).
- `MYFLOWFX_CREDENTIAL_KEY`: independently generated 32 random bytes,
  encoded as standard base64 (e.g. `openssl rand -base64 32`).
- `MYFLOWFX_WORKER_TOKEN`: independent random token of 32+ chars
  (e.g. `openssl rand -hex 32`). Must match on worker, treat as sensitive.

**Keep encryption keys backed up in a secure vault**: losing the key makes
stored broker credentials undecryptable. Rotating requires controlled
re-encryption and careful rollback strategy.

## Central Windows worker configuration
Run `worker/agent.py` on a secured Windows VPS with MT5 installed and Python
`MetaTrader5` package available. Worker env:
- `MYFLOWFX_API_URL=https://<exact Railway service origin>`
- `MYFLOWFX_WORKER_TOKEN=<same secret as on Railway>`
- `MYFLOWFX_WORKER_ID=<unique worker identity>`

No credentials are accepted on the worker CLI. Worker receives temporary
passwords over TLS, uses them in memory, checks DEMO status and posts results.
It cannot send orders by design. Use one trusted worker while validating; do
not confuse this diagnostic queue with multi-user production execution.

## Local tests
- Node: `npm test` and `node --check server.js`.
- Python mocks (no Windows/MT5 required):
  `cd worker && python -m unittest discover -s tests -v`.
- The GitHub Actions workflow runs both suites on pull requests.

## Demo acceptance gates before enabling automation
1. Account creation, deletion, and ownership isolation confirmed.
2. Live broker account detected and rejected, with password erased.
3. Wrong credentials handled without leaking secrets.
4. Worker disconnections and expired leases recovered.
5. Manual MT5 position opened on demo; initial SL and volume snapshotted.
6. BE rule is correct for buy and sell, including gaps/slippage.
7. TP1/TP2/TP3 on different broker lot steps confirmed from history.
8. Reconnect/restart cannot execute the same partial close twice.
9. Read-only investor password is rejected for trading operations.
10. Kill switch persists across browser and worker restart, with audit trail.
11. Parallel users and multiple isolated MT5 terminals tested.
12. Independent security review and broker/prop-firm terms reviewed.

Only after all checks pass may a separately authorized demo execution engine
be introduced. Live account support requires a distinct formal launch review.
