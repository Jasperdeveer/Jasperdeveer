'use strict';

const PT = 'https://peertube.beeldengeluid.nl/api/v1';
const PT_HOST = 'https://peertube.beeldengeluid.nl';

// ─── HTTP / cache ────────────────────────────────────────────────────────────

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

async function ptGet(path) {
  const resp = await fetch(PT + path, { headers: { Accept: 'application/json' } });
  if (!resp.ok) throw new Error(`PT ${resp.status} ${path}`);
  return resp.json();
}

async function fromCache(key) {
  const r = await caches.default.match(new Request(`https://cache.local/${key}`));
  return r ? r.json() : null;
}

async function toCache(key, value, ttl) {
  await caches.default.put(
    new Request(`https://cache.local/${key}`),
    new Response(JSON.stringify(value), {
      headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${ttl}` },
    })
  );
}

// ─── ID schema ─────────────────────────────────────────────────────────────────
//  bg:pt-<uuid>      → losse video (movie)
//  bg:ch-<handle>    → kanaal / programma (series)

function videoId(uuid)   { return `bg:pt-${uuid}`; }
function channelId(h)    { return `bg:ch-${encodeURIComponent(h)}`; }
function parseId(bgId) {
  if (bgId.startsWith('bg:pt-')) return { kind: 'video',   val: bgId.slice(6) };
  if (bgId.startsWith('bg:ch-')) return { kind: 'channel', val: decodeURIComponent(bgId.slice(6)) };
  return null;
}

// ─── Mappers ────────────────────────────────────────────────────────────────────

function thumb(path) {
  return path ? PT_HOST + path : undefined;
}

function videoToMeta(v, type = 'movie') {
  return {
    id: videoId(v.uuid),
    type,
    name: v.name,
    poster: thumb(v.thumbnailPath),
    background: thumb(v.previewPath),
    description: v.description || undefined,
    year: v.publishedAt ? new Date(v.publishedAt).getFullYear() : undefined,
    runtime: v.duration ? Math.round(v.duration / 60) : undefined,
    genres: v.category?.label ? [v.category.label] : ['Archief'],
    links: [{ name: 'Open Beelden', category: 'Beeld & Geluid', url: `${PT_HOST}/w/${v.uuid}` }],
  };
}

function channelToMeta(ch) {
  return {
    id: channelId(ch.name),
    type: 'series',
    name: ch.displayName,
    poster: thumb(ch.avatar?.path),
    background: thumb(ch.banner?.path),
    description: ch.description || undefined,
    genres: ['Archief', 'Nederland'],
    links: [{ name: 'Open Beelden', category: 'Beeld & Geluid', url: `${PT_HOST}/c/${ch.name}` }],
  };
}

function videoToStreams(v) {
  const streams = [];
  if (v.streamingPlaylists?.length) {
    const hls = v.streamingPlaylists[0];
    if (hls.playlistUrl)
      streams.push({ url: hls.playlistUrl, title: 'HLS', name: 'Open Beelden', behaviorHints: { notWebReady: false } });
  }
  if (v.files?.length) {
    const sorted = [...v.files].sort((a, b) => (b.resolution?.id || 0) - (a.resolution?.id || 0));
    for (const f of sorted.slice(0, 3)) {
      if (f.fileUrl)
        streams.push({ url: f.fileUrl, title: f.resolution?.label || 'MP4', name: 'Open Beelden', behaviorHints: { notWebReady: false } });
    }
  }
  if (!streams.length)
    streams.push({ externalUrl: `${PT_HOST}/w/${v.uuid}`, name: 'Open Beelden', title: 'Open in browser' });
  return streams;
}

// ─── Manifest ─────────────────────────────────────────────────────────────────

const MANIFEST = {
  id: 'nl.beeldengeluid.openbeelden',
  version: '3.0.0',
  name: 'Beeld & Geluid',
  description: 'Open Beelden – historische Nederlandse films en tv-programma\'s van het Nederlands Instituut voor Beeld en Geluid.',
  logo: 'https://www.beeldengeluid.nl/favicon.ico',
  types: ['movie', 'series'],
  catalogs: [
    {
      type: 'series',
      id: 'bg-programmas',
      name: 'Programma\'s',
      extra: [
        { name: 'search', isRequired: false },
        { name: 'skip',   isRequired: false },
      ],
    },
    {
      type: 'movie',
      id: 'bg-fragmenten',
      name: 'Fragmenten & Films',
      extra: [
        { name: 'search', isRequired: false },
        { name: 'skip',   isRequired: false },
        {
          name: 'genre',
          isRequired: false,
          options: ['Nieuws', 'Documentaire', 'Cultuur', 'Sport', 'Muziek', 'Geschiedenis'],
        },
      ],
    },
  ],
  resources: ['catalog', 'meta', 'stream'],
  idPrefixes: ['bg:'],
  behaviorHints: { adult: false, p2p: false },
};

// ─── Extra parser ───────────────────────────────────────────────────────────

function parseExtra(raw) {
  const str = decodeURIComponent(raw || '');
  return Object.fromEntries(str.split('&').filter(Boolean).map(p => {
    const i = p.indexOf('=');
    return i < 0 ? [p, ''] : [p.slice(0, i), p.slice(i + 1)];
  }));
}

// Genre → PeerTube category label (best-effort match)
const GENRE_MAP = {
  'Nieuws': 11, 'Documentaire': 4, 'Cultuur': 4,
  'Sport': 5, 'Muziek': 1, 'Geschiedenis': 14,
};

// ─── Router ───────────────────────────────────────────────────────────────────

export default {
  async fetch(request) {
    const url  = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS')
      return new Response('', { status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' } });

    if (path === '/manifest.json') return json(MANIFEST);

    // ── CATALOG ───────────────────────────────────────────────────────
    const catM = path.match(/^\/catalog\/(movie|series)\/([^/]+)\.json$/);
    if (catM) {
      const [, type, catalogId] = catM;
      const extra = parseExtra(url.searchParams.get('extra'));
      const query = extra.search || '';
      const skip  = parseInt(extra.skip || '0', 10);
      const genre = extra.genre || '';
      const cKey  = `cat:${catalogId}:${query}:${skip}:${genre}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ metas: cached });

      try {
        let metas = [];

        if (catalogId === 'bg-programmas') {
          // Series: toon kanalen als programma’s
          const data = query
            ? await ptGet(`/search/video-channels?search=${encodeURIComponent(query)}&count=20&start=${skip}`)
            : await ptGet(`/video-channels?count=20&start=${skip}`);
          metas = (data.data || []).map(channelToMeta);
        }

        if (catalogId === 'bg-fragmenten') {
          // Movies: losse video’s, optioneel gefilterd op genre
          let apiPath;
          if (query) {
            apiPath = `/search/videos?search=${encodeURIComponent(query)}&count=20&start=${skip}&nsfw=false`;
          } else {
            apiPath = `/videos?count=20&start=${skip}&sort=-publishedAt&nsfw=false`;
            if (genre && GENRE_MAP[genre]) apiPath += `&categoryOneOf[]=${GENRE_MAP[genre]}`;
          }
          const data = await ptGet(apiPath);
          metas = (data.data || []).map(v => videoToMeta(v, 'movie'));
        }

        await toCache(cKey, metas, 600);
        return json({ metas });
      } catch (e) {
        console.error('[catalog]', e.message);
        return json({ metas: [] });
      }
    }

    // ── META ───────────────────────────────────────────────────────────
    const metaM = path.match(/^\/meta\/(movie|series)\/([^/]+)\.json$/);
    if (metaM) {
      const [, type, rawId] = metaM;
      const bgId   = decodeURIComponent(rawId);
      const parsed = parseId(bgId);
      if (!parsed) return json({ meta: null });

      const cKey = `meta:${bgId}`;
      const cached = await fromCache(cKey);
      if (cached) return json({ meta: cached });

      try {
        let meta;

        if (parsed.kind === 'video') {
          const v = await ptGet(`/videos/${parsed.val}`);
          meta = videoToMeta(v, type);
        }

        if (parsed.kind === 'channel') {
          // Kanaal + alle video’s als afleveringen
          const [ch, vData] = await Promise.all([
            ptGet(`/video-channels/${parsed.val}`),
            ptGet(`/video-channels/${parsed.val}/videos?count=100&sort=-publishedAt&nsfw=false`),
          ]);
          const videos = (vData.data || []).map((v, i) => ({
            id:        videoId(v.uuid),
            title:     v.name,
            season:    1,
            episode:   i + 1,
            thumbnail: thumb(v.thumbnailPath),
            overview:  v.description || undefined,
            released:  v.publishedAt ? new Date(v.publishedAt) : undefined,
          }));
          meta = { ...channelToMeta(ch), videos };
        }

        if (meta) await toCache(cKey, meta, 3600);
        return json({ meta: meta || null });
      } catch (e) {
        console.error('[meta]', e.message);
        return json({ meta: null });
      }
    }

    // ── STREAM ──────────────────────────────────────────────────────────
    const streamM = path.match(/^\/stream\/(movie|series)\/([^/]+)\.json$/);
    if (streamM) {
      const [, , rawId] = streamM;
      const bgId   = decodeURIComponent(rawId);
      const parsed = parseId(bgId);
      // Alleen video’s kunnen worden afgespeeld, niet kanalen
      if (!parsed || parsed.kind !== 'video') return json({ streams: [] });

      const cKey = `stream:${bgId}`;
      const cached = await fromCache(cKey);
      if (cached) return json({ streams: cached });

      try {
        const v       = await ptGet(`/videos/${parsed.val}`);
        const streams = videoToStreams(v);
        await toCache(cKey, streams, 3600);
        return json({ streams });
      } catch (e) {
        console.error('[stream]', e.message);
        return json({ streams: [] });
      }
    }

    return json({ error: 'Not found' }, 404);
  },
};
