'use strict';

// ── Landvlaggen (emoji) per teamnaam ──────────────────────────────────────────
const FLAGS = {
  'argentina': '🇦🇷', 'france': '🇫🇷', 'england': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'spain': '🇪🇸',
  'brazil': '🇧🇷', 'portugal': '🇵🇹', 'netherlands': '🇳🇱', 'holland': '🇳🇱',
  'belgium': '🇧🇪', 'italy': '🇮🇹', 'uruguay': '🇺🇾', 'germany': '🇩🇪',
  'croatia': '🇭🇷', 'switzerland': '🇨🇭', 'colombia': '🇨🇴', 'mexico': '🇲🇽',
  'united states': '🇺🇸', 'usa': '🇺🇸', 'senegal': '🇸🇳', 'denmark': '🇩🇰',
  'austria': '🇦🇹', 'morocco': '🇲🇦', 'japan': '🇯🇵', 'serbia': '🇷🇸',
  'poland': '🇵🇱', 'south korea': '🇰🇷', 'korea republic': '🇰🇷', 'hungary': '🇭🇺',
  'ukraine': '🇺🇦', 'australia': '🇦🇺', 'canada': '🇨🇦', 'turkey': '🇹🇷',
  'türkiye': '🇹🇷', 'iran': '🇮🇷', 'ecuador': '🇪🇨', 'peru': '🇵🇪',
  'chile': '🇨🇱', 'paraguay': '🇵🇾', 'saudi arabia': '🇸🇦', 'egypt': '🇪🇬',
  'nigeria': '🇳🇬', 'cameroon': '🇨🇲', 'ghana': '🇬🇭', 'tunisia': '🇹🇳',
  'algeria': '🇩🇿', "côte d'ivoire": '🇨🇮', 'ivory coast': '🇨🇮', 'mali': '🇲🇱',
  'south africa': '🇿🇦', 'new zealand': '🇳🇿', 'qatar': '🇶🇦', 'jamaica': '🇯🇲',
  'honduras': '🇭🇳', 'panama': '🇵🇦', 'costa rica': '🇨🇷', 'el salvador': '🇸🇻',
  'venezuela': '🇻🇪', 'bolivia': '🇧🇴', 'scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', 'wales': '🏴󠁧󠁢󠁷󠁬󠁳󠁿',
  'indonesia': '🇮🇩', 'iraq': '🇮🇶', 'uzbekistan': '🇺🇿', 'oman': '🇴🇲',
  'palestine': '🇵🇸', 'guatemala': '🇬🇹', 'cuba': '🇨🇺', 'angola': '🇦🇴',
  'tanzania': '🇹🇿', 'zambia': '🇿🇲', 'zimbabwe': '🇿🇼'
};

function getFlag(teamName) {
  return FLAGS[(teamName || '').toLowerCase()] || '🏳️';
}

// ── Status en staat ───────────────────────────────────────────────────────────
let currentPredictions = [];

function showError(elementId, msg) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
}
function hideError(elementId) {
  document.getElementById(elementId)?.classList.add('hidden');
}

function setLoading(text) {
  document.getElementById('loginPanel').classList.add('hidden');
  document.getElementById('predictionsPanel').classList.add('hidden');
  document.getElementById('successPanel').classList.add('hidden');
  const panel = document.getElementById('loadingPanel');
  panel.classList.remove('hidden');
  document.getElementById('loadingText').textContent = text;
}

function showPredictions() {
  document.getElementById('loadingPanel').classList.add('hidden');
  document.getElementById('loginPanel').classList.add('hidden');
  document.getElementById('predictionsPanel').classList.remove('hidden');
}

function showSuccess(msg) {
  document.getElementById('loadingPanel').classList.add('hidden');
  document.getElementById('predictionsPanel').classList.add('hidden');
  document.getElementById('successPanel').classList.remove('hidden');
  document.getElementById('successMessage').textContent = msg;
}

// ── Login ─────────────────────────────────────────────────────────────────────
async function doLogin() {
  hideError('loginError');
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const oddsApiKey = document.getElementById('oddsApiKey').value.trim();
  const footballDataApiKey = document.getElementById('footballDataApiKey').value.trim();

  if (!username || !password) {
    showError('loginError', 'Vul je gebruikersnaam en wachtwoord in.');
    return;
  }

  document.getElementById('loginBtn').disabled = true;
  setLoading('Inloggen op Scorito...');

  try {
    const loginRes = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, oddsApiKey, footballDataApiKey })
    });
    if (!loginRes.ok) {
      const data = await loginRes.json();
      throw new Error(data.error || 'Login mislukt');
    }

    document.getElementById('loadingText').textContent = 'Scorito-ronde ophalen via browser...';
    await fetchAndRenderPredictions();

    // Toon ingestatus in header
    document.getElementById('statusBadge').classList.remove('hidden');
    document.getElementById('statusText').textContent = username;

  } catch (err) {
    document.getElementById('loginPanel').classList.remove('hidden');
    document.getElementById('loadingPanel').classList.add('hidden');
    showError('loginError', err.message);
  } finally {
    document.getElementById('loginBtn').disabled = false;
  }
}

// ── Voorspellingen ophalen en renderen ────────────────────────────────────────
async function fetchAndRenderPredictions() {
  document.getElementById('loadingText').textContent = 'Voorspellingen genereren op basis van odds, FIFA-rang en toernooivorm...';

  const res = await fetch('/api/predictions');
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.error || 'Kon voorspellingen niet ophalen');
  }
  const data = await res.json();

  currentPredictions = data.predictions;
  renderPredictions(data.round, data.predictions, data.dataSources);
  showPredictions();
}

// ── Wedstrijdkaarten renderen ─────────────────────────────────────────────────
function renderPredictions(round, predictions, dataSources) {
  document.getElementById('roundTitle').textContent = round.title || 'Huidige ronde';
  document.getElementById('roundUrl').textContent = round.url || '';
  document.getElementById('matchCount').textContent = `${predictions.length} wedstrijd${predictions.length !== 1 ? 'en' : ''}`;

  // Databron-badges
  const badges = document.getElementById('dataBadges');
  badges.innerHTML = '';
  badges.appendChild(badge('Odds', dataSources?.odds));
  badges.appendChild(badge('Vorm', dataSources?.form));
  badges.appendChild(badge('Scorers', dataSources?.scorers));

  const container = document.getElementById('matchCards');
  container.innerHTML = '';
  predictions.forEach((match, i) => {
    container.appendChild(buildMatchCard(match, i));
  });
}

function badge(label, available) {
  const el = document.createElement('span');
  el.className = `badge ${available ? 'badge-ok' : 'badge-warn'}`;
  el.textContent = available ? `✓ ${label}` : `⚠ ${label}`;
  return el;
}

function buildMatchCard(match, cardIndex) {
  const tmpl = document.getElementById('matchCardTemplate');
  const card = tmpl.content.cloneNode(true);
  const root = card.querySelector('.match-card');
  root.dataset.index = cardIndex;

  // Teams en vlaggen
  root.querySelector('.home-team .team-flag').textContent = getFlag(match.homeTeam);
  root.querySelector('.home-team .team-name').textContent = match.homeTeam;
  root.querySelector('.away-team .team-flag').textContent = getFlag(match.awayTeam);
  root.querySelector('.away-team .team-name').textContent = match.awayTeam;

  // Score-inputs
  const homeInput = root.querySelector('.home-score');
  const awayInput = root.querySelector('.away-score');
  homeInput.value = match.prediction.homeScore;
  awayInput.value = match.prediction.awayScore;
  homeInput.addEventListener('change', () => updatePrediction(cardIndex, 'homeScore', +homeInput.value));
  awayInput.addEventListener('change', () => updatePrediction(cardIndex, 'awayScore', +awayInput.value));

  // Topscorer-dropdowns vullen
  buildScorerDropdown(root.querySelector('.home-scorer-select'), match, 'home');
  buildScorerDropdown(root.querySelector('.away-scorer-select'), match, 'away');

  // Onderbouwing
  fillReasoning(root, match);

  return card;
}

function buildScorerDropdown(select, match, side) {
  const candidates = match.prediction.recommendedScorers?.[side] || [];
  const selected = match.prediction.selectedScorers?.[side === 'home' ? 0 : 1] || '';

  select.innerHTML = '<option value="">— geen —</option>';
  candidates.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.name;
    opt.textContent = `${p.name} (${p.goals} ⚽, ${p.gamesPlayed} wed.)`;
    if (p.name === selected) opt.selected = true;
    select.appendChild(opt);
  });

  const cardIndex = parseInt(select.closest('.match-card').dataset.index, 10);
  select.addEventListener('change', () => {
    const scorers = [...(currentPredictions[cardIndex]?.prediction?.selectedScorers || ['', ''])];
    scorers[side === 'home' ? 0 : 1] = select.value;
    updatePrediction(cardIndex, 'selectedScorers', scorers);
  });
}

function fillReasoning(root, match) {
  const r = match.reasoning || {};

  // FIFA-rang
  root.querySelector('.home-rank').textContent = `#${r.homeRank || '?'} ${match.homeTeam}`;
  root.querySelector('.away-rank').textContent = `${match.awayTeam} #${r.awayRank || '?'}`;

  // Odds
  const oddsRow = root.querySelector('.odds-row');
  if (r.oddsProbs) {
    const h = Math.round(r.finalProbs.homeWin * 100);
    const d = Math.round(r.finalProbs.draw * 100);
    const a = 100 - h - d;
    oddsRow.innerHTML = `
      <div class="odds-bar">
        <div class="odds-home" style="width:${h}%"></div>
        <div class="odds-draw" style="width:${d}%"></div>
        <div class="odds-away" style="width:${a}%"></div>
      </div>
      <div class="odds-labels">
        <span>${match.homeTeam.split(' ')[0]} ${h}%</span>
        <span>Gelijk ${d}%</span>
        <span>${a}% ${match.awayTeam.split(' ')[0]}</span>
      </div>`;
  } else {
    const h = Math.round((r.finalProbs?.homeWin || 0) * 100);
    const d = Math.round((r.finalProbs?.draw || 0) * 100);
    const a = 100 - h - d;
    oddsRow.innerHTML = `
      <div class="odds-bar">
        <div class="odds-home" style="width:${h}%"></div>
        <div class="odds-draw" style="width:${d}%"></div>
        <div class="odds-away" style="width:${a}%"></div>
      </div>
      <div class="odds-labels">
        <span>${h}%</span><span>${d}%</span><span>${a}%</span>
      </div>
      <small style="color:var(--muted);font-size:.72rem;">Geschat op basis van FIFA-rang en vorm (geen live odds)</small>`;
  }

  // Toernooivorm
  const homeFormDots = root.querySelector('.home-form-dots');
  const awayFormDots = root.querySelector('.away-form-dots');
  root.querySelectorAll('.form-name')[0].textContent = match.homeTeam.split(' ')[0];
  root.querySelectorAll('.form-name')[1].textContent = match.awayTeam.split(' ')[0];
  homeFormDots.innerHTML = renderFormDots(r.homeForm || []);
  awayFormDots.innerHTML = renderFormDots(r.awayForm || []);

  // Verwachte goals
  const xgRow = root.querySelector('.xg-row');
  if (r.expectedGoals) {
    xgRow.innerHTML = `
      <div class="xg-numbers">${r.expectedGoals.home.toFixed(1)} – ${r.expectedGoals.away.toFixed(1)}</div>
      <div>Verwachte doelpunten · Over 2.5: ${Math.round(r.over25Prob * 100)}%</div>`;
  } else {
    xgRow.textContent = 'Geen over/under odds beschikbaar';
  }

  // Topscorer-kandidaten
  const candidatesEl = root.querySelector('.scorer-candidates');
  const allCandidates = [
    ...(match.prediction.recommendedScorers?.home || []).map(p => ({ ...p, side: match.homeTeam })),
    ...(match.prediction.recommendedScorers?.away || []).map(p => ({ ...p, side: match.awayTeam }))
  ];
  if (allCandidates.length > 0) {
    candidatesEl.innerHTML = allCandidates.map(p => `
      <div class="scorer-candidate">
        <div>
          <strong>${p.name}</strong><br/>
          <span style="font-size:.72rem;color:var(--muted)">${p.side}</span>
        </div>
        <span class="scorer-stat">${p.goals} ⚽ / ${p.gamesPlayed} wed.</span>
      </div>`).join('');
  } else {
    candidatesEl.innerHTML = '<div style="color:var(--muted);font-size:.8rem">Nog geen toernooidata beschikbaar</div>';
  }
}

function renderFormDots(form) {
  const dots = form.length > 0
    ? form.map(r => `<span class="form-dot ${r}">${r}</span>`).join('')
    : '<span class="form-dot empty">?</span>'.repeat(3);
  return dots;
}

// ── State bijwerken ───────────────────────────────────────────────────────────
function updatePrediction(index, field, value) {
  if (!currentPredictions[index]) return;
  currentPredictions[index].prediction[field] = value;
}

// ── Indienen ──────────────────────────────────────────────────────────────────
async function submitAll() {
  hideError('submitError');
  document.getElementById('submitBtn').disabled = true;
  document.getElementById('submitBtn').textContent = 'Bezig met indienen...';

  try {
    const res = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ predictions: currentPredictions })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Indienen mislukt');
    showSuccess(data.message);
  } catch (err) {
    showError('submitError', err.message);
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('submitBtn').textContent = '✓ Bevestig & dien in op Scorito';
  }
}

// ── Uitloggen / reset ─────────────────────────────────────────────────────────
async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  resetToLogin();
}

function resetToLogin() {
  currentPredictions = [];
  document.getElementById('matchCards').innerHTML = '';
  document.getElementById('successPanel').classList.add('hidden');
  document.getElementById('predictionsPanel').classList.add('hidden');
  document.getElementById('loadingPanel').classList.add('hidden');
  document.getElementById('loginPanel').classList.remove('hidden');
  document.getElementById('statusBadge').classList.add('hidden');
  document.getElementById('password').value = '';
}

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  const status = await fetch('/api/status').then(r => r.json()).catch(() => ({}));
  if (status.loggedIn) {
    document.getElementById('statusBadge').classList.remove('hidden');
    setLoading('Sessie herstellen...');
    try {
      await fetchAndRenderPredictions();
    } catch {
      document.getElementById('loginPanel').classList.remove('hidden');
      document.getElementById('loadingPanel').classList.add('hidden');
    }
  }
})();
