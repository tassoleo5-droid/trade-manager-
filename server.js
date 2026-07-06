const express = require('express');
const fetch = require('node-fetch');
const cors = require('cors');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const fs = require('fs');

const app = express();
const META_API = 'https://mt-client-api-v1.london.agiliumtrade.ai';
const METAAPI_TOKEN = process.env.METAAPI_TOKEN;
const JWT_SECRET = process.env.JWT_SECRET || 'trademanager_secret_2024';
const DB_FILE = '/tmp/users.json';

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

function loadDB() {
  try { return JSON.parse(fs.readFileSync(DB_FILE, 'utf8')); }
  catch(e) { return { users: [] }; }
}

function saveDB(db) {
  fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2));
}

function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Non autorisé' });
  try { req.user = jwt.verify(token, JWT_SECRET); next(); }
  catch(e) { res.status(401).json({ error: 'Token invalide' }); }
}

app.post('/api/register', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ error: 'Email et mot de passe requis' });
  const db = loadDB();
  if (db.users.find(u => u.email === email)) return res.status(400).json({ error: 'Email déjà utilisé' });
  const hash = await bcrypt.hash(password, 10);
  const user = { id: Date.now(), email, password: hash, mt5_account_id: null };
  db.users.push(user);
  saveDB(db);
  res.json({ success: true });
});

app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;
  const db = loadDB();
  const user = db.users.find(u => u.email === email);
  if (!user) return res.status(401).json({ error: 'Email ou mot de passe incorrect' });
  const valid = await bcrypt.compare(password, user.password);
  if (!valid) return res.status(401).json({ error: 'Email ou mot de passe incorrect' });
  const token = jwt.sign({ id: user.id, email: user.email }, JWT_SECRET, { expiresIn: '30d' });
  res.json({ token, email: user.email, mt5_account_id: user.mt5_account_id });
});

app.post('/api/connect-mt5', authMiddleware, async (req, res) => {
  const { login, password, server } = req.body;
  try {
    const response = await fetch('https://mt-provisioning-api-v1.agiliumtrade.ai/users/current/accounts', {      method: 'POST',
      headers: { 'auth-token': METAAPI_TOKEN, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        login, password, server,
        platform: 'mt5',
        name: `user_${req.user.id}`,
        type: 'cloud',
        region: 'london',
        reliability: 'high'
      })
    });
    const data = await response.json();
    if (!response.ok) return res.status(400).json({ error: data.message || 'Erreur connexion MT5' });
    const db = loadDB();
    const user = db.users.find(u => u.id === req.user.id);
    if (user) { user.mt5_account_id = data.id; saveDB(db); }
    res.json({ success: true, accountId: data.id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/trade', authMiddleware, async (req, res) => {
  const db = loadDB();
  const user = db.users.find(u => u.id === req.user.id);
  if (!user?.mt5_account_id) return res.status(400).json({ error: 'Aucun compte MT5 connecté' });
  const { method, path: apiPath, body } = req.body;
  try {
    const response = await fetch(META_API + `/users/current/accounts/${user.mt5_account_id}${apiPath}`, {
      method: method || 'GET',
      headers: { 'auth-token': METAAPI_TOKEN, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    });
    const text = await response.text();
    const result = text ? JSON.parse(text) : {};
    res.status(response.status).json(result);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`TradeFlow running on port ${PORT}`));
