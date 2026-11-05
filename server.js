const express = require('express');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const app = express();
const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  throw new Error('JWT_SECRET must be set to a strong secret of at least 32 characters');
}
const { DEFAULT_RULES, validateRules } = require('./rulesValidation');
const { initDemoDB, registerDemoAccountsApi } = require('./demoAccountsApi');
const { validateHeartbeat, validatePositions, verifyWorkerToken } = require('./workerLink');

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// Initialize database tables on startup
async function initDB() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        mt5_account_id VARCHAR(255),
        firstname VARCHAR(100),
        lastname VARCHAR(100),
        phone VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);
    await pool.query(`
      CREATE TABLE IF NOT EXISTS user_rules (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        rules JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
    await pool.query(`
      CREATE TABLE IF NOT EXISTS worker_heartbeat (
        id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
        last_seen TIMESTAMPTZ NOT NULL,
        demo BOOLEAN NOT NULL CHECK (demo),
        automation_active BOOLEAN NOT NULL DEFAULT FALSE,
        positions_count INTEGER NOT NULL CHECK (positions_count >= 0)
      )
    `);
    await pool.query('ALTER TABLE worker_heartbeat ADD COLUMN IF NOT EXISTS automation_active BOOLEAN NOT NULL DEFAULT FALSE');
    await pool.query(`
      CREATE TABLE IF NOT EXISTS worker_position_snapshot (
        id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
        updated_at TIMESTAMPTZ NOT NULL,
        positions JSONB NOT NULL
      )
    `);
    await initDemoDB(pool);
    console.log('Database initialized ✓');
  } catch (e) {
    console.error('Database init error:', e.message);
  }
}
initDB();

// Same-origin browser app: do not grant arbitrary websites API access.
// If a separate frontend is deployed, configure a strict allowlist instead.
app.disable('x-powered-by');
app.use(express.json({ limit: '32kb' }));

function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Non autorisé' });
  try { req.user = jwt.verify(token, JWT_SECRET); next(); }
  catch(e) { res.status(401).json({ error: 'Token invalide' }); }
}

app.post('/api/register', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ error: 'Email et mot de passe requis' });
  try {
    const existing = await pool.query('SELECT id FROM users WHERE email = $1', [email]);
    if (existing.rows.length > 0) return res.status(400).json({ error: 'Email déjà utilisé' });
    const hash = await bcrypt.hash(password, 10);
    await pool.query(
      'INSERT INTO users (email, password) VALUES ($1, $2)',
      [email, hash]
    );
    res.json({ success: true });
  } catch(e) {
    console.error('Register error:', e.message);
    res.status(500).json({ error: 'Erreur serveur' });
  }
});

app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;
  try {
    const result = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
    const user = result.rows[0];
    if (!user) return res.status(401).json({ error: 'Email ou mot de passe incorrect' });
    const valid = await bcrypt.compare(password, user.password);
    if (!valid) return res.status(401).json({ error: 'Email ou mot de passe incorrect' });
    const token = jwt.sign({ id: user.id, email: user.email }, JWT_SECRET, { expiresIn: '30d' });
    res.json({ token, email: user.email, mt5_account_id: null });
  } catch(e) {
    console.error('Login error:', e.message);
    res.status(500).json({ error: 'Erreur serveur' });
  }
});

// Legacy MetaApi registration disabled in the new demo-only branch.
app.post('/api/connect-mt5', authMiddleware, (_req,res) => {
  res.status(410).json({error:'Connexion MetaApi remplacée par /accounts'});
});

// Persistent strategy preferences. Safe until the MT5 execution worker is verified.
app.get('/api/rules', authMiddleware, async (req, res) => {
  try {
    const result = await pool.query('SELECT rules FROM user_rules WHERE user_id=$1', [req.user.id]);
    res.set('Cache-Control', 'no-store');
    res.json({ rules: result.rows[0]?.rules || DEFAULT_RULES, engine: 'not_configured' });
  } catch (e) {
    console.error('Rule read failed');
    res.status(500).json({error:'Erreur serveur'});
  }
});

app.put('/api/rules', authMiddleware, async (req, res) => {
  const validation = validateRules(req.body);
  if (validation.error) return res.status(400).json({error:validation.error});
  try {
    await pool.query(
      `INSERT INTO user_rules (user_id,rules) VALUES ($1,$2::jsonb)
       ON CONFLICT (user_id) DO UPDATE SET rules=EXCLUDED.rules,updated_at=NOW()`,
      [req.user.id, JSON.stringify(validation.rules)]
    );
    res.set('Cache-Control', 'no-store');
    res.json({rules:validation.rules,engine:'not_configured'});
  } catch(e) {
    console.error('Rule save failed');
    res.status(500).json({error:'Erreur serveur'});
  }
});

app.get('/api/engine/status', authMiddleware, async (_req, res) => {
  try {
    const [heartbeatResult, snapshotResult] = await Promise.all([
      pool.query('SELECT last_seen, demo, automation_active, positions_count FROM worker_heartbeat WHERE id = TRUE'),
      pool.query('SELECT positions FROM worker_position_snapshot WHERE id = TRUE')
    ]);
    const heartbeat = heartbeatResult.rows[0];
    const snapshot = snapshotResult.rows[0];
    const lastSeen = heartbeat?.last_seen ? new Date(heartbeat.last_seen) : null;
    const isOnline = Boolean(lastSeen && Date.now() - lastSeen.getTime() < 10 * 60 * 1000);
    res.set('Cache-Control', 'no-store');
    return res.json({
      status: isOnline ? 'online' : 'offline',
      lastSeen: lastSeen?.toISOString() || null,
      demo: heartbeat?.demo === true,
      positionsCount: heartbeat?.positions_count ?? null,
      positions: Array.isArray(snapshot?.positions) ? snapshot.positions : [],
      liveTradingEnabled: false,
      demoAutomationActive: heartbeat?.automation_active === true,
      message: isOnline
        ? (heartbeat?.automation_active === true
          ? 'Worker MT5 démo connecté : break-even automatique actif.'
          : 'Worker MT5 démo connecté en lecture seule.')
        : 'Aucun signal récent du worker MT5 démo.'
    });
  } catch (_error) {
    return res.status(503).json({ error: 'Statut du worker temporairement indisponible' });
  }
});

// Demo onboarding is completely separate from the legacy MetaApi proxy.
registerDemoAccountsApi(app, pool, authMiddleware);

// Worker rules are scoped to a verified DEMO account. They never enable entry orders.
app.get('/api/worker/rules', async (req, res) => {
  const configuredToken = process.env.WORKER_INGEST_TOKEN;
  if (!configuredToken || configuredToken.length < 32 ||
      !verifyWorkerToken(req.get('x-myflowfx-worker-token'), configuredToken)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const login = String(req.get('x-myflowfx-account-login') || '');
  const server = String(req.get('x-myflowfx-account-server') || '');
  if (!/^[0-9]{1,20}$/.test(login) || server !== 'FusionMarkets-Demo') {
    return res.status(400).json({ error: 'Invalid demo account identity' });
  }
  try {
    const result = await pool.query(
      `SELECT r.rules FROM demo_mt5_accounts a
       LEFT JOIN user_rules r ON r.user_id=a.user_id
       WHERE a.login=$1 AND a.server=$2 AND a.status='verified_demo'`,
      [login, server]
    );
    if (!result.rowCount) return res.status(403).json({ error: 'No verified demo account configuration' });
    res.set('Cache-Control', 'no-store');
    return res.json({ rules: result.rows[0].rules || DEFAULT_RULES });
  } catch (_error) {
    return res.status(503).json({ error: 'Demo rules temporarily unavailable' });
  }
});

// Read-only worker telemetry. It intentionally has no order-routing capability.
app.post('/api/worker/heartbeat', async (req, res) => {
  const configuredToken = process.env.WORKER_INGEST_TOKEN;
  if (!configuredToken || configuredToken.length < 32) {
    return res.status(503).json({ error: 'Worker link not configured' });
  }
  if (!verifyWorkerToken(req.get('x-myflowfx-worker-token'), configuredToken)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const payload = validateHeartbeat(req.body);
  if (!payload) return res.status(400).json({ error: 'Invalid read-only heartbeat' });
  try {
    await pool.query(
      `INSERT INTO worker_heartbeat (id, last_seen, demo, automation_active, positions_count)
       VALUES (TRUE, NOW(), $1, $2, $3)
       ON CONFLICT (id) DO UPDATE
       SET last_seen = EXCLUDED.last_seen, demo = EXCLUDED.demo,
           automation_active = EXCLUDED.automation_active,
           positions_count = EXCLUDED.positions_count`,
      [payload.demo, payload.automation, payload.positionsCount]
    );
    res.set('Cache-Control', 'no-store');
    return res.status(202).json({ status: 'accepted', execution: payload.automation ? 'demo_break_even' : 'disabled' });
  } catch (_error) {
    return res.status(503).json({ error: 'Worker status storage unavailable' });
  }
});

app.post('/api/worker/positions', async (req, res) => {
  const configuredToken = process.env.WORKER_INGEST_TOKEN;
  if (!configuredToken || configuredToken.length < 32) {
    return res.status(503).json({ error: 'Worker link not configured' });
  }
  if (!verifyWorkerToken(req.get('x-myflowfx-worker-token'), configuredToken)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const positions = validatePositions(req.body);
  if (!positions) return res.status(400).json({ error: 'Invalid read-only positions' });
  try {
    await pool.query(
      `INSERT INTO worker_position_snapshot (id, updated_at, positions)
       VALUES (TRUE, NOW(), $1::jsonb)
       ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at, positions = EXCLUDED.positions`,
      [JSON.stringify(positions)]
    );
    res.set('Cache-Control', 'no-store');
    return res.status(202).json({ status: 'accepted', execution: 'disabled' });
  } catch (_error) {
    return res.status(503).json({ error: 'Position storage unavailable' });
  }
});

// Fail closed: no broker orders while the new Windows worker is being verified.
app.post('/api/trade', authMiddleware, (_req,res) => {
  res.status(503).json({error:'Automatisation désactivée pendant les tests démo'});
});

app.get('/accounts', (_req,res) => {
  res.sendFile(path.join(__dirname,'public','accounts.html'));
});

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'landing.html'));
});

app.get('/app', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.use(express.static('public'));

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'landing.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`TradeFlow running on port ${PORT}`));
