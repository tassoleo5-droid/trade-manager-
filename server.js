const express = require('express');
const fetch = require('node-fetch');
const cors = require('cors');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const app = express();
const META_API = 'https://mt-client-api-v1.london.agiliumtrade.ai';
const METAAPI_TOKEN = process.env.METAAPI_TOKEN;
const JWT_SECRET = process.env.JWT_SECRET || 'trademanager_secret_2024';

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
    console.log('Database initialized ✓');
  } catch (e) {
    console.error('Database init error:', e.message);
  }
}
initDB();

app.use(cors());
app.use(express.json());

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
    res.json({ token, email: user.email, mt5_account_id: user.mt5_account_id });
  } catch(e) {
    console.error('Login error:', e.message);
    res.status(500).json({ error: 'Erreur serveur' });
  }
});

app.post('/api/connect-mt5', authMiddleware, async (req, res) => {
  const { account_id } = req.body;
  if (!account_id) return res.status(400).json({ error: 'Account ID requis' });
  try {
    await pool.query('UPDATE users SET mt5_account_id = $1 WHERE id = $2', [account_id, req.user.id]);
    res.json({ success: true });
  } catch(e) {
    console.error('Connect MT5 error:', e.message);
    res.status(500).json({ error: 'Erreur serveur' });
  }
});

app.post('/api/trade', authMiddleware, async (req, res) => {
  try {
    const result = await pool.query('SELECT mt5_account_id FROM users WHERE id = $1', [req.user.id]);
    const user = result.rows[0];
    if (!user?.mt5_account_id) return res.status(400).json({ error: 'Aucun compte MT5 connecté' });
    const { method, path: apiPath, body } = req.body;
    const response = await fetch(`${META_API}/users/current/accounts/${user.mt5_account_id}${apiPath}`, {
      method: method || 'GET',
      headers: { 'auth-token': METAAPI_TOKEN, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    });
    const text = await response.text();
    const result2 = text ? JSON.parse(text) : {};
    res.status(response.status).json(result2);
  } catch(e) { res.status(500).json({ error: e.message }); }
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
