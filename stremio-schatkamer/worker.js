'use strict';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const BASE = 'https://schatkamer.beeldengeluid.nl';

// Browser-achtige headers zodat Cloudflare de request niet blokkeert
const NL_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  Accept:
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
  'Accept-Encoding': 'gzip, deflate, br',
  Referer: BASE + '/',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'same-origin',
};

function cors(body, status = 200, extra = {}) {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': '*',
      ...extra,
    },
  });
}

function json(obj, status = 200) {
  return cors(JSON.stringify(obj), status);
}

// Cache via Cloudflare KV-ish wrapper (uses the Cache API)
async function withCache(cacheKey, ttl, fn) {
  const cache = caches.default;
  const cached = await cache.match(new Request(`https://cache.local/${cacheKey}`));
  if (cached) return cached.clone();

  const result = await fn();
  const resp = new Response(result, {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': `public, max-age=${ttl}`,
    },
  });
  await cache.put(new Request(`https://cache.local/${cacheKey}`), resp.clone());
  return resp;
}

// ─── HTML scraping helpers ───────────────────────────────────────────────────

/**
 * Haal een pagina op van de Schatkamer en geef de HTML terug als tekst.
 */
async function fetchPage(url) {
  const resp = await fetch(url, {
    headers: NL_HEADERS,
    cf: { cacheEverything: false },
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.text();
}

/**
 * Verwerk de zoekpagina en geef een lijst van catalog-items terug.
 * Gebruikt een eenvoudige regex-parser (Workers hebben geen DOM).
 */
function parseSearchResults(html, skip) {
  const items = [];

  // Probeer <article> of <li> tags te vinden met een href naar /programma/ of /item/
  const cardPattern =
    /<(?:article|li|div)[^>]*class="[^"]*(?:card|result|item|program)[^"]*"[^>]*>[\s\S]*?<\/(?:article|li|div)>/gi;
  const hrefPattern = /href="(\/(?:programma|item|video|film|serie)[^"]+)"/i;
  const titlePattern =
    /<(?:h[1-4]|span)[^>]*class="[^"]*(?:title|naam|name)[^"]*"[^>]*>\s*([\s\S]*?)\s*<\/(?:h[1-4]|span)>/i;
  const imgPattern = /<img[^>]+src="([^"]+(?:jpg|jpeg|png|webp)[^"]*)"[^>]*>/i;
  const yearPattern = /\b(19[2-9]\d|20[0-2]\d)\b/;

  let match;
  while ((match = cardPattern.exec(html)) !== null) {
    const block = match[0];
    const hrefM = hrefPattern.exec(block);
    if (!hrefM) continue;

    const href = hrefM[1];
    const titleM = titlePattern.exec(block);
    const imgM = imgPattern.exec(block);
    const yearM = yearPattern.exec(block);

    const id = 'bg:' + href.replace(/^\//, '').replace(/\//g, '|');
    items.push({
      id,
      type: 'movie',
      name: titleM ? decodeHtml(titleM[1].replace(/<[^>]+>/g, '').trim()) : href.split('/').pop(),
      poster: imgM ? imgM[1] : undefined,
      year: yearM ? parseInt(yearM[1]) : undefined,
    });
  }

  // Fallback: zoek alle links naar programma-pagina's als er geen cards zijn
  if (items.length === 0) {
    const linkPattern = /href="(\/(?:programma|item|video|film|serie)\/[^"]+)"/gi;
    const seen = new Set();
    let lm;
    while ((lm = linkPattern.exec(html)) !== null) {
      const href = lm[1];
      if (seen.has(href)) continue;
      seen.add(href);
      const id = 'bg:' + href.replace(/^\//, '').replace(/\//g, '|');
      items.push({ id, type: 'movie', name: href.split('/').pop().replace(/-/g, ' ') });
    }
  }

  return items.slice(skip, skip + 100);
}

/**
 * Haal metadata op van een individuele programmapagina.
 */
function parseMeta(html, bgId, pageUrl) {
  const titleM = /<h1[^>]*>\s*([\s\S]*?)\s*<\/h1>/i.exec(html);
  const ogImage = /property="og:image"\s+content="([^"]+)"/i.exec(html);
  const ogDesc = /property="og:description"\s+content="([^"]+)"/i.exec(html);
  const yearM = /\b(19[2-9]\d|20[0-2]\d)\b/.exec(html);

  return {
    id: bgId,
    type: 'movie',
    name: titleM ? decodeHtml(titleM[1].replace(/<[^>]+>/g, '').trim()) : bgId,
    poster: ogImage ? ogImage[1] : undefined,
    description: ogDesc ? decodeHtml(ogDesc[1]) : undefined,
    year: yearM ? parseInt(yearM[1]) : undefined,
    genres: ['Archief', 'Nederland'],
    links: [{ name: 'Open in browser', category: 'Schatkamer', url: pageUrl }],
  };
}

/**
 * Zoek naar stream-URLs in de HTML (video tags, JSON-LD, script variabelen).
 */
function parseStreams(html, pageUrl) {
  const streams = [];

  // <video src="..."> of <source src="...">
  const videoSrcPattern = /<(?:video|source)[^>]+src="([^"]+)"/gi;
  let m;
  while ((m = videoSrcPattern.exec(html)) !== null) {
    const src = m[1];
    if (src.match(/\.(m3u8|mp4|webm)/i) || src.includes('stream')) {
      streams.push({ url: src, title: src.includes('m3u8') ? 'HLS' : 'Video' });
    }
  }

  // JSON in script tags: zoek naar "src":"..." of "url":"..." met stream-achtige URLs
  const scriptPattern = /<script[^>]*>([\s\S]*?)<\/script>/gi;
  while ((m = scriptPattern.exec(html)) !== null) {
    const script = m[1];
    const urlMatches = script.matchAll(/"(?:src|url|hls|stream|file|source)":\s*"(https?[^"]+\.(?:m3u8|mp4)[^"]*)"/gi);
    for (const um of urlMatches) {
      streams.push({ url: um[1], title: um[1].includes('m3u8') ? 'HLS' : 'MP4' });
    }
  }

  // JSON-LD contentUrl
  const jsonLdM = /<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/i.exec(html);
  if (jsonLdM) {
    try {
      const data = JSON.parse(jsonLdM[1]);
      const url = data.contentUrl || data.embedUrl || data?.video?.contentUrl;
      if (url) streams.push({ url, title: 'JSON-LD' });
    } catch (_) {}
  }

  // De-dupliceer
  const seen = new Set();
  const unique = streams.filter((s) => {
    if (seen.has(s.url)) return false;
    seen.add(s.url);
    return true;
  });

  if (unique.length === 0) {
    return [{ externalUrl: pageUrl, name: 'Open in browser', title: 'Schatkamer' }];
  }

  return unique.map((s) => ({
    url: s.url,
    title: s.title,
    name: 'Beeld & Geluid',
    behaviorHints: { notWebReady: false },
  }));
}

function decodeHtml(str) {
  return str
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ');
}

// ─── Manifest ────────────────────────────────────────────────────────────────

const MANIFEST = {
  id: 'nl.beeldengeluid.schatkamer',
  version: '1.0.0',
  name: 'Beeld & Geluid Schatkamer',
  description:
    "Gratis toegang tot het archief van Beeld & Geluid – meer dan 700.000 Nederlandse radio- en tv-programma's (1920–2020).",
  logo: 'https://www.beeldengeluid.nl/favicon.ico',
  catalogs: [
    {
      type: 'movie',
      id: 'bg-browse',
      name: 'Schatkamer',
      extra: [
        { name: 'search', isRequired: false },
        { name: 'skip', isRequired: false },
      ],
    },
  ],
  resources: ['catalog', 'meta', 'stream'],
  types: ['movie'],
  idPrefixes: ['bg:'],
  behaviorHints: { adult: false, p2p: false },
};

// ─── Router ──────────────────────────────────────────────────────────────────

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return cors('', 204);
    }

    // /manifest.json
    if (path === '/manifest.json') {
      return json(MANIFEST);
    }

    // /catalog/movie/bg-browse.json?extra=...
    const catalogM = path.match(/^\/catalog\/movie\/bg-browse\.json$/);
    if (catalogM) {
      const extra = url.searchParams.get('extra') || '';
      const extraDecoded = Object.fromEntries(
        decodeURIComponent(extra)
          .split('&')
          .filter(Boolean)
          .map((p) => p.split('='))
      );
      const query = extraDecoded.search || '';
      const skip = parseInt(extraDecoded.skip || '0', 10);

      const cacheKey = `catalog:${query}:${skip}`;
      const cached = await caches.default.match(new Request(`https://cache.local/${cacheKey}`));
      if (cached) {
        const data = await cached.json();
        return json({ metas: data });
      }

      try {
        const pageUrl = query
          ? `${BASE}/zoeken?zoekterm=${encodeURIComponent(query)}`
          : `${BASE}/zoeken`;
        const html = await fetchPage(pageUrl);
        const metas = parseSearchResults(html, skip);

        const resp = new Response(JSON.stringify(metas), {
          headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=600' },
        });
        await caches.default.put(new Request(`https://cache.local/${cacheKey}`), resp.clone());

        return json({ metas });
      } catch (err) {
        console.error('[catalog]', err.message);
        return json({ metas: [] });
      }
    }

    // /meta/movie/bg:....json
    const metaM = path.match(/^\/meta\/movie\/(bg:[^.]+)\.json$/);
    if (metaM) {
      const bgId = decodeURIComponent(metaM[1]);
      const pagePath = bgId.replace(/^bg:/, '').replace(/\|/g, '/');
      const pageUrl = `${BASE}/${pagePath}`;

      const cacheKey = `meta:${bgId}`;
      const cached = await caches.default.match(new Request(`https://cache.local/${cacheKey}`));
      if (cached) {
        const data = await cached.json();
        return json({ meta: data });
      }

      try {
        const html = await fetchPage(pageUrl);
        const meta = parseMeta(html, bgId, pageUrl);

        const resp = new Response(JSON.stringify(meta), {
          headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=3600' },
        });
        await caches.default.put(new Request(`https://cache.local/${cacheKey}`), resp.clone());

        return json({ meta });
      } catch (err) {
        console.error('[meta]', err.message);
        return json({ meta: null });
      }
    }

    // /stream/movie/bg:....json
    const streamM = path.match(/^\/stream\/movie\/(bg:[^.]+)\.json$/);
    if (streamM) {
      const bgId = decodeURIComponent(streamM[1]);
      const pagePath = bgId.replace(/^bg:/, '').replace(/\|/g, '/');
      const pageUrl = `${BASE}/${pagePath}`;

      const cacheKey = `stream:${bgId}`;
      const cached = await caches.default.match(new Request(`https://cache.local/${cacheKey}`));
      if (cached) {
        const data = await cached.json();
        return json({ streams: data });
      }

      try {
        const html = await fetchPage(pageUrl);
        const streams = parseStreams(html, pageUrl);

        const ttl = streams.some((s) => s.url) ? 1800 : 60;
        const resp = new Response(JSON.stringify(streams), {
          headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${ttl}` },
        });
        await caches.default.put(new Request(`https://cache.local/${cacheKey}`), resp.clone());

        return json({ streams });
      } catch (err) {
        console.error('[stream]', err.message);
        return json({ streams: [] });
      }
    }

    return json({ error: 'Not found' }, 404);
  },
};
