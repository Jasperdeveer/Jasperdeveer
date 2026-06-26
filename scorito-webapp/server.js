'use strict';
require('dotenv').config();

const express = require('express');
const session = require('express-session');
const path = require('path');

// SSE-voortgang per sessie
const sseClients = new Map();

function sendProgress(sessionId, text) {
  console.log(`[progress] ${text}`);
  const res = sseClients.get(sessionId);
  if (res) {
    try { res.write(`data: ${JSON.stringify({ text })}\n\n`); } catch {}
  }
}

function makeLog(sessionId) {
  return (text) => sendProgress(sessionId, text);
}

const { fetchRound, submitPredictions } = require('./lib/scorito');
const { getOdds } = require('./lib/odds');
const { getRankings } = require('./lib/fifa');
const { getTeamForm, getScorers, getTeamStats } = require('./lib/tournament');
const { generatePredictions } = require('./lib/predictor');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(session({
  secret: process.env.SESSION_SECRET || 'scorito-dev-secret-change-me',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, maxAge: 4 * 60 * 60 * 1000 }
}));

// Optionele PIN-beveiliging — stel APP_PIN in als de app publiek bereikbaar is
app.post('/api/verify-pin', (req, res) => {
  const appPin = process.env.APP_PIN;
  if (!appPin) { req.session.pinVerified = true; return res.json({ success: true, pinRequired: false }); }
  if (req.body.pin === appPin) {
    req.session.pinVerified = true;
    return res.json({ success: true });
  }
  res.status(401).json({ error: 'Onjuiste PIN' });
});

app.get('/api/pin-required', (req, res) => {
  res.json({ required: !!process.env.APP_PIN, verified: !!req.session.pinVerified });
});

// Bescherm alle /api/* routes (behalve verify-pin en pin-required) als APP_PIN is ingesteld
app.use('/api', (req, res, next) => {
  if (!process.env.APP_PIN) return next();
  if (req.path === '/verify-pin' || req.path === '/pin-required') return next();
  if (req.session.pinVerified) return next();
  res.status(401).json({ error: 'PIN vereist', pinRequired: true });
});

app.use(express.static(path.join(__dirname, 'public')));

// ── SSE voortgangsstream ───────────────────────────────────────────────────

app.get('/api/progress', (req, res) => {
  if (!req.session.scorito) return res.status(401).end();
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();
  sseClients.set(req.sessionID, res);
  req.on('close', () => sseClients.delete(req.sessionID));
});

// ── Debug: bekijk wat Puppeteer echt ziet op de loginpagina ──────────────────

app.get('/api/debug-login', async (req, res) => {
  if (!req.session.pinVerified && process.env.APP_PIN) {
    return res.status(401).json({ error: 'PIN vereist' });
  }
  const puppeteer = require('puppeteer');
  const { execSync } = require('child_process');
  let executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
  if (!executablePath) {
    try { executablePath = execSync('which chromium-browser 2>/dev/null || which chromium 2>/dev/null', { timeout: 2000 }).toString().trim(); } catch {}
  }
  const browser = await puppeteer.launch({
    headless: true, executablePath,
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-gpu']
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 390, height: 844 });
    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1');

    const urlsToTry = [
      'https://mobile.scorito.com/login',
      'https://www.scorito.com/account/login'
    ];
    const results = [];
    for (const url of urlsToTry) {
      try {
        try {
          await page.goto(url, { waitUntil: 'load', timeout: 20000 });
        } catch (e) {
          if (!e.message.includes('detach') && !e.message.includes('net::ERR')) throw e;
        }
        await new Promise(r => setTimeout(r, 3000));
        const screenshot = await page.screenshot({ type: 'jpeg', quality: 72, encoding: 'base64' });
        const dom = await page.evaluate(() => ({
          finalUrl: location.href,
          title: document.title,
          inputs: Array.from(document.querySelectorAll('input')).map(i => ({
            type: i.type, name: i.name, id: i.id,
            placeholder: i.placeholder, className: i.className.substring(0, 80)
          })),
          buttons: Array.from(document.querySelectorAll('button,input[type=submit]')).map(b => ({
            type: b.type || b.tagName, id: b.id,
            text: b.textContent?.trim().substring(0, 60),
            className: b.className?.substring(0, 80)
          })),
          forms: Array.from(document.querySelectorAll('form')).map(f => ({
            id: f.id, action: f.action, className: f.className.substring(0, 80)
          })),
          bodySnippet: document.body.innerHTML.substring(0, 6000)
        }));
        results.push({ url, screenshot: `data:image/jpeg;base64,${screenshot}`, ...dom });
      } catch (e) {
        results.push({ url, error: e.message });
      }
    }
    res.json(results);
  } finally {
    await browser.close();
  }
});

// ── Auth ──────────────────────────────────────────────────────────────────────

app.post('/api/login', (req, res) => {
  const { username, password, oddsApiKey, footballDataApiKey } = req.body;
  if (!username?.trim() || !password) {
    return res.status(400).json({ error: 'Gebruikersnaam en wachtwoord zijn verplicht.' });
  }
  req.session.scorito = { username: username.trim(), password };
  if (oddsApiKey?.trim()) req.session.oddsApiKey = oddsApiKey.trim();
  if (footballDataApiKey?.trim()) req.session.footballDataApiKey = footballDataApiKey.trim();
  res.json({ success: true });
});

app.post('/api/logout', (req, res) => {
  req.session.destroy(() => res.json({ success: true }));
});

app.get('/api/status', (req, res) => {
  res.json({
    loggedIn: !!req.session.scorito,
    hasOddsKey: !!(req.session.oddsApiKey || process.env.ODDS_API_KEY),
    hasFootballKey: !!(req.session.footballDataApiKey || process.env.FOOTBALL_DATA_API_KEY)
  });
});

// ── Scorito ronde ophalen ─────────────────────────────────────────────────────

app.get('/api/round', async (req, res) => {
  if (!req.session.scorito) return res.status(401).json({ error: 'Niet ingelogd.' });
  try {
    const round = await fetchRound(req.session.scorito, makeLog(req.sessionID));
    res.json(round);
  } catch (err) {
    console.error('fetchRound:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── Voorspellingen genereren ─────────────────────────────────────────────────

app.get('/api/predictions', async (req, res) => {
  if (!req.session.scorito) return res.status(401).json({ error: 'Niet ingelogd.' });

  const oddsKey = req.session.oddsApiKey || process.env.ODDS_API_KEY || null;
  const footballKey = req.session.footballDataApiKey || process.env.FOOTBALL_DATA_API_KEY || null;

  try {
    const log = makeLog(req.sessionID);
    const round = await fetchRound(req.session.scorito, log);
    log('Odds en statistieken ophalen...');

    // Haal externe data parallel op; fouten worden afzonderlijk afgehandeld
    const [rankingsResult, oddsResult, formResult, scorersResult, statsResult] =
      await Promise.allSettled([
        Promise.resolve(getRankings()),
        oddsKey ? getOdds(round.matches, oddsKey) : Promise.resolve([]),
        footballKey ? getTeamForm(footballKey) : Promise.resolve({}),
        footballKey ? getScorers(footballKey) : Promise.resolve([]),
        footballKey ? getTeamStats(footballKey) : Promise.resolve({})
      ]);

    if (rankingsResult.status === 'rejected') console.warn('FIFA-ranglijst fout:', rankingsResult.reason);
    if (oddsResult.status === 'rejected') console.warn('Odds fout:', oddsResult.reason);
    if (formResult.status === 'rejected') console.warn('Vorm fout:', formResult.reason);
    if (scorersResult.status === 'rejected') console.warn('Scorers fout:', scorersResult.reason);
    if (statsResult.status === 'rejected') console.warn('Stats fout:', statsResult.reason);

    log('Voorspellingen berekenen...');
    const predictions = generatePredictions({
      matches: round.matches,
      rankings: rankingsResult.value || {},
      odds: oddsResult.value || [],
      form: formResult.value || {},
      scorers: scorersResult.value || [],
      teamStats: statsResult.value || {}
    });

    res.json({
      round,
      predictions,
      dataSources: {
        odds: oddsResult.status === 'fulfilled' && (oddsResult.value?.length > 0),
        form: formResult.status === 'fulfilled' && Object.keys(formResult.value || {}).length > 0,
        scorers: scorersResult.status === 'fulfilled' && (scorersResult.value?.length > 0)
      }
    });
  } catch (err) {
    console.error('predictions:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── Voorspellingen indienen ──────────────────────────────────────────────────

app.post('/api/submit', async (req, res) => {
  if (!req.session.scorito) return res.status(401).json({ error: 'Niet ingelogd.' });
  const { predictions } = req.body;
  if (!Array.isArray(predictions) || predictions.length === 0) {
    return res.status(400).json({ error: 'Geen voorspellingen meegegeven.' });
  }
  try {
    const result = await submitPredictions(req.session.scorito, predictions, makeLog(req.sessionID));
    res.json(result);
  } catch (err) {
    console.error('submitPredictions:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`\nScoreto WK 2026 Auto-Fill draait op: http://localhost:${PORT}`);
  console.log('Ga naar de webapp om je Scorito-gegevens in te voeren.\n');
});
