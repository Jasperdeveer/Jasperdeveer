'use strict';
const puppeteer = require('puppeteer');
const { execSync } = require('child_process');

const SCORITO_URL = 'https://www.scorito.com';
const MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';

// Scorito React SPA: score-inputs hebben deze CSS-klasse (gevonden in de JS-bundle)
const PRED_INPUT_SEL = 'input[class*="matchPredictionInput"]';

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
      '--disable-features=VizDisplayCompositor',
      '--disable-ipc-flooding-protection',
      '--mute-audio',
      '--lang=nl-NL,nl'
    ]
  });
}

async function setupAntiDetection(page) {
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['nl-NL', 'nl', 'en'] });
    window.chrome = { runtime: {} };
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
      params.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : origQuery(params);
  });
}

// Blokkeer alleen tracking/analytics — laat alle app-JS door zodat React kan renderen
// termly.io bewust NIET geblokkeerd: Termly consent JS moet laden zodat de banner
// afwijsbaar is en React zijn content kan renderen.
async function setupPageOptimizations(page) {
  await page.setRequestInterception(true);
  page.on('request', req => {
    const rt = req.resourceType();
    const url = req.url();
    if (rt === 'font' || rt === 'media') {
      req.abort();
    } else if (
      url.includes('google-analytics') || url.includes('gtag') ||
      url.includes('doubleclick') || url.includes('facebook.net') ||
      url.includes('/beacon') || url.includes('newrelic')
    ) {
      req.abort();
    } else {
      req.continue();
    }
  });
}

// Sluit de Termly cookie-melding als die aanwezig is.
// De melding blokkeert React van het renderen van app-content.
async function dismissCookieConsent(page, log) {
  try {
    await page.waitForSelector(
      '[data-tid="banner-decline"], [data-tid="banner-accept"], button[id*="termly"], .termly-styles-consent-banner button',
      { timeout: 6000 }
    );
    const clicked = await page.evaluate(() => {
      const selectors = [
        '[data-tid="banner-decline"]',
        '[data-tid="banner-accept"]',
        'button[id*="termly"]',
        '.termly-styles-consent-banner button'
      ];
      for (const sel of selectors) {
        const btn = document.querySelector(sel);
        if (btn) { btn.click(); return true; }
      }
      return false;
    });
    if (clicked) {
      await new Promise(r => setTimeout(r, 800));
      if (log) log('Cookie-melding gesloten ✓');
    }
  } catch {
    // Geen cookie-melding aanwezig — doorgaan
  }
}

// Poll page.url() vanuit Node.js — overleeft React-navigatie (execution-context-safe)
async function waitForLoginRedirect(page, timeout = 45000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    try {
      if (!page.url().includes('/login')) {
        await new Promise(r => setTimeout(r, 800));
        return;
      }
    } catch {}
    await new Promise(r => setTimeout(r, 600));
  }
  try {
    if (page.url().includes('/login')) {
      throw new Error('Login timeout na 45s. Controleer je gebruikersnaam en wachtwoord.');
    }
  } catch (e) {
    if (e.message.includes('timeout')) throw e;
  }
}

async function safeGoto(page, url, waitMs = 5000) {
  page.goto(url).catch(() => {});
  await new Promise(r => setTimeout(r, waitMs));
}

async function doLogin(page, credentials, log) {
  const loginUrls = [
    `${SCORITO_URL}/account/login`,
    `${SCORITO_URL}/login`,
    'https://mobile.scorito.com/login'
  ];

  let foundLogin = false;
  for (const loginUrl of loginUrls) {
    log(`Navigeren naar ${loginUrl}...`);
    await safeGoto(page, loginUrl, 3000);

    // Scorito toont eerst een Termly cookie-melding die React blokkeert van renderen.
    // Sluit de melding zodat de login-form verschijnt.
    await dismissCookieConsent(page, log);

    // Scorito is een React SPA — wacht tot de login-form gerenderd is (max 15s)
    try {
      await page.waitForSelector('input', { timeout: 15000 });
    } catch {}
    const currentUrl = page.url();
    log(`Pagina geladen: ${currentUrl}`);
    const hasInputs = await page.$('input').then(el => !!el).catch(() => false);
    if (hasInputs) { foundLogin = true; break; }
    log('Geen inputs gevonden, volgende URL proberen...');
  }
  if (!foundLogin) {
    throw new Error('Kon de Scorito loginpagina niet laden. Controleer je internetverbinding.');
  }

  log('Loginformulier invullen en indienen...');
  const loginResult = await page.evaluate((username, password) => {
    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"])'));
    const emailEl = inputs.find(i =>
      i.type === 'email' || i.type === 'text' ||
      /email|user|naam/i.test(i.name + i.id + i.placeholder)
    );
    const passEl = inputs.find(i => i.type === 'password');
    if (!emailEl || !passEl) {
      return { ok: false, found: inputs.map(i => `${i.type}|${i.name}|${i.id}|${i.placeholder}`) };
    }
    function fill(el, value) {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
      setter.set.call(el, value);
      el.dispatchEvent(new Event('input',  { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    fill(emailEl, username);
    fill(passEl, password);
    const btn = document.querySelector('button[type="submit"]') ||
                document.querySelector('form button') ||
                document.querySelector('button');
    if (btn) btn.click();
    else if (passEl.form) passEl.form.submit();
    return { ok: true };
  }, credentials.username, credentials.password);

  if (!loginResult.ok) {
    const found = (loginResult.found || []).join(' / ');
    console.error('Aanwezige inputs:', found);
    log('Inputs gevonden: ' + found);
    throw new Error('Kan het loginformulier niet vinden op Scorito.');
  }

  log('Wachten op doorverwijzing (Scorito kan traag zijn)...');
  await waitForLoginRedirect(page, 45000);

  if (page.url().includes('/login')) {
    throw new Error('Login mislukt. Controleer je gebruikersnaam en wachtwoord.');
  }
  log('Ingelogd ✓');
}

async function navigateToPredictions(page, log) {
  log('Navigeren naar WK 2026 invulpagina...');

  // Correcte URL voor de resterende WK 2026 wedstrijden (marketId=301, phase=4)
  const directUrls = [
    `${SCORITO_URL}/footballtournament/301/4`,
    'https://mobile.scorito.com/wk-2026/invullen',
    'https://mobile.scorito.com/worldcup2026/invullen',
    `${SCORITO_URL}/wk-2026/invullen`,
    `${SCORITO_URL}/worldcup2026/invullen`,
  ];

  for (const url of directUrls) {
    await safeGoto(page, url, 8000);
    const currentUrl = page.url();
    if (!currentUrl.includes('/login') && !currentUrl.includes('/account/login')) {
      // Sluit cookie-melding als die ook op de invulpagina verschijnt
      await dismissCookieConsent(page, log);
      log(`Invulpagina geladen: ${currentUrl}`);
      return true;
    }
    log(`Omgeleid naar login bij ${url} — volgende proberen...`);
  }

  log('Geen invulpagina gevonden — doorgaan met huidige pagina.');
  return false;
}

// Extraheert wedstrijden uit de Scorito React SPA.
// Scorito gebruikt inputs met klasse 'matchPredictionInput-ciMjLN' (geen name/id).
// Elke wedstrijd heeft 2 inputs: thuisscore (even index) en uitscore (oneven index).
async function extractMatches(page) {
  const url = page.url();

  // Scroll naar beneden zodat React lazy-loading alle wedstrijden rendert
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)).catch(() => {});
  await new Promise(r => setTimeout(r, 1000));
  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});

  const result = await page.evaluate((inputSel) => {
    const inputs = Array.from(document.querySelectorAll(inputSel));

    if (inputs.length === 0) {
      return {
        success: false,
        debug: {
          url: window.location.href,
          title: document.title,
          allInputs: Array.from(document.querySelectorAll('input')).map(i => ({
            type: i.type,
            class: i.className.substring(0, 100),
            name: i.name,
            id: i.id,
            placeholder: i.placeholder
          })).slice(0, 25),
          buttons: Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).slice(0, 20),
          bodySnippet: document.body.innerHTML.substring(0, 4000)
        }
      };
    }

    const matches = [];
    for (let i = 0; i + 1 < inputs.length; i += 2) {
      const homeInput = inputs[i];

      // DOM-structuur: input → div (scores-rij) → div (outer PredictionInput-component)
      // Teamnamen staan hoger in de boom — zoek naar leaf-nodes met tekst
      let homeTeam = `Thuisteam ${i / 2 + 1}`;
      let awayTeam = `Uitteam ${i / 2 + 1}`;

      let container = homeInput.parentElement?.parentElement?.parentElement;
      for (let depth = 0; depth < 10 && container; depth++) {
        const leafTexts = Array.from(container.querySelectorAll('span, p'))
          .filter(el => el.children.length === 0)
          .map(el => el.textContent.trim())
          .filter(t =>
            t.length >= 2 && t.length <= 35 &&
            !/^[\d\s.:%-]+$/.test(t) &&
            !t.includes('.') // filter translation keys zoals 'Common.Confirm'
          );

        if (leafTexts.length >= 2) {
          homeTeam = leafTexts[0];
          awayTeam = leafTexts[leafTexts.length - 1];
          break;
        }
        container = container.parentElement;
      }

      matches.push({
        index: i / 2,
        matchId: String(i / 2),
        homeTeam,
        awayTeam,
        homeInputName: '',
        homeInputId: '',
        awayInputName: '',
        awayInputId: '',
        scorerFieldName: '',
        scorerFieldType: '',
        scorerOptions: []
      });
    }

    return { success: true, inputCount: inputs.length, matches };
  }, PRED_INPUT_SEL);

  if (!result.success) {
    console.error('extractMatches debug:', JSON.stringify(result.debug, null, 2).substring(0, 2000));
    throw new Error(
      `Kon de wedstrijden niet automatisch uitlezen op ${url}. ` +
      'Zie de serverlogs voor debug-informatie over de aanwezige DOM-elementen.'
    );
  }

  return result.matches;
}

async function fetchRound(credentials, log = console.log) {
  log('Browser starten...');
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    await setupAntiDetection(page);
    await page.setViewport({ width: 390, height: 844 });
    await page.setUserAgent(MOBILE_UA);
    await setupPageOptimizations(page);

    await doLogin(page, credentials, log);
    await navigateToPredictions(page, log);

    // Wacht op React-render: wacht maximaal 20s op de score-inputs
    log('Wachten op React-render van wedstrijdinputs...');
    await page.waitForSelector(PRED_INPUT_SEL, { timeout: 20000 }).catch(() => {
      log('Inputs nog niet zichtbaar na 20s — toch doorgaan...');
    });
    // Extra wachttijd voor volledige render
    await new Promise(r => setTimeout(r, 2000));

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
    await setupAntiDetection(page);
    await page.setViewport({ width: 390, height: 844 });
    await page.setUserAgent(MOBILE_UA);
    await setupPageOptimizations(page);

    await doLogin(page, credentials, log);
    await navigateToPredictions(page, log);

    // Wacht op score-inputs
    log('Wachten op invulvelden...');
    await page.waitForSelector(PRED_INPUT_SEL, { timeout: 20000 }).catch(() => {
      log('Inputs nog niet zichtbaar — toch doorgaan...');
    });
    await new Promise(r => setTimeout(r, 2000));

    log(`${predictions.length} voorspellingen invullen via React-inputs...`);

    for (let i = 0; i < predictions.length; i++) {
      const match = predictions[i];
      const { homeScore, awayScore } = match.prediction;
      const matchIdx = typeof match.index === 'number' ? match.index : i;

      try {
        // Scroll naar het invoerveld zodat het in view komt
        await page.evaluate((inputSel, idx) => {
          const inputs = Array.from(document.querySelectorAll(inputSel));
          const el = inputs[idx * 2];
          if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
        }, PRED_INPUT_SEL, matchIdx);
        await new Promise(r => setTimeout(r, 200));

        // Vul thuisscore en uitscore via React's native setter
        const fillResult = await page.evaluate((inputSel, idx, home, away) => {
          const inputs = Array.from(document.querySelectorAll(inputSel));
          const homeInput = inputs[idx * 2];
          const awayInput = inputs[idx * 2 + 1];
          if (!homeInput || !awayInput) return { ok: false, total: inputs.length };

          function fillReact(el, value) {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
            setter.set.call(el, String(value));
            el.dispatchEvent(new Event('input',  { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          }

          fillReact(homeInput, home);
          fillReact(awayInput, away);
          return { ok: true };
        }, PRED_INPUT_SEL, matchIdx, homeScore, awayScore);

        if (!fillResult.ok) {
          console.warn(`Match ${matchIdx} (${match.homeTeam}): inputs niet gevonden (totaal: ${fillResult.total})`);
          continue;
        }

        // Wacht op React state-update
        await new Promise(r => setTimeout(r, 350));

        // Klik de Bevestig-knop: zit 2 niveaus boven de eerste input van dit match
        // DOM: input → div (scores-rij) → div (outer) → button
        const clicked = await page.evaluate((inputSel, idx) => {
          const inputs = Array.from(document.querySelectorAll(inputSel));
          const homeInput = inputs[idx * 2];
          if (!homeInput) return false;

          const outerDiv = homeInput.parentElement?.parentElement;
          if (!outerDiv) return false;

          // Zoek een niet-disabled button in de outer container
          const btn = outerDiv.querySelector('button:not([disabled])') ||
                      outerDiv.querySelector('button');
          if (!btn) return false;

          btn.click();
          return true;
        }, PRED_INPUT_SEL, matchIdx);

        if (clicked) {
          log(`${match.homeTeam} ${homeScore}-${awayScore} ${match.awayTeam} ✓`);
        } else {
          log(`${match.homeTeam} ${homeScore}-${awayScore} ${match.awayTeam} (geen bevestig-knop gevonden)`);
        }

        // Wacht op API-call
        await new Promise(r => setTimeout(r, 400));

      } catch (e) {
        console.warn(`Match ${matchIdx} fout:`, e.message);
        log(`Fout bij ${match.homeTeam} vs ${match.awayTeam}: ${e.message}`);
      }
    }

    log('Screenshot maken...');
    const previewShot = await page.screenshot({ type: 'jpeg', quality: 72, encoding: 'base64' });

    // Wacht even zodat alle API-calls afgerond zijn
    await new Promise(r => setTimeout(r, 2000));

    const confirmShot = await page.screenshot({ type: 'jpeg', quality: 72, encoding: 'base64' });
    log('Alle voorspellingen ingediend ✓');

    return {
      success: true,
      message: `${predictions.length} voorspellingen succesvol ingediend op Scorito!`,
      screenshotBefore: `data:image/jpeg;base64,${previewShot}`,
      screenshotAfter: `data:image/jpeg;base64,${confirmShot}`
    };
  } finally {
    await browser.close();
  }
}

module.exports = { fetchRound, submitPredictions };
