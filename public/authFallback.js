(() => {
  'use strict';
  let mode = 'login';
  const $ = (id) => document.getElementById(id);

  function message(text, kind = 'error') {
    const box = $('auth-msg');
    box.textContent = text;
    box.className = 'auth-msg ' + kind;
    box.style.display = 'block';
  }

  function showDashboard() {
    $('auth-wrap').style.display = 'none';
    const app = $('app');
    app.style.display = 'block';
    app.innerHTML = '<div class="topbar"><span class="topbar-logo">MyFlow<span>FX</span></span></div>' +
      '<div class="mt5-card"><div class="mt5-title">Worker MT5 démo</div>' +
      '<div class="mt5-sub" id="worker-message">Chargement du statut sécurisé…</div>' +
      '<div class="metrics-grid"><div class="metric"><div class="metric-lbl">Statut</div><div class="metric-val" id="worker-state">—</div></div>' +
      '<div class="metric"><div class="metric-lbl">Positions ouvertes</div><div class="metric-val" id="worker-positions">—</div></div></div>' +
      '<div class="how-to" id="worker-last" style="margin-top:14px">Lecture seule : aucun ordre n’est autorisé.</div></div>' +
      '<div class="mt5-card"><div class="mt5-title">Positions démo ouvertes</div><div id="position-list" class="mt5-sub">Chargement…</div></div>' +
      '<a class="btn-connect" style="display:flex;align-items:center;justify-content:center;text-decoration:none" href="/accounts">Gérer mes comptes et réglages</a>';
    loadStatus();
  }

  async function loadStatus() {
    const token = localStorage.getItem('tf_token');
    if (!token) return;
    try {
      const response = await fetch('/api/engine/status', {
        headers: { Authorization: 'Bearer ' + token },
        cache: 'no-store'
      });
      const data = await response.json();
      if (!response.ok) throw new Error();
      const online = data.status === 'online';
      $('worker-state').textContent = online ? 'Connecté' : 'Hors ligne';
      $('worker-state').className = 'metric-val ' + (online ? 'pos' : 'neg');
      $('worker-positions').textContent = Number.isInteger(data.positionsCount) ? String(data.positionsCount) : '—';
      $('worker-message').textContent = data.message;
      $('worker-last').textContent = data.lastSeen
        ? 'Dernier signal : ' + new Date(data.lastSeen).toLocaleString('fr-FR') + ' · Lecture seule : aucun ordre autorisé.'
        : 'Aucun signal reçu. Lecture seule : aucun ordre autorisé.';
      renderPositions(data.positions);
    } catch (_) {
      $('worker-message').textContent = 'Statut du worker indisponible.';
    }
  }

  function renderPositions(positions) {
    const list = $('position-list');
    list.replaceChildren();
    if (!Array.isArray(positions) || positions.length === 0) {
      list.textContent = 'Aucune position démo ouverte.';
      return;
    }
    for (const position of positions) {
      const line = document.createElement('div');
      line.className = 'how-to';
      line.style.margin = '10px 0 0';
      const stop = position.stopLoss > 0 ? position.stopLoss : 'non défini';
      line.textContent = position.symbol + ' · ' + position.side + ' · Volume ' +
        position.volume + ' · Entrée ' + position.openPrice + ' · Stop-loss ' + stop;
      list.append(line);
    }
  }

  window.switchTab = (next) => {
    mode = next;
    document.querySelectorAll('.auth-tab').forEach((button, index) => {
      button.classList.toggle('active', (index === 0 && next === 'login') || (index === 1 && next === 'register'));
    });
    $('auth-btn').textContent = next === 'login' ? 'Se connecter' : 'S’inscrire';
    $('auth-msg').style.display = 'none';
  };

  window.handleAuth = async () => {
    const email = $('auth-email').value.trim();
    const password = $('auth-password').value;
    if (!email || !password) return message('Remplis l’e-mail et le mot de passe.');
    try {
      const response = await fetch('/api/' + (mode === 'login' ? 'login' : 'register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) return message(data.error || 'Impossible de continuer.');
      if (mode === 'register') {
        window.switchTab('login');
        return message('Compte créé. Tu peux maintenant te connecter.', 'success');
      }
      localStorage.setItem('tf_token', data.token);
      showDashboard();
    } catch (_) {
      message('Le serveur staging est momentanément indisponible.');
    }
  };

  if (localStorage.getItem('tf_token')) showDashboard();
})();
