'use strict';

const FLAGS = {
  'argentina':'🇦🇷','france':'🇫🇷','england':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','spain':'🇪🇸',
  'brazil':'🇧🇷','portugal':'🇵🇹','netherlands':'🇳🇱','holland':'🇳🇱',
  'belgium':'🇧🇪','italy':'🇮🇹','uruguay':'🇺🇾','germany':'🇩🇪',
  'croatia':'🇭🇷','switzerland':'🇨🇭','colombia':'🇨🇴','mexico':'🇲🇽',
  'united states':'🇺🇸','usa':'🇺🇸','senegal':'🇸🇳','denmark':'🇩🇰',
  'austria':'🇦🇹','morocco':'🇲🇦','japan':'🇯🇵','serbia':'🇷🇸',
  'poland':'🇵🇱','south korea':'🇰🇷','korea republic':'🇰🇷','hungary':'🇭🇺',
  'ukraine':'🇺🇦','australia':'🇦🇺','canada':'🇨🇦','turkey':'🇹🇷',
  'türkiye':'🇹🇷','iran':'🇮🇷','ecuador':'🇪🇨','peru':'🇵🇪',
  'chile':'🇨🇱','paraguay':'🇵🇾','saudi arabia':'🇸🇦','egypt':'🇪🇬',
  'nigeria':'🇳🇬','cameroon':'🇨🇲','ghana':'🇬🇭','tunisia':'🇹🇳',
  'algeria':'🇩🇿',"côte d'ivoire":'🇨🇮','ivory coast':'🇨🇮','mali':'🇲🇱',
  'south africa':'🇿🇦','new zealand':'🇳🇿','qatar':'🇶🇦','jamaica':'🇯🇲',
  'honduras':'🇭🇳','panama':'🇵🇦','costa rica':'🇨🇷','el salvador':'🇸🇻',
  'venezuela':'🇻🇪','bolivia':'🇧🇴','scotland':'🏴󠁧󠁢󠁳󠁣󠁴󠁿','wales':'🏴󠁧󠁢󠁷󠁬󠁳󠁿',
  'indonesia':'🇮🇩','iraq':'🇮🇶','uzbekistan':'🇺🇿','guatemala':'🇬🇹'
};
const flag = n => FLAGS[(n||'').toLowerCase()] || '🏳️';

let currentPredictions = [];
let progressSource = null;

// ── Hulpfuncties ──────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => $(id).classList.remove('hidden');
const hide = id => $(id).classList.add('hidden');
function showErr(id, msg) { const el=$(id); el.textContent=msg; el.classList.remove('hidden'); }
function hideErr(id) { $(id)?.classList.add('hidden'); }

function setLoading(text) {
  ['loginPanel','predictionsPanel','successPanel'].forEach(hide);
  show('loadingPanel');
  $('loadingText').textContent = text;
  $('progressLog').innerHTML = '';
}

// ── Live voortgangslog via Server-Sent Events ─────────────────────────────────
function openProgressStream() {
  if (progressSource) { progressSource.close(); progressSource = null; }
  progressSource = new EventSource('/api/progress');
  progressSource.onmessage = (e) => {
    try {
      const { text } = JSON.parse(e.data);
      $('loadingText').textContent = text;
      const line = document.createElement('div');
      line.className = 'progress-line';
      line.textContent = text;
      const log = $('progressLog');
      log.appendChild(line);
      log.scrollTop = log.scrollHeight;
    } catch {}
  };
  progressSource.onerror = () => {};
}

function closeProgressStream() {
  if (progressSource) { progressSource.close(); progressSource = null; }
}

// ── Credentials opslaan/laden in localStorage ─────────────────────────────────
function saveCreds(username, password) {
  try { localStorage.setItem('scorito_creds', JSON.stringify({ username, password })); } catch {}
}
function loadCreds() {
  try { return JSON.parse(localStorage.getItem('scorito_creds') || 'null'); } catch { return null; }
}
function clearCreds() {
  try { localStorage.removeItem('scorito_creds'); } catch {}
}

async function autoLoginWithSaved(creds) {
  const r = await fetch('/api/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: creds.username, password: creds.password })
  });
  if (!r.ok) throw new Error('Auto-login mislukt');
  $('statusText').textContent = creds.username.split('@')[0];
  $('statusBadge').classList.remove('hidden');
}

// ── Initialisatie ─────────────────────────────────────────────────────────────
startApp();

async function startApp() {
  const status = await fetch('/api/status').then(r=>r.json()).catch(()=>({}));

  if (status.hasOddsKey && status.hasFootballKey) {
    hide('apiKeysSection');
    show('apiKeysBadge');
  }

  // Al ingelogd via actieve sessie
  if (status.loggedIn) {
    $('statusBadge').classList.remove('hidden');
    setLoading('Even geduld...');
    try { await fetchAndRenderPredictions(); return; }
    catch { ['loadingPanel'].forEach(hide); }
  }

  // Probeer opgeslagen credentials (alleen PIN nodig geweest)
  const saved = loadCreds();
  if (saved) {
    setLoading('Automatisch inloggen...');
    try {
      await autoLoginWithSaved(saved);
      await fetchAndRenderPredictions();
      return;
    } catch {
      ['loadingPanel'].forEach(hide);
    }
  }

  // Pre-fill gebruikersnaam als die bekend is
  if (saved?.username) $('username').value = saved.username;
  show('loginPanel');
}

// ── Login ─────────────────────────────────────────────────────────────────────
async function doLogin() {
  hideErr('loginError');
  const username = $('username').value.trim();
  const password = $('password').value;
  const oddsApiKey = $('oddsApiKey').value.trim();
  const footballDataApiKey = $('footballDataApiKey').value.trim();

  if (!username || !password) {
    showErr('loginError', 'Vul je e-mail en wachtwoord in.');
    return;
  }
  $('loginBtn').disabled = true;
  setLoading('Inloggen op Scorito...');

  try {
    const r = await fetch('/api/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ username, password, oddsApiKey, footballDataApiKey })
    });
    if (!r.ok) throw new Error((await r.json()).error || 'Login mislukt');

    saveCreds(username, password);
    $('statusBadge').classList.remove('hidden');
    $('statusText').textContent = username.split('@')[0];
    await fetchAndRenderPredictions();
  } catch(err) {
    show('loginPanel'); hide('loadingPanel');
    showErr('loginError', err.message);
  } finally {
    $('loginBtn').disabled = false;
  }
}

// ── Voorspellingen ophalen ────────────────────────────────────────────────────
async function fetchAndRenderPredictions() {
  openProgressStream();
  // Geef SSE-verbinding even tijd om op te starten
  await new Promise(r => setTimeout(r, 250));
  $('loadingText').textContent = 'Verbinding maken met Scorito...';
  try {
    const r = await fetch('/api/predictions');
    if (!r.ok) throw new Error((await r.json()).error || 'Ophalen mislukt');
    const data = await r.json();
    currentPredictions = data.predictions;
    renderPredictions(data.round, data.predictions, data.dataSources);
    ['loadingPanel'].forEach(hide);
    show('predictionsPanel');
  } finally {
    closeProgressStream();
  }
}

// ── Renderen ──────────────────────────────────────────────────────────────────
function renderPredictions(round, predictions, ds) {
  $('roundTitle').textContent = round.title || 'Actieve ronde';
  $('roundUrl').textContent = round.url || '';
  $('matchCount').textContent = `${predictions.length} wedstrijd${predictions.length!==1?'en':''}`;

  const badges = $('dataBadges');
  badges.innerHTML = '';
  [['Odds', ds?.odds], ['Vorm', ds?.form], ['Scorers', ds?.scorers]].forEach(([l,ok]) => {
    const b = document.createElement('span');
    b.className = `badge ${ok ? 'badge-ok' : 'badge-warn'}`;
    b.textContent = ok ? `✓ ${l}` : `⚠ ${l}`;
    badges.appendChild(b);
  });

  const container = $('matchCards');
  container.innerHTML = '';
  predictions.forEach((m,i) => container.appendChild(buildCard(m,i)));
}

function buildCard(match, idx) {
  const frag = document.getElementById('matchCardTemplate').content.cloneNode(true);
  const root = frag.querySelector('.match-card');
  root.dataset.index = idx;

  root.querySelector('.home-team .team-flag').textContent = flag(match.homeTeam);
  root.querySelector('.home-team .team-name').textContent = match.homeTeam;
  root.querySelector('.away-team .team-flag').textContent = flag(match.awayTeam);
  root.querySelector('.away-team .team-name').textContent = match.awayTeam;

  const hIn = root.querySelector('.home-score');
  const aIn = root.querySelector('.away-score');
  hIn.value = match.prediction.homeScore;
  aIn.value = match.prediction.awayScore;
  hIn.addEventListener('change', () => updatePred(idx, 'homeScore', +hIn.value));
  aIn.addEventListener('change', () => updatePred(idx, 'awayScore', +aIn.value));

  buildScorerDrop(root.querySelector('.home-scorer-select'), match, 'home', idx);
  buildScorerDrop(root.querySelector('.away-scorer-select'), match, 'away', idx);

  fillReasoning(root, match);
  return frag;
}

function buildScorerDrop(sel, match, side, idx) {
  const candidates = match.prediction.recommendedScorers?.[side] || [];
  const presel = match.prediction.selectedScorers?.[side==='home'?0:1] || '';
  sel.innerHTML = '<option value="">— geen —</option>';
  candidates.forEach(p => {
    const o = document.createElement('option');
    o.value = p.name;
    o.textContent = `${p.name} (${p.goals} ⚽, ${p.gamesPlayed} w)`;
    if (p.name === presel) o.selected = true;
    sel.appendChild(o);
  });
  sel.addEventListener('change', () => {
    const sc = [...(currentPredictions[idx]?.prediction?.selectedScorers || ['',''])];
    sc[side==='home'?0:1] = sel.value;
    updatePred(idx, 'selectedScorers', sc);
  });
}

function fillReasoning(root, m) {
  const r = m.reasoning || {};
  root.querySelector('.home-rank').textContent = `#${r.homeRank||'?'} ${m.homeTeam.split(' ')[0]}`;
  root.querySelector('.away-rank').textContent = `${m.awayTeam.split(' ')[0]} #${r.awayRank||'?'}`;

  const odds = root.querySelector('.odds-row');
  const fp = r.finalProbs || {};
  const h = Math.round((fp.homeWin||0)*100);
  const d = Math.round((fp.draw||0)*100);
  const a = 100-h-d;
  odds.innerHTML = `
    <div class="odds-bar">
      <div class="odds-home" style="width:${h}%"></div>
      <div class="odds-draw" style="width:${d}%"></div>
      <div class="odds-away" style="width:${a}%"></div>
    </div>
    <div class="odds-labels">
      <span>${m.homeTeam.split(' ')[0]} ${h}%</span>
      <span>Gelijk ${d}%</span>
      <span>${a}% ${m.awayTeam.split(' ')[0]}</span>
    </div>
    ${!r.oddsProbs ? '<small style="color:var(--muted);font-size:.7rem">Schatting (geen live odds)</small>' : ''}`;

  root.querySelector('.home-form-name').textContent = m.homeTeam.split(' ')[0];
  root.querySelector('.away-form-name').textContent = m.awayTeam.split(' ')[0];
  root.querySelector('.home-form-dots').innerHTML = formDots(r.homeForm||[]);
  root.querySelector('.away-form-dots').innerHTML = formDots(r.awayForm||[]);

  const xg = root.querySelector('.xg-row');
  if (r.expectedGoals) {
    xg.innerHTML = `<div class="xg-numbers">${r.expectedGoals.home.toFixed(1)} – ${r.expectedGoals.away.toFixed(1)}</div>
      <div>Over 2.5: ${Math.round((r.over25Prob||0)*100)}%</div>`;
  } else {
    xg.textContent = 'Geen over/under data beschikbaar';
  }

  const all = [
    ...(m.prediction.recommendedScorers?.home||[]).map(p=>({...p,club:m.homeTeam})),
    ...(m.prediction.recommendedScorers?.away||[]).map(p=>({...p,club:m.awayTeam}))
  ];
  root.querySelector('.scorer-candidates').innerHTML = all.length
    ? all.map(p => `<div class="scorer-candidate">
        <div><strong>${p.name}</strong><br><span style="font-size:.7rem;color:var(--muted)">${flag(p.club)} ${p.club.split(' ')[0]}</span></div>
        <span class="scorer-stat">${p.goals}⚽/${p.gamesPlayed}w</span></div>`).join('')
    : '<div style="color:var(--muted);font-size:.8rem">Nog geen toernooiscorerdata</div>';
}

function formDots(form) {
  return form.length
    ? form.map(r=>`<span class="form-dot ${r}">${r}</span>`).join('')
    : `<span class="form-dot empty">?</span>`.repeat(3);
}

function updatePred(idx, field, value) {
  if (currentPredictions[idx]) currentPredictions[idx].prediction[field] = value;
}

// ── Indienen ──────────────────────────────────────────────────────────────────
async function submitAll() {
  hideErr('submitError');
  $('submitBtn').disabled = true;
  $('submitBtn').textContent = 'Bezig met indienen...';
  setLoading('Scorito automatisch invullen en indienen...');
  openProgressStream();
  await new Promise(r => setTimeout(r, 250));

  try {
    const r = await fetch('/api/submit', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ predictions: currentPredictions })
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Indienen mislukt');

    ['loadingPanel','predictionsPanel'].forEach(hide);
    show('successPanel');
    $('successMessage').textContent = data.message;

    if (data.screenshotAfter) {
      show('screenshotWrap');
      $('successScreenshot').src = data.screenshotAfter;
    }
  } catch(err) {
    hide('loadingPanel');
    show('predictionsPanel');
    showErr('submitError', err.message);
    $('submitBtn').disabled = false;
    $('submitBtn').textContent = '✓ Dien in op Scorito';
  } finally {
    closeProgressStream();
  }
}

// ── Uitloggen ─────────────────────────────────────────────────────────────────
async function logout() {
  clearCreds();
  await fetch('/api/logout', { method:'POST' });
  resetToLogin();
}

function resetToLogin() {
  currentPredictions = [];
  $('matchCards').innerHTML = '';
  ['successPanel','predictionsPanel','loadingPanel'].forEach(hide);
  show('loginPanel');
  $('statusBadge').classList.add('hidden');
  $('username').value = '';
  $('password').value = '';
}
