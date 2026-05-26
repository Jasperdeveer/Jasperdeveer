'use strict';

const puppeteer = require('puppeteer');

const BASE_URL = 'https://schatkamer.beeldengeluid.nl';
const SEARCH_URL = `${BASE_URL}/zoeken`;

let browser = null;

async function getBrowser() {
  if (!browser || !browser.isConnected()) {
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled',
      ],
    });
  }
  return browser;
}

async function newPage() {
  const b = await getBrowser();
  const page = await b.newPage();
  await page.setUserAgent(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
  );
  await page.setExtraHTTPHeaders({ 'Accept-Language': 'nl-NL,nl;q=0.9' });
  return page;
}

/**
 * Search the Schatkamer and return a list of catalog items.
 * @param {string} query  Search term (empty = browse recent)
 * @param {number} skip   Pagination offset
 * @returns {Promise<Array>}
 */
async function search(query, skip = 0) {
  const page = await newPage();
  try {
    const url = query
      ? `${SEARCH_URL}?zoekterm=${encodeURIComponent(query)}`
      : SEARCH_URL;

    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    // Wait for search result cards to appear
    await page.waitForSelector('[class*="SearchResult"], [class*="search-result"], article, .result-item', {
      timeout: 15000,
    }).catch(() => null);

    const items = await page.evaluate((baseUrl) => {
      // Try multiple selector patterns since the site may use CSS modules
      const cards = [
        ...document.querySelectorAll('[class*="SearchResult"]'),
        ...document.querySelectorAll('[class*="search-result"]'),
        ...document.querySelectorAll('article[class*="Card"]'),
        ...document.querySelectorAll('[data-testid*="result"]'),
      ];

      // De-duplicate by href
      const seen = new Set();
      const results = [];

      for (const card of cards) {
        const anchor = card.querySelector('a[href]') || (card.tagName === 'A' ? card : null);
        if (!anchor) continue;

        const href = anchor.getAttribute('href');
        if (!href || seen.has(href)) continue;
        seen.add(href);

        const titleEl = card.querySelector('h1, h2, h3, h4, [class*="title"], [class*="Title"]');
        const imgEl = card.querySelector('img');
        const descEl = card.querySelector('p, [class*="description"], [class*="Description"]');
        const yearEl = card.querySelector('[class*="year"], [class*="Year"], time, [class*="date"]');

        // Encode the path with | as separator so we can reverse it unambiguously
        const id = href.replace(/^\//, '').replace(/\//g, '|');
        const fullUrl = href.startsWith('http') ? href : baseUrl + href;

        results.push({
          id: 'bg:' + id,
          type: 'movie',
          name: titleEl ? titleEl.textContent.trim() : 'Onbekend',
          poster: imgEl ? (imgEl.src || imgEl.dataset.src) : null,
          description: descEl ? descEl.textContent.trim() : '',
          year: yearEl ? yearEl.textContent.trim().match(/\d{4}/)?.[0] : null,
          _url: fullUrl,
        });
      }

      return results;
    }, BASE_URL);

    return items.slice(skip, skip + 100);
  } finally {
    await page.close();
  }
}

/**
 * Get full metadata for a single item.
 * @param {string} bgId  The ID used in the catalog (bg:<path>)
 * @returns {Promise<Object|null>}
 */
async function getMeta(bgId) {
  const path = bgId.replace(/^bg:/, '').replace(/\|/g, '/');
  const url = `${BASE_URL}/${path}`;

  const page = await newPage();
  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    const meta = await page.evaluate((itemUrl, itemId) => {
      const title =
        document.querySelector('h1')?.textContent.trim() ||
        document.title.split('|')[0].trim();

      const description =
        document.querySelector('[class*="description"], [class*="Description"], [class*="synopsis"], p')
          ?.textContent.trim() || '';

      const poster =
        document.querySelector('meta[property="og:image"]')?.content ||
        document.querySelector('[class*="poster"] img, [class*="hero"] img')?.src ||
        null;

      const year = document
        .querySelector('[class*="year"], [class*="Year"], time[datetime]')
        ?.textContent.trim()
        .match(/\d{4}/)?.[0] || null;

      const genre =
        document.querySelector('[class*="genre"], [class*="Genre"]')?.textContent.trim() || null;

      return {
        id: itemId,
        type: 'movie',
        name: title,
        description,
        poster,
        year: year ? parseInt(year) : null,
        genres: genre ? [genre] : ['Archief'],
        links: [{ name: 'Schatkamer', category: 'Beeld & Geluid', url: itemUrl }],
      };
    }, url, bgId);

    return meta;
  } finally {
    await page.close();
  }
}

/**
 * Extract the video stream URL from a Schatkamer player page.
 * @param {string} bgId
 * @returns {Promise<Array>}  Array of Stremio stream objects
 */
async function getStreams(bgId) {
  const path = bgId.replace(/^bg:/, '').replace(/\|/g, '/');
  const url = `${BASE_URL}/${path}`;

  const page = await newPage();
  const streamUrls = [];

  try {
    // Intercept network requests to catch HLS manifests and MP4 files
    await page.setRequestInterception(true);

    page.on('request', (req) => req.continue());

    page.on('response', async (response) => {
      const respUrl = response.url();
      const contentType = response.headers()['content-type'] || '';

      if (
        respUrl.includes('.m3u8') ||
        respUrl.includes('.mp4') ||
        contentType.includes('application/x-mpegurl') ||
        contentType.includes('video/')
      ) {
        if (!streamUrls.find((s) => s.url === respUrl)) {
          streamUrls.push({
            url: respUrl,
            title: contentType.includes('m3u8') || respUrl.includes('m3u8') ? 'HLS Stream' : 'MP4',
          });
        }
      }
    });

    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    // Give the video player extra time to initialize and request the stream
    await new Promise((r) => setTimeout(r, 5000));

    // Also try to find stream URLs in video elements and source tags
    const domStreams = await page.evaluate(() => {
      const found = [];
      for (const el of document.querySelectorAll('video, video source, [src*=".m3u8"], [src*=".mp4"]')) {
        const src = el.src || el.getAttribute('src');
        if (src && (src.includes('.m3u8') || src.includes('.mp4') || src.includes('stream'))) {
          found.push({ url: src, title: 'Video' });
        }
      }
      // Check for common player config objects
      const scripts = document.querySelectorAll('script:not([src])');
      for (const s of scripts) {
        const matches = s.textContent.match(/"(https?:[^"]+\.m3u8[^"]*)"/g);
        if (matches) {
          for (const m of matches) {
            found.push({ url: m.replace(/"/g, ''), title: 'HLS (script)' });
          }
        }
      }
      return found;
    });

    for (const s of domStreams) {
      if (!streamUrls.find((x) => x.url === s.url)) {
        streamUrls.push(s);
      }
    }
  } finally {
    await page.close();
  }

  if (streamUrls.length === 0) {
    return [
      {
        externalUrl: url,
        title: 'Open in browser',
        name: 'Schatkamer',
      },
    ];
  }

  return streamUrls.map((s) => ({
    url: s.url,
    title: s.title,
    name: 'Beeld & Geluid',
    behaviorHints: { notWebReady: false },
  }));
}

module.exports = { search, getMeta, getStreams };
