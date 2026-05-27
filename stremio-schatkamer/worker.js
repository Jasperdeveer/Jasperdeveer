'use strict';

// Beeld & Geluid PeerTube instance – publieke REST API, 7000+ Open Beelden videos
const PT = 'https://peertube.beeldengeluid.nl/api/v1';
const PT_HOST = 'https://peertube.beeldengeluid.nl';

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

async function ptFetch(path) {
  const resp = await fetch(PT + path, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) throw new Error(`PeerTube HTTP ${resp.status} for ${path}`);
  return resp.json();
}

// ─── ID helpers ───────────────────────────────────────────────────────────────
// ID = "bg:pt-<uuid>"

function encodeId(uuid) {
  return `bg:pt-${uuid}`;
}

function decodeUuid(bgId) {
  return bgId.replace(/^bg:pt-/, '');
}

// ─── PeerTube mappers ─────────────────────────────────────────────────────────

function videoToMeta(v) {
  return {
    id: encodeId(v.uuid),
    type: 'movie',
    name: v.name,
    poster: v.thumbnailPath ? PT_HOST + v.thumbnailPath : undefined,
    background: v.previewPath ? PT_HOST + v.previewPath : undefined,
    description: v.description || undefined,
    year: v.publishedAt ? new Date(v.publishedAt).getFullYear() : undefined,
    genres: (v.tags || []).length ? v.tags : ['Archief', 'Nederland'],
    runtime: v.duration ? Math.round(v.duration / 60) : undefined,
    links: [{ name: 'Open Beelden', category: 'Beeld & Geluid', url: `${PT_HOST}/w/${v.uuid}` }],
  };
}

function videoToStreams(v) {
  const streams = [];

  // HLS playlist (beste keuze voor Stremio)
  if (v.streamingPlaylists && v.streamingPlaylists.length > 0) {
    const hls = v.streamingPlaylists[0];
    if (hls.playlistUrl) {
      streams.push({
        url: hls.playlistUrl,
        title: 'HLS',
        name: 'Open Beelden',
        behaviorHints: { notWebReady: false },
      });
    }
  }

  // Directe MP4-bestanden op resolutie gesorteerd (hoogste eerst)
  if (v.files && v.files.length > 0) {
    const sorted = [...v.files].sort((a, b) => (b.resolution?.id || 0) - (a.resolution?.id || 0));
    for (const f of sorted.slice(0, 3)) {
      if (f.fileUrl) {
        streams.push({
          url: f.fileUrl,
          title: f.resolution?.label || 'MP4',
          name: 'Open Beelden',
          behaviorHints: { notWebReady: false },
        });
      }
    }
  }

  if (streams.length === 0) {
    streams.push({
      externalUrl: `${PT_HOST}/w/${v.uuid}`,
      name: 'Open Beelden',
      title: 'Open in browser',
    });
  }

  return streams;
}

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

// ─── Manifest ─────────────────────────────────────────────────────────────────

const MANIFEST = {
  id: 'nl.beeldengeluid.schatkamer',
  version: '2.0.0',
  name: 'Beeld & Geluid',
  description:
    'Open Beelden – gratis Nederlandse historische films en tv-fragmenten van het Nederlands Instituut voor Beeld en Geluid.',
  logo: 'https://www.beeldengeluid.nl/favicon.ico',
  catalogs: [
    {
      type: 'movie',
      id: 'bg-nieuwste',
      name: 'Open Beelden – Nieuwste',
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

    // manifest
    if (path === '/manifest.json') return json(MANIFEST);

    // catalog
    if (/^\/catalog\/movie\/bg-nieuwste\.json$/.test(path)) {
      const raw = url.searchParams.get('extra') || '';
      const extra = Object.fromEntries(
        decodeURIComponent(raw).split('&').filter(Boolean).map((p) => p.split('='))
      );
      const query = extra.search || '';
      const skip = parseInt(extra.skip || '0', 10);
      const cKey = `cat2:${query}:${skip}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ metas: cached });

      try {
        let data;
        if (query) {
          data = await ptFetch(
            `/search/videos?search=${encodeURIComponent(query)}&count=20&start=${skip}&sort=-match&nsfw=false`
          );
        } else {
          data = await ptFetch(`/videos?count=20&start=${skip}&sort=-publishedAt&nsfw=false`);
        }
        const metas = (data.data || []).map(videoToMeta);
        await toCache(cKey, metas, 600);
        return json({ metas });
      } catch (e) {
        console.error('[catalog]', e.message);
        return json({ metas: [] });
      }
    }

    // meta
    const metaM = path.match(/^\/meta\/movie\/([^/]+)\.json$/);
    if (metaM) {
      const bgId = decodeURIComponent(metaM[1]);
      if (!bgId.startsWith('bg:pt-')) return json({ meta: null });
      const uuid = decodeUuid(bgId);
      const cKey = `meta2:${uuid}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ meta: cached });

      try {
        const v = await ptFetch(`/videos/${uuid}`);
        const meta = videoToMeta(v);
        await toCache(cKey, meta, 3600);
        return json({ meta });
      } catch (e) {
        console.error('[meta]', e.message);
        return json({ meta: null });
      }
    }

    // stream
    const streamM = path.match(/^\/stream\/movie\/([^/]+)\.json$/);
    if (streamM) {
      const bgId = decodeURIComponent(streamM[1]);
      if (!bgId.startsWith('bg:pt-')) return json({ streams: [] });
      const uuid = decodeUuid(bgId);
      const cKey = `stream2:${uuid}`;

      const cached = await fromCache(cKey);
      if (cached) return json({ streams: cached });

      try {
        const v = await ptFetch(`/videos/${uuid}`);
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
