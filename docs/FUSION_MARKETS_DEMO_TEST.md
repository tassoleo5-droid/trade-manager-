# Fusion Markets — MyFlowFX MT5 DEMO acceptance run

## Broker / account
- Broker: Fusion Markets
- Platform: MetaTrader 5 (not MT4)
- Server: `FusionMarkets-Demo` **only if this exact name appears in the Fusion Markets account confirmation or client hub**.
- Account login: enter only in the authenticated MyFlowFX form once a separate, secured staging site is ready.
- Password: never paste it into GitHub, chat, source code, Railway logs or a CLI command.
- Fusion Markets states demo accounts generally expire 30 days after creation. Ensure the test window is within the expiry.

Broker source: https://fusionmarkets.com/FAQ

## Phase A — manual connectivity (no broker orders via MyFlowFX)
1. Confirm the user's account was created as an **MT5** account, not MT4.
2. Log in to Fusion Markets' MT5 terminal (Mac/mobile is fine for this user-side check), using the account's specific login, server and MT5 trading password.
3. Check that MT5 shows a demo account, correct account number and an active connection. Do not supply any credentials to ChatGPT.
4. Set up a **separate Railway staging environment and database**; never point testing at the production Postgres.
5. Configure `JWT_SECRET` (32+ characters), `MYFLOWFX_CREDENTIAL_KEY` (32 random bytes encoded as base64), and `MYFLOWFX_WORKER_TOKEN` (distinct random value, 32+ chars) in the staging secrets manager.
6. Deploy the development branch to staging *only after* security checks and authentication hardening.
7. Connect a Windows MT5 worker and make sure the worker reports `verified_demo`. Verify the worker refuses any real account and never sends orders.

## Phase B — demo-only execution integration (NOT IMPLEMENTED YET)
- Manually open a small 0.01-lot position in the Fusion Markets MT5 demo with an initial SL.
- Worker must record initial entry, SL, current lot volume, tick size, lot step and position ticket.
- Validate BE at configured R, SL never worsens, TP1/TP2/TP3 ordered and broker result confirmation.
- Validate price gaps, broker freeze zones, volume normalization, no duplicate orders after network interruptions or restarts.
- Confirm server-side stop/resume and that user closing the website never suspends active management.
- Test account deletion immediately stops any new trading action and clears credentials.
- No automatic live trading until full external review.

## Operational blocker
Railway provides Linux runtime services. For the chosen direct MT5 Python adapter, supply a dedicated Windows VPS with MetaTrader 5 terminal and isolated account processes. Do not commit live credentials or assume a single terminal supports a fleet of accounts.
