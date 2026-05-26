'use strict';

const { addonBuilder, serveHTTP } = require('stremio-addon-sdk');
const scraper = require('./lib/scraper');
const cache = require('./lib/cache');

const PORT = process.env.PORT || 7000;

const manifest = {
  id: 'nl.beeldengeluid.schatkamer',
  version: '1.0.0',
  name: 'Beeld & Geluid Schatkamer',
  description:
    "Gratis toegang tot het archief van Beeld & Geluid – meer dan 700.000 Nederlandse radio- en tv-programma's uit de periode 1920–2020.",
  logo: 'https://www.beeldengeluid.nl/sites/default/files/favicon.ico',
  background: 'https://schatkamer.beeldengeluid.nl/',
  catalogs: [
    {
      type: 'movie',
      id: 'bg-browse',
      name: 'Schatkamer – Bladeren',
      extra: [
        { name: 'search', isRequired: false },
        { name: 'skip', isRequired: false },
      ],
    },
  ],
  resources: ['catalog', 'meta', 'stream'],
  types: ['movie'],
  idPrefixes: ['bg:'],
  behaviorHints: {
    adult: false,
    p2p: false,
  },
};

const builder = new addonBuilder(manifest);

// ─── Catalog ────────────────────────────────────────────────────────────────

builder.defineCatalogHandler(async ({ type, id, extra }) => {
  if (type !== 'movie' || id !== 'bg-browse') return { metas: [] };

  const query = extra?.search || '';
  const skip = parseInt(extra?.skip || '0', 10);
  const cacheKey = `catalog:${query}:${skip}`;

  const cached = cache.get(cacheKey);
  if (cached) return { metas: cached };

  try {
    const items = await scraper.search(query, skip);
    const metas = items.map((item) => ({
      id: item.id,
      type: 'movie',
      name: item.name,
      poster: item.poster || undefined,
      description: item.description || undefined,
      year: item.year ? parseInt(item.year) : undefined,
    }));
    cache.set(cacheKey, metas);
    return { metas };
  } catch (err) {
    console.error('[catalog]', err.message);
    return { metas: [] };
  }
});

// ─── Meta ────────────────────────────────────────────────────────────────────

builder.defineMetaHandler(async ({ type, id }) => {
  if (type !== 'movie' || !id.startsWith('bg:')) return { meta: null };

  const cacheKey = `meta:${id}`;
  const cached = cache.get(cacheKey);
  if (cached) return { meta: cached };

  try {
    const meta = await scraper.getMeta(id);
    if (meta) cache.set(cacheKey, meta);
    return { meta: meta || null };
  } catch (err) {
    console.error('[meta]', err.message);
    return { meta: null };
  }
});

// ─── Stream ──────────────────────────────────────────────────────────────────

builder.defineStreamHandler(async ({ type, id }) => {
  if (type !== 'movie' || !id.startsWith('bg:')) return { streams: [] };

  const cacheKey = `stream:${id}`;
  const cached = cache.get(cacheKey);
  if (cached) return { streams: cached };

  try {
    const streams = await scraper.getStreams(id);
    if (streams.length) cache.set(cacheKey, streams);
    return { streams };
  } catch (err) {
    console.error('[stream]', err.message);
    return { streams: [] };
  }
});

// ─── Start server ────────────────────────────────────────────────────────────

serveHTTP(builder.getInterface(), { port: PORT });
console.log(`Stremio Schatkamer addon gestart op http://127.0.0.1:${PORT}/manifest.json`);
