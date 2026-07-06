const express = require('express');
const fetch = require('node-fetch');
const cors = require('cors');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const Database = require('better-sqlite3');

const app = express();
const db = new Database('users.db');
const META_API = 'https://mt-client-api-v1.london.agiliumtrade.ai';
const METAAPI_TOKEN = process.env.METAAPI_TOKEN;
const JWT_SECRET = process.env.JWT_SECRET || 'trademanager_secret_2024';

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Init base de données
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    mt5_account_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Middleware auth
function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Non autorisé' });
  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch(e) {
    res.status(401).json({ error: 'Token invalide' });
  }
}

// Inscription
app.post('/api/register', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ error: 'Email et mot de passe requis' });
  try {
    const hash = await bcrypt.hash(password, 10);
    const stmt = db.prepare('INSERT INTO users (email, password) VALUES (?, ?)');
    stmt.run(email, hash);
    res.json({ success: true });
  } catch(e) {
    res.status(400).json({ error: 'Email déjà utilisé' });
  }
});

// Connexion
app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;
  const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  if (!user) return res.status(401).json({ error: 'Email ou mot de passe incorrect' });
  const valid = await bcrypt.compare(password, user.password);
  if (!valid) return res.status(401).json({ error: 'Email ou mot de passe incorrect' });
  const token = jwt.sign({ id: user.id, email: user.email }, JWT_SECRET, { expiresIn: '30d' });
  res.json({ token, email: user.email, mt5_account_id: user.mt5_account_id });
});

// Connecter compte MT5
app.post('/api/connect-mt5', authMiddleware, async (req, res) => {
  const { login, password, server, platform } = req.body;
  try {
    const response = await fetch('https://trading-api-v1.agiliumtrade.ai/users/current/accounts', {
      method: 'POST',
      headers: { 'auth-token': METAAPI_TOKEN, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        login, password, server,
        platform: platform || 'mt5',
        name: `user_${req.user.id}`,
        type: 'cloud',
        region: 'london',
        reliability: 'high',
        tags: [`user_${req.user.id}`]
      })
    });
    const data = await response.json();
    if (!response.ok) return res.status(400).json({ error: data.message || 'Erreur connexion MT5' });
    const accountId = data.id;
    db.prepare('UPDATE users SET mt5_account_id = ? WHERE id = ?').run(accountId, req.user.id);
    res.json({ success: true, accountId });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

// Proxy MetaApi
app.post('/api/trade', authMiddleware, async
