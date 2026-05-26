'use strict';

const BASE = 'https://schatkamer.beeldengeluid.nl';

const NL_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
  'Accept-Encoding': 'gzip, deflate, br',
  Referer: BASE + '/',
};

// ─── ID helpers ──────────────────────────────────────────────────────────────
// ID = "bg:" + base64url(path)  →  veilig in alle URL-contexten

function encodeId(path) {
  const b64 = btoa(unescape(encodeURIComponent(path)));
  return 'bg:' + b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function decodeId(bgId) {
  const b64 = bgId.replace(/^bg:/, '').replace(/-/g, '+').replace(/_/g, '/');
  try {
    return decodeURIComponent(escape(atob(b64)));
  } catch {
    return bgId.replace(/^bg:/, '').replace(/\|/g, '/');
  }
}

// ─── HTTP helpers ─────────────────────────────────────────────────────────────

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': '*',
    },
  });
}

async function fetchPage(url) {
  const resp = await fetch(url, { headers: NL_HEADERS });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.text();
}

function decodeHtml(s) {
  return s
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ');
}

// ─── Parsers ──────────────────────────────────────────────────────────────────

function parseSearchResults(html, skip) {
  const items = [];
  const seen = new Set();

  const nextDataM = /<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i.exec(html);
  if (nextDataM) {
    try {
      const data = JSON.parse(nextDataM[1]);
      const hits =
        data?.props?.pageProps?.results ||
        data?.props?.pageProps?.items ||
        data?.props?.pageProps?.hits ||
        [];
      for (const hit of hits) {
        const href = hit.url || hit.slug || hit.path || hit.id;
        if (!href || seen.has(href)) continue;
        seen.add(href);
        items.push({
          id: encodeId(href.replace(/^\//, '')),
          type: 'movie',
          name: hit.title || hit.name || hit.label || href,
          poster: hit.image || hit.thumbnail || hit.poster || undefined,
          year: hit.year || hit.publicationYear || undefined,
        });
      }
    } catch (_) {}
  }

  if (items.length === 0) {
    const EXCLUDE = /^\/(zoeken|veelgestelde-vragen|over|contact|verhaal|collectie|#)/;
    const linkRe = /href="(\/[a-z0-9][^"#?]{3,}?)"/gi;
    let m;
    while ((m = linkRe.exec(html)) !== null) {
      const href = m[1];
      if (EXCLUDE.test(href) || seen.has(href)) continue;
      seen.add(href);

      const start = Math.max(0, m.index - 400);
      const block = html.slice(start, m.index + 600);

      const titleM =
        /<(?:h[1-4]|span|strong|p)[^>]*>\s*([^<]{3,80})\s*<\/(?:h[1-4]|span|strong|p)>/i.exec(block);
      const imgM = /src="(https?:[^"]+\.(?:jpg|jpeg|png|webp)[^"]*?)"/i.exec(block);
      const yearM = /\b(19[2-9]\d|20[0-2]\d)\b/.exec(block);

      const slug = href.split('/').pop();
      const name = titleM
        ? decodeHtml(titleM[1].trim())
        : slug.replace(/-/g, ' ').replace(/_/g, ' ');

      if (name.length < 3) continue;

      items.push({
        id: encodeId(href.replace(/^\//, '')),
        type: 'movie',
        name,
        poster: imgM ? imgM[1] : undefined,
        year: yearM ? parseInt(yearM[1]) : undefined,
      });
    }
  }

  return items.slice(skip, skip + 100);
}

function parseMeta(html, bgId, pageUrl) {
  const ogTitle = /property="og:title"\s+content="([^"]+)"/i.exec(html)
    || /name="twitter:title"\s+content="([^"]+)"/i.exec(html);
  const ogImage = /property="og:image"\s+content="([^"]+)"/i.exec(html)
    || /name="twitter:image"\s+content="([^"]+)"/i.exec(html);
  const ogDesc = /property="og:description"\s+content="([^"]+)"/i.exec(html)
    || /name="description"\s+content="([^"]+)"/i.exec(html);
  const h1 = /<h1[^>]*>\s*([\s\S]*?)\s*<\/h1>/i.exec(html);
  const yearM = /\b(19[2-9]\d|20[0-2]\d)\b/.exec(html);

  const name = ogTitle
    ? decodeHtml(ogTitle[1])
    : h1
    ? decodeHtml(h1[1].replace(/<[^>]+>/g, '').trim())
    : pageUrl.split('/').pop().replace(/-/g, ' ');

  return {
    id: bgId,
    type: 'movie',
    name,
    poster: ogImage ? ogImage[1] : undefined,
    background: ogImage ? ogImage[1] : undefined,
    description: ogDesc ? decodeHtml(ogDesc[1]) : undefined,
    year: yearM ? parseInt(yearM[1]) : undefined,
    genres: ['Archief', 'Nederland'],
    links: [{ name: 'Open in browser', category: 'Schatkamer', url: pageUrl }],
  };
}

function parseStreams(html, pageUrl) {
  const streams = [];

  const videoRe = /<(?:video|source)[^>]+src="([^"]+)"/gi;
  let m;
  while ((m = videoRe.exec(html)) !== null) {
    const src = m[1];
    if (/\.(m3u8|mp4|webm)/i.test(src) || /stream/i.test(src)) {
      streams.push({ url: src, title: /m3u8/i.test(src) ? 'HLS' : 'Video' });
    }
  }

  const nextDataM = /<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i.exec(html);
  if (nextDataM) {
    const matches = nextDataM[1].matchAll(/"(https?[^"]+\.(?:m3u8|mp4)[^"]*)"/g);
    for (const um of matches) {
      streams.push({ url: um[1], title: /m3u8/i.test(um[1]) ? 'HLS' : 'MP4' });
    }
  }

  const scriptRe = /<script[^>]*>([\s\S]*?)<\/script>/gi;
  while ((m = scriptRe.exec(html)) !== null) {
    const matches = m[1].matchAll(/"(https?[^"]+\.(?:m3u8|mp4)[^"]*)"/g);
    for (const um of matches) {
      streams.push({ url: um[1], title: /m3u8/i.test(um[1]) ? 'HLS' : 'MP4' });
    }
  }

  const jsonLdM = /<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/i.exec(html);
  if (jsonLdM) {
    try {
      const d = JSON.parse(jsonLdM[1]);
      const u = d.contentUrl || d.embedUrl || d?.video?.contentUrl;
      if (u) streams.push({ url: u, title: 'JSON-LD' });
    } catch (_) {}
  }

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

// ─── Manifest ─────────────────────────────────────────────────────────────────

const MANIFEST = {
  id: 'nl.beeldengeluid.schatkamer',
  version: '1.1.0',
  name: 'Beeld & Geluid Schatkamer',
  description:
    "Gratis toegang tot het archief van Beeld & Geluid – meer dan 700.000 Nederlandse tv-programma's (1920–2020).",
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

// ─── Cache ────────────────────────────────────────────────────────────────────

async function fromCache(key) {
  const r = await caches.default.match(new Request(`https://cache.local/${key}`));
  return r ? r.json() : null;
}

async function toCache(key, value, ttl) {
  const r = new Response(JSON.stringify(value), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${ttl}` },
  });
  await caches.default.put(new Request(`https://cache.local/${key}`), r);
}

// ─── Router ───────────────────────────────────────────────────────────────────

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response('', {
        status: 204,
        headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' },
      });
    }

    if (path === '/manifest.json') return json(MANIFEST);

    if (/^\/catalog\/movie\/bg-browse\.json$/.test(path)) {
      const raw = url.searchParams.get('extra') || '';
      const extra = Object.fromEntries(
        decodeURIComponent(raw).split('&').filter(Boolean).map((p) => p.split('='))
      );
      const query = extra.search || '';
      const skip = parseInt(extra.skip || '0', 10);
      const cKey = `cat:${query}:${skip}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ metas: cached });

      try {
        const pageUrl = query
          ? `${BASE}/zoeken?zoekterm=${encodeURIComponent(query)}`
          : `${BASE}/zoeken`;
        const html = await fetchPage(pageUrl);
        const metas = parseSearchResults(html, skip);
        await toCache(cKey, metas, 600);
        return json({ metas });
      } catch (e) {
        console.error('[catalog]', e.message);
        return json({ metas: [] });
      }
    }

    const metaM = path.match(/^\/meta\/movie\/([^/]+)\.json$/);
    if (metaM) {
      const bgId = decodeURIComponent(metaM[1]);
      const itemPath = decodeId(bgId);
      const pageUrl = `${BASE}/${itemPath}`;
      const cKey = `meta:${bgId}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ meta: cached });

      try {
        const html = await fetchPage(pageUrl);
        const meta = parseMeta(html, bgId, pageUrl);
        await toCache(cKey, meta, 3600);
        return json({ meta });
      } catch (e) {
        console.error('[meta]', e.message, pageUrl);
        const fallback = {
          id: bgId,
          type: 'movie',
          name: itemPath.split('/').pop().replace(/-/g, ' '),
          description: 'Beeld & Geluid Schatkamer',
          genres: ['Archief'],
        };
        return json({ meta: fallback });
      }
    }

    const streamM = path.match(/^\/stream\/movie\/([^/]+)\.json$/);
    if (streamM) {
      const bgId = decodeURIComponent(streamM[1]);
      const itemPath = decodeId(bgId);
      const pageUrl = `${BASE}/${itemPath}`;
      const cKey = `stream:${bgId}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ streams: cached });

      try {
        const html = await fetchPage(pageUrl);
        const streams = parseStreams(html, pageUrl);
        await toCache(cKey, streams, streams.some(s => s.url) ? 1800 : 60);
        return json({ streams });
      } catch (e) {
        console.error('[stream]', e.message);
        return json({ streams: [{ externalUrl: pageUrl, name: 'Open in browser', title: 'Schatkamer' }] });
      }
    }

    return json({ error: 'Not found' }, 404);
  },
};
