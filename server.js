const express = require('express');
const fetch = require('node-fetch');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const META_API = 'https://mt-client-api-v1.london.agiliumtrade.ai';

app.post('/api/proxy', async (req, res) => {
  const { method, path: apiPath, body, token } = req.body;
  try {
    const response = await fetch(META_API + apiPath, {
      method: method || 'GET',
      headers: {
        'auth-token': token,
        'Content-Type': 'application/json'
      },
      body: body ? JSON.stringify(body) : undefined
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    res.status(response.status).json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Trade Manager running on port ${PORT}`));
