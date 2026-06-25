'use strict';
const puppeteer = require('puppeteer');
const { execSync } = require('child_process');

const SCORITO_URL = 'https://www.scorito.com';

function findChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  // Probeer pre-installed Playwright Chromium (beschikbaar in cloud-omgeving)
  try {
    const found = execSync(
      'find /opt/pw-browsers -name "chrome" -o -name "chromium" 2>/dev/null | grep -v ".zip" | head -1',
      { timeout: 3000 }
    ).toString().trim();
    if (found) { console.log('Chromium gevonden:', found); return found; }
  } catch {}
  // Systeembrowser
  for (const cmd of ['chromium-browser', 'chromium', 'google-chrome']) {
    try {
      const found = execSync(`which ${cmd} 2>/dev/null`, { timeout: 2000 }).toString().trim();
      if (found) return found;
    } catch {}
  }
  return undefined;
}

async function launchBrowser(headless = true) {
  const executablePath = findChromium();
  return puppeteer.launch({
    headless: headless ? 'new' : false,
    executablePath,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--lang=nl-NL,nl'
    ]
  });
}

async function doLogin(page, credentials) {
  console.log('Navigeren naar Scorito login...');
  await page.goto(`${SCORITO_URL}/account/login`, { waitUntil: 'networkidle2', timeout: 30000 });

  // Probeer meerdere selector-patronen voor het loginformulier
  const userSelectors = [
    'input[name="username"]',
    'input[name="email"]',
    'input[type="email"]',
    'input[id*="username"]',
    'input[id*="email"]',
    'input[placeholder*="gebruikersnaam" i]',
    'input[placeholder*="e-mail" i]',
    'input[placeholder*="email" i]'
  ];
  const passSelectors = [
    'input[name="password"]',
    'input[type="password"]',
    'input[id*="password"]'
  ];

  let usernameInput = null;
  for (const sel of userSelectors) {
    usernameInput = await page.$(sel);
    if (usernameInput) { console.log('Gebruikersnaam-veld:', sel); break; }
  }
  let passwordInput = null;
  for (const sel of passSelectors) {
    passwordInput = await page.$(sel);
    if (passwordInput) { console.log('Wachtwoord-veld:', sel); break; }
  }

  if (!usernameInput || !passwordInput) {
    throw new Error(
      'Kan het loginformulier niet vinden op Scorito. ' +
      'Controleer of de URL correct is of dat Scorito de paginastructuur heeft gewijzigd.'
    );
  }

  await usernameInput.click({ clickCount: 3 });
  await usernameInput.type(credentials.username, { delay: 50 });
  await passwordInput.click({ clickCount: 3 });
  await passwordInput.type(credentials.password, { delay: 50 });

  // Klik submit
  let submitted = false;
  for (const sel of ['button[type="submit"]', 'input[type="submit"]', 'form button']) {
    try { await page.click(sel); submitted = true; break; } catch {}
  }
  if (!submitted) await page.keyboard.press('Enter');

  await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 20000 });

  const url = page.url();
  if (url.includes('login') || url.includes('fout') || url.includes('error')) {
    throw new Error('Login mislukt. Controleer je gebruikersnaam en wachtwoord.');
  }
  console.log('Ingelogd. Huidige pagina:', url);
}

// Zoek naar de WK-invulpagina en navigeer er naartoe
async function navigateToPredictions(page) {
  // Probeer directe URL-patronen die Scorito mogelijk gebruikt
  const directUrls = [
    `${SCORITO_URL}/wk-2026/invullen`,
    `${SCORITO_URL}/worldcup2026/invullen`,
    `${SCORITO_URL}/competition/wk2026/predict`
  ];

  for (const url of directUrls) {
    try {
      const res = await page.goto(url, { waitUntil: 'networkidle2', timeout: 8000 });
      if (res && res.ok() && !page.url().includes('login')) {
        console.log('Voorspellingspagina gevonden via directe URL:', url);
        return true;
      }
    } catch {}
  }

  // Zoek via linktekst op de huidige pagina
  const linkPatterns = [
    'a[href*="wk-2026"]',
    'a[href*="world-cup"]',
    'a[href*="weltmeisterschaft"]',
    'a[href*="invullen"]',
    'a[href*="predict"]',
    'a[href*="voorspel"]'
  ];

  for (const sel of linkPatterns) {
    try {
      const link = await page.$(sel);
      if (link) {
        const href = await link.evaluate(el => el.href);
        console.log('WK/invullen link gevonden:', href);
        await link.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 });
        return true;
      }
    } catch {}
  }

  console.warn('Geen voorspellingspagina gevonden via links. Gebruik huidige pagina.');
  return false;
}

// Lees wedstrijddata uit het Scorito-formulier
async function extractMatches(page) {
  const url = page.url();
  console.log('Wedstrijden lezen van:', url);

  const result = await page.evaluate(() => {
    // Probeer meerdere selectors voor wedstrijdrijen
    const rowSelectors = [
      '.match', '.wedstrijd', '.fixture', '.game-row',
      '[class*="match-row"]', '[class*="match_row"]', '[class*="prediction-row"]',
      'tr[data-match-id]', 'tr[data-fixture]', '.tiprow', '[class*="tip-row"]'
    ];

    let rows = null;
    let usedSelector = '';
    for (const sel of rowSelectors) {
      const found = document.querySelectorAll(sel);
      if (found.length > 0) { rows = found; usedSelector = sel; break; }
    }

    if (!rows || rows.length === 0) {
      // Geen rijen gevonden: geef de paginastructuur terug zodat we kunnen debuggen
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
      const homeEl = teamEls[0];
      const awayEl = teamEls[1];

      const scoreInputs = row.querySelectorAll(
        'input[type="number"], input[type="text"][name*="score"], input[name*="goal"], input[name*="stand"]'
      );

      const homeInput = scoreInputs[0];
      const awayInput = scoreInputs[1];

      // Scorer dropdown of tekstveld
      const scorerEl = row.querySelector(
        'select[name*="scorer"], select[name*="doelpuntenmaker"], select[name*="topscorer"], ' +
        'input[name*="scorer"], input[name*="doelpuntenmaker"]'
      );

      // Probeer een unieke rij-identifier te vinden
      const matchId = row.dataset.matchId || row.dataset.fixtureId ||
                      row.dataset.id || String(index);

      matches.push({
        index,
        matchId,
        homeTeam: homeEl?.textContent?.trim() || `Team ${index * 2 + 1}`,
        awayTeam: awayEl?.textContent?.trim() || `Team ${index * 2 + 2}`,
        homeInputName: homeInput?.name || '',
        homeInputId: homeInput?.id || '',
        awayInputName: awayInput?.name || '',
        awayInputId: awayInput?.id || '',
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
    console.error('Kon wedstrijden niet lezen. Debug info:', JSON.stringify(result.debug, null, 2).substring(0, 1000));
    throw new Error(
      `Kon de wedstrijden niet automatisch uitlezen op ${url}. ` +
      'Mogelijk moet je de Scorito-URL of DOM-selectors aanpassen. ' +
      'Zie de serverlogs voor debug-info.'
    );
  }

  console.log(`${result.matches.length} wedstrijden gevonden via selector: ${result.selector}`);
  return result.matches;
}

// Haal de huidige ronde op van Scorito
async function fetchRound(credentials) {
  const browser = await launchBrowser(true);
  try {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    );

    await doLogin(page, credentials);
    await navigateToPredictions(page);

    const title = await page.title();
    const url = page.url();
    const matches = await extractMatches(page);

    return { title, url, matches };
  } finally {
    await browser.close();
  }
}

// Dien goedgekeurde voorspellingen in via Puppeteer
async function submitPredictions(credentials, predictions) {
  // Headless false: gebruiker kan het zien
  const browser = await launchBrowser(false);
  try {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    );

    await doLogin(page, credentials);
    await navigateToPredictions(page);

    console.log(`${predictions.length} voorspellingen invullen...`);

    for (const match of predictions) {
      const { homeInputName, homeInputId, awayInputName, awayInputId, prediction } = match;

      // Thuisscore invullen
      const homeSelector = homeInputName
        ? `input[name="${homeInputName}"]`
        : homeInputId ? `#${homeInputId}` : null;

      const awaySelector = awayInputName
        ? `input[name="${awayInputName}"]`
        : awayInputId ? `#${awayInputId}` : null;

      if (homeSelector) {
        try {
          await page.click(homeSelector, { clickCount: 3 });
          await page.type(homeSelector, String(prediction.homeScore), { delay: 30 });
        } catch (e) {
          console.warn(`Kon thuisscore niet invullen voor ${match.homeTeam}:`, e.message);
        }
      }

      if (awaySelector) {
        try {
          await page.click(awaySelector, { clickCount: 3 });
          await page.type(awaySelector, String(prediction.awayScore), { delay: 30 });
        } catch (e) {
          console.warn(`Kon uitscore niet invullen voor ${match.awayTeam}:`, e.message);
        }
      }

      // Topscorer invullen (als het veld aanwezig is)
      if (match.scorerFieldName && prediction.selectedScorers?.length > 0) {
        const scorer = prediction.selectedScorers[0];
        try {
          if (match.scorerFieldType === 'select') {
            // Zoek beste overeenkomst in de dropdown
            const opts = match.scorerOptions || [];
            const best = opts.find(o =>
              o.text.toLowerCase().includes(scorer.toLowerCase().split(' ').pop()) ||
              scorer.toLowerCase().includes(o.text.toLowerCase().split(' ').pop())
            );
            if (best) {
              await page.select(`select[name="${match.scorerFieldName}"]`, best.value);
            }
          } else {
            await page.click(`input[name="${match.scorerFieldName}"]`, { clickCount: 3 });
            await page.type(`input[name="${match.scorerFieldName}"]`, scorer, { delay: 30 });
          }
        } catch (e) {
          console.warn(`Kon scorer niet invullen voor ${match.homeTeam} vs ${match.awayTeam}:`, e.message);
        }
      }

      await new Promise(r => setTimeout(r, 150));
    }

    console.log('Klaar met invullen. Browser blijft open zodat je het kunt controleren.');
    console.log('Klik zelf op Opslaan/Bevestigen in de browser om te bevestigen.');

    // Geef de browser 60 seconden om de gebruiker te laten controleren
    await new Promise(r => setTimeout(r, 60000));

    return {
      success: true,
      message: 'Voorspellingen zijn ingevuld. Controleer de browser en klik op Opslaan/Bevestigen.'
    };
  } catch (err) {
    await browser.close();
    throw err;
  }
  // Browser wordt na 60s of bij fout gesloten
}

module.exports = { fetchRound, submitPredictions };
