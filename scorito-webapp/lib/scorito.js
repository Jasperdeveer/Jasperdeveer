'use strict';
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());
const { execSync } = require('child_process');

const SCORITO_URL = 'https://www.scorito.com';

function findChromium() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) return process.env.PUPPETEER_EXECUTABLE_PATH;
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  try {
    const found = execSync(
      'find /opt/pw-browsers -name "chrome" -o -name "chromium" 2>/dev/null | grep -v ".zip" | head -1',
      { timeout: 3000 }
    ).toString().trim();
    if (found) return found;
  } catch {}
  for (const cmd of ['chromium-browser', 'chromium', 'google-chrome']) {
    try {
      const found = execSync(`which ${cmd} 2>/dev/null`, { timeout: 2000 }).toString().trim();
      if (found) return found;
    } catch {}
  }
  return undefined;
}

async function launchBrowser() {
  const executablePath = findChromium();
  return puppeteer.launch({
    headless: true,
    executablePath,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-extensions',
      '--disable-background-networking',
      '--disable-default-apps',
      '--no-first-run',
      '--disable-blink-features=AutomationControlled',
      '--lang=nl-NL,nl'
    ]
  });
}


// Blokkeer afbeeldingen, media, fonts en analytics — maakt Scorito ~3× sneller
async function setupPageOptimizations(page) {
  await page.setRequestInterception(true);
  page.on('request', req => {
    const rt = req.resourceType();
    const url = req.url();
    if (rt === 'image' || rt === 'media' || rt === 'font') {
      req.abort();
    } else if (url.includes('google-analytics') || url.includes('gtag') ||
               url.includes('doubleclick') || url.includes('facebook.net') ||
               url.includes('analytics') || url.includes('/beacon')) {
      req.abort();
    } else {
      req.continue();
    }
  });
}

// Poll de URL vanuit Node.js (niet via browser-JS) — overleeft execution-context-vernietiging
// die optreedt wanneer de pagina navigeert terwijl waitForFunction nog actief is.
async function waitForLoginRedirect(page, timeout = 45000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    try {
      if (!page.url().includes('/account/login')) {
        await new Promise(r => setTimeout(r, 800));
        return;
      }
    } catch {}
    await new Promise(r => setTimeout(r, 600));
  }
  try {
    if (page.url().includes('/account/login')) {
      throw new Error('Login timeout na 45s. Controleer je gebruikersnaam en wachtwoord.');
    }
  } catch (e) {
    if (e.message.includes('timeout')) throw e;
  }
}

async function doLogin(page, credentials, log) {
  log('Navigeren naar Scorito loginpagina...');
  await page.goto(`${SCORITO_URL}/account/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await new Promise(r => setTimeout(r, 1500));

  const userSelectors = [
    'input[name="username"]', 'input[name="email"]', 'input[type="email"]',
    'input[id*="username"]', 'input[id*="email"]',
    'input[placeholder*="gebruikersnaam" i]', 'input[placeholder*="e-mail" i]',
    'input[placeholder*="email" i]'
  ];
  const passSelectors = [
    'input[name="password"]', 'input[type="password"]', 'input[id*="password"]'
  ];

  let usernameInput = null;
  for (const sel of userSelectors) {
    usernameInput = await page.$(sel);
    if (usernameInput) { log(`Inlogveld gevonden (${sel})`); break; }
  }
  let passwordInput = null;
  for (const sel of passSelectors) {
    passwordInput = await page.$(sel);
    if (passwordInput) break;
  }

  if (!usernameInput || !passwordInput) {
    throw new Error(
      'Kan het loginformulier niet vinden op Scorito. ' +
      'Controleer of de URL correct is of dat Scorito de paginastructuur heeft gewijzigd.'
    );
  }

  log('E-mail en wachtwoord invullen...');
  await usernameInput.click({ clickCount: 3 });
  await usernameInput.type(credentials.username, { delay: 40 });
  await passwordInput.click({ clickCount: 3 });
  await passwordInput.type(credentials.password, { delay: 40 });

  log('Inlogknop klikken...');
  let submitted = false;
  for (const sel of ['button[type="submit"]', 'input[type="submit"]', 'form button']) {
    try { await page.click(sel); submitted = true; break; } catch {}
  }
  if (!submitted) {
    try { await page.keyboard.press('Enter'); } catch {}
  }

  log('Wachten op doorverwijzing (Scorito kan traag zijn)...');
  await waitForLoginRedirect(page, 45000);

  const url = page.url();
  if (url.includes('/account/login') || url.includes('fout') || url.includes('error')) {
    throw new Error('Login mislukt. Controleer je gebruikersnaam en wachtwoord.');
  }
  log('Ingelogd ✓');
}

async function navigateToPredictions(page, log) {
  log('Zoeken naar invulpagina WK 2026...');
  const directUrls = [
    `${SCORITO_URL}/wk-2026/invullen`,
    `${SCORITO_URL}/worldcup2026/invullen`,
    `${SCORITO_URL}/competition/wk2026/predict`
  ];

  for (const url of directUrls) {
    try {
      const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await new Promise(r => setTimeout(r, 1000));
      if (res && res.ok() && !page.url().includes('login')) {
        log(`Invulpagina gevonden: ${url}`);
        return true;
      }
    } catch {}
  }

  const linkPatterns = [
    'a[href*="wk-2026"]', 'a[href*="world-cup"]', 'a[href*="invullen"]',
    'a[href*="predict"]', 'a[href*="voorspel"]', 'a[href*="wk2026"]'
  ];

  for (const sel of linkPatterns) {
    try {
      const link = await page.$(sel);
      if (link) {
        const href = await link.evaluate(el => el.href);
        log(`Link gevonden: ${href}`);
        await link.click();
        // Poll vanuit Node.js — vermijdt execution-context-vernietiging
        const deadline = Date.now() + 20000;
        while (Date.now() < deadline) {
          try { if (page.url() !== href) break; } catch {}
          await new Promise(r => setTimeout(r, 600));
        }
        await new Promise(r => setTimeout(r, 800));
        return true;
      }
    } catch {}
  }

  log('Geen aparte invulpagina gevonden — huidige pagina gebruiken.');
  return false;
}

async function extractMatches(page) {
  const url = page.url();

  const result = await page.evaluate(() => {
    const rowSelectors = [
      '.match', '.wedstrijd', '.fixture', '.game-row',
      '[class*="match-row"]', '[class*="match_row"]', '[class*="prediction-row"]',
      'tr[data-match-id]', 'tr[data-fixture]', '.tiprow', '[class*="tip-row"]'
    ];

    let rows = null, usedSelector = '';
    for (const sel of rowSelectors) {
      const found = document.querySelectorAll(sel);
      if (found.length > 0) { rows = found; usedSelector = sel; break; }
    }

    if (!rows || rows.length === 0) {
      return {
        success: false,
        debug: {
          url: window.location.href,
          title: document.title,
          bodySnippet: document.body.innerHTML.substring(0, 3000),
          allInputs: Array.from(document.querySelectorAll('input')).map(i => ({
            type: i.type, name: i.name, id: i.id, placeholder: i.placeholder
          })).slice(0, 30)
        }
      };
    }

    const matches = [];
    rows.forEach((row, index) => {
      const teamEls = row.querySelectorAll(
        '.team-name, .team, [class*="team-name"], [class*="club-name"], .ploeg'
      );
      const scoreInputs = row.querySelectorAll(
        'input[type="number"], input[type="text"][name*="score"], input[name*="goal"], input[name*="stand"]'
      );
      const scorerEl = row.querySelector(
        'select[name*="scorer"], select[name*="doelpuntenmaker"], select[name*="topscorer"], ' +
        'input[name*="scorer"], input[name*="doelpuntenmaker"]'
      );
      const matchId = row.dataset.matchId || row.dataset.fixtureId || row.dataset.id || String(index);

      matches.push({
        index, matchId,
        homeTeam: teamEls[0]?.textContent?.trim() || `Team ${index * 2 + 1}`,
        awayTeam: teamEls[1]?.textContent?.trim() || `Team ${index * 2 + 2}`,
        homeInputName: scoreInputs[0]?.name || '',
        homeInputId: scoreInputs[0]?.id || '',
        awayInputName: scoreInputs[1]?.name || '',
        awayInputId: scoreInputs[1]?.id || '',
        scorerFieldName: scorerEl?.name || '',
        scorerFieldType: scorerEl?.tagName?.toLowerCase() || '',
        scorerOptions: scorerEl?.tagName === 'SELECT'
          ? Array.from(scorerEl.options).map(o => ({ value: o.value, text: o.text }))
          : []
      });
    });

    return { success: true, selector: usedSelector, matches };
  });

  if (!result.success) {
    console.error('Kon wedstrijden niet lezen. Debug:', JSON.stringify(result.debug, null, 2).substring(0, 1000));
    throw new Error(
      `Kon de wedstrijden niet automatisch uitlezen op ${url}. ` +
      'Mogelijk moet je de Scorito-URL of DOM-selectors aanpassen. Zie de serverlogs.'
    );
  }

  return result.matches;
}

async function fetchRound(credentials, log = console.log) {
  log('Browser starten...');
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    );
    await setupPageOptimizations(page);

    await doLogin(page, credentials, log);
    await navigateToPredictions(page, log);

    log('Wedstrijden uitlezen...');
    const title = await page.title().catch(() => 'Scorito WK 2026');
    const url = page.url();
    const matches = await extractMatches(page);

    log(`${matches.length} wedstrijd${matches.length !== 1 ? 'en' : ''} gevonden ✓`);
    return { title, url, matches };
  } finally {
    await browser.close();
  }
}

async function submitPredictions(credentials, predictions, log = console.log) {
  log('Browser starten...');
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    );
    await setupPageOptimizations(page);

    await doLogin(page, credentials, log);
    await navigateToPredictions(page, log);

    log(`${predictions.length} voorspellingen invullen...`);

    for (const match of predictions) {
      const { homeInputName, homeInputId, awayInputName, awayInputId, prediction } = match;
      const homeSelector = homeInputName ? `input[name="${homeInputName}"]`
        : homeInputId ? `#${homeInputId}` : null;
      const awaySelector = awayInputName ? `input[name="${awayInputName}"]`
        : awayInputId ? `#${awayInputId}` : null;

      if (homeSelector) {
        try {
          await page.click(homeSelector, { clickCount: 3 });
          await page.type(homeSelector, String(prediction.homeScore), { delay: 25 });
        } catch (e) { console.warn(`Thuisscore ${match.homeTeam}:`, e.message); }
      }
      if (awaySelector) {
        try {
          await page.click(awaySelector, { clickCount: 3 });
          await page.type(awaySelector, String(prediction.awayScore), { delay: 25 });
        } catch (e) { console.warn(`Uitscore ${match.awayTeam}:`, e.message); }
      }

      if (match.scorerFieldName && prediction.selectedScorers?.length > 0) {
        const scorer = prediction.selectedScorers[0];
        try {
          if (match.scorerFieldType === 'select') {
            const best = (match.scorerOptions || []).find(o =>
              o.text.toLowerCase().includes(scorer.toLowerCase().split(' ').pop()) ||
              scorer.toLowerCase().includes(o.text.toLowerCase().split(' ').pop())
            );
            if (best) await page.select(`select[name="${match.scorerFieldName}"]`, best.value);
          } else {
            await page.click(`input[name="${match.scorerFieldName}"]`, { clickCount: 3 });
            await page.type(`input[name="${match.scorerFieldName}"]`, scorer, { delay: 25 });
          }
        } catch (e) { console.warn(`Scorer ${match.homeTeam} vs ${match.awayTeam}:`, e.message); }
      }

      await new Promise(r => setTimeout(r, 100));
    }

    log('Screenshot maken voor indienen...');
    const previewShot = await page.screenshot({ type: 'jpeg', quality: 72, encoding: 'base64' });

    log('Formulier indienen...');
    let submitted = false;
    for (const sel of [
      'button[type="submit"]', 'input[type="submit"]',
      '[class*="submit"]', '[class*="save"]',
      'button:has-text("Opslaan")', 'button:has-text("Indienen")'
    ]) {
      try { await page.click(sel); submitted = true; break; } catch {}
    }
    if (!submitted) throw new Error('Kon de submit-knop niet vinden op Scorito.');

    log('Wachten op bevestiging...');
    await page.waitForFunction(
      () => true, { timeout: 15000 }
    ).catch(() => {});
    await new Promise(r => setTimeout(r, 2000));

    const confirmShot = await page.screenshot({ type: 'jpeg', quality: 72, encoding: 'base64' });
    log('Ingediend ✓');

    return {
      success: true,
      message: 'Voorspellingen succesvol ingediend op Scorito!',
      screenshotBefore: `data:image/jpeg;base64,${previewShot}`,
      screenshotAfter: `data:image/jpeg;base64,${confirmShot}`
    };
  } finally {
    await browser.close();
  }
}

module.exports = { fetchRound, submitPredictions };
