const MANIFEST = {
  id: 'community.stremio-trakt-episodes',
  version: '1.1.0',
  name: 'Trakt Episodes',
  description:
    'Overrides Cinemeta with correct season & episode data from Trakt.tv, posters from TMDB.',
  logo: 'https://walter.trakt.tv/hotlink-ok/public/favicon.ico',
  resources: ['catalog', 'meta'],
  types: ['series'],
  catalogs: [
    {
      id: 'trakt-trending',
      type: 'series',
      name: 'Trakt Trending',
      extra: [{ name: 'skip' }],
    },
    {
      id: 'trakt-popular',
      type: 'series',
      name: 'Trakt Popular',
      extra: [{ name: 'skip' }],
    },
    {
      id: 'trakt-search',
      type: 'series',
      name: 'Trakt Search',
      extra: [{ name: 'search', isRequired: true }],
    },
  ],
  idPrefixes: ['tt'],
  behaviorHints: { configurable: false, adult: false },
};

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};

const TMDB_IMG = 'https://image.tmdb.org/t/p/w500';
const TMDB_BACKDROP = 'https://image.tmdb.org/t/p/w1280';

// ── Cached fetch ─────────────────────────────────────────────────────────────

async function cachedFetch(url, ctx, ttl = 3600) {
  const cache = caches.default;
  const cacheKey = new Request(url);
  const cached = await cache.match(cacheKey);
  if (cached) return cached.json();

  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);

  const body = await res.json();
  const cacheable = new Response(JSON.stringify(body), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': `public, max-age=${ttl}`,
    },
  });
  ctx.waitUntil(cache.put(cacheKey, cacheable));
  return body;
}

// ── Trakt API ─────────────────────────────────────────────────────────────────

function traktUrl(path, clientId) {
  const base = 'https://api.trakt.tv';
  const sep = path.includes('?') ? '&' : '?';
  return `${base}${path}${sep}client_id=${clientId}`;
}

async function traktGet(path, env, ctx, ttl) {
  return cachedFetch(traktUrl(path, env.TRAKT_CLIENT_ID), ctx, ttl);
}

async function traktFindByImdb(imdbId, env, ctx) {
  const results = await traktGet(
    `/search/imdb/${imdbId}?type=show`,
    env, ctx, 86400
  );
  return results?.[0]?.show ?? null;
}

async function traktShowSummary(slug, env, ctx) {
  return traktGet(`/shows/${slug}?extended=full`, env, ctx, 3600);
}

async function traktSeasons(slug, env, ctx) {
  return traktGet(`/shows/${slug}/seasons?extended=full`, env, ctx, 3600);
}

async function traktEpisodes(slug, season, env, ctx) {
  return traktGet(
    `/shows/${slug}/seasons/${season}?extended=full`,
    env, ctx, 3600
  );
}

async function traktSearch(query, env, ctx) {
  return traktGet(
    `/search/show?query=${encodeURIComponent(query)}&limit=20&extended=full`,
    env, ctx, 600
  );
}

async function traktTrending(env, ctx) {
  return traktGet('/shows/trending?limit=20&extended=full', env, ctx, 900);
}

async function traktPopular(env, ctx) {
  return traktGet('/shows/popular?limit=20&extended=full', env, ctx, 900);
}

// ── TMDB API ──────────────────────────────────────────────────────────────────

async function tmdbFindByImdb(imdbId, env, ctx) {
  if (!env.TMDB_API_KEY) return null;
  try {
    const url =
      `https://api.themoviedb.org/3/find/${imdbId}` +
      `?external_source=imdb_id&api_key=${env.TMDB_API_KEY}`;
    const data = await cachedFetch(url, ctx, 86400);
    return data?.tv_results?.[0] ?? null;
  } catch {
    return null;
  }
}

async function tmdbSeasonEpisodes(tmdbId, seasonNum, env, ctx) {
  if (!env.TMDB_API_KEY || !tmdbId) return null;
  try {
    const url =
      `https://api.themoviedb.org/3/tv/${tmdbId}/season/${seasonNum}` +
      `?api_key=${env.TMDB_API_KEY}`;
    return await cachedFetch(url, ctx, 3600);
  } catch {
    return null;
  }
}

// ── Data builders ─────────────────────────────────────────────────────────────

function showMeta(show, tmdb) {
  const imdbId = show.ids?.imdb;
  if (!imdbId) return null;
  return {
    id: imdbId,
    type: 'series',
    name: show.title,
    year: show.year,
    poster: tmdb?.poster_path ? `${TMDB_IMG}${tmdb.poster_path}` : null,
    background: tmdb?.backdrop_path ? `${TMDB_BACKDROP}${tmdb.backdrop_path}` : null,
    description: show.overview || '',
    genres: show.genres || [],
    imdbRating: show.rating ? show.rating.toFixed(1) : undefined,
    runtime: show.runtime ? `${show.runtime} min` : undefined,
    status: show.status,
    country: show.country,
    network: show.network,
    slug: show.ids?.slug,
  };
}

async function buildVideos(slug, seasons, env, ctx, tmdbId) {
  const mainSeasons = seasons.filter((s) => s.number > 0);

  const videos = [];

  await Promise.all(
    mainSeasons.map(async (season) => {
      const [traktEps, tmdbSeason] = await Promise.all([
        traktEpisodes(slug, season.number, env, ctx),
        tmdbSeasonEpisodes(tmdbId, season.number, env, ctx),
      ]);

      const tmdbEpMap = {};
      for (const ep of tmdbSeason?.episodes ?? []) {
        tmdbEpMap[ep.episode_number] = ep;
      }

      for (const ep of traktEps ?? []) {
        const tmdbEp = tmdbEpMap[ep.number];
        videos.push({
          id: `${ep.ids?.imdb || `${slug}:${season.number}:${ep.number}`}`,
          title: ep.title || `Episode ${ep.number}`,
          season: season.number,
          episode: ep.number,
          overview: ep.overview || '',
          released: ep.first_aired
            ? new Date(ep.first_aired).toISOString()
            : undefined,
          rating: ep.rating ? ep.rating.toFixed(1) : undefined,
          thumbnail: tmdbEp?.still_path
            ? `${TMDB_IMG}${tmdbEp.still_path}`
            : null,
        });
      }
    })
  );

  // Sort by season then episode
  videos.sort((a, b) => a.season - b.season || a.episode - b.episode);
  return videos;
}

// ── Extra string parser ───────────────────────────────────────────────────────
// Stremio encodes catalog extras as path segments: key=value&key=value

function parseExtra(extraStr) {
  if (!extraStr) return {};
  const out = {};
  for (const part of decodeURIComponent(extraStr).split('&')) {
    const [k, v] = part.split('=');
    if (k) out[k] = v ?? '';
  }
  return out;
}

// ── Route handlers ────────────────────────────────────────────────────────────

async function handleCatalog(catalogId, extraStr, env, ctx) {
  const extra = parseExtra(extraStr);

  try {
    if (catalogId === 'trakt-search' && extra.search) {
      const results = await traktSearch(extra.search, env, ctx);
      const shows = results.map((r) => r.show ?? r).filter((s) => s.ids?.imdb);

      const metas = await Promise.all(
        shows.map(async (show) => {
          const tmdb = await tmdbFindByImdb(show.ids.imdb, env, ctx);
          return showMeta(show, tmdb);
        })
      );
      return { metas: metas.filter(Boolean) };
    }

    if (catalogId === 'trakt-trending') {
      const results = await traktTrending(env, ctx);
      const shows = results.map((r) => r.show ?? r).filter((s) => s.ids?.imdb);
      const metas = await Promise.all(
        shows.map(async (show) => {
          const tmdb = await tmdbFindByImdb(show.ids.imdb, env, ctx);
          return showMeta(show, tmdb);
        })
      );
      return { metas: metas.filter(Boolean) };
    }

    if (catalogId === 'trakt-popular') {
      const results = await traktPopular(env, ctx);
      const shows = results.filter((s) => s.ids?.imdb);
      const metas = await Promise.all(
        shows.map(async (show) => {
          const tmdb = await tmdbFindByImdb(show.ids.imdb, env, ctx);
          return showMeta(show, tmdb);
        })
      );
      return { metas: metas.filter(Boolean) };
    }
  } catch (err) {
    console.error(`Catalog [${catalogId}] error:`, err.message);
  }

  return { metas: [] };
}

async function handleMeta(imdbId, env, ctx) {
  try {
    const [traktShow, tmdbShow] = await Promise.all([
      traktFindByImdb(imdbId, env, ctx),
      tmdbFindByImdb(imdbId, env, ctx),
    ]);

    if (!traktShow) return { meta: null };

    const slug = traktShow.ids.slug;
    const tmdbId = tmdbShow?.id ?? null;

    const [summary, seasons] = await Promise.all([
      traktShowSummary(slug, env, ctx),
      traktSeasons(slug, env, ctx),
    ]);

    const videos = await buildVideos(slug, seasons, env, ctx, tmdbId);

    const meta = {
      id: imdbId,
      type: 'series',
      name: summary.title,
      year: summary.year,
      poster: tmdbShow?.poster_path ? `${TMDB_IMG}${tmdbShow.poster_path}` : null,
      background: tmdbShow?.backdrop_path
        ? `${TMDB_BACKDROP}${tmdbShow.backdrop_path}`
        : null,
      description: summary.overview || '',
      genres: summary.genres || [],
      imdbRating: summary.rating ? summary.rating.toFixed(1) : undefined,
      runtime: summary.runtime ? `${summary.runtime} min` : undefined,
      status: summary.status,
      country: summary.country,
      network: summary.network,
      videos,
    };

    return { meta };
  } catch (err) {
    console.error(`Meta [${imdbId}] error:`, err.message);
    return { meta: null };
  }
}

// ── Main fetch handler ────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/$/, '');

    const json = (data) =>
      new Response(JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json', ...CORS },
      });

    // /manifest.json
    if (path === '/manifest.json') {
      return json(MANIFEST);
    }

    // /catalog/series/:catalogId.json
    // /catalog/series/:catalogId/:extra.json
    const catalogMatch = path.match(
      /^\/catalog\/series\/([^/]+?)(?:\/([^/]+))?\.json$/
    );
    if (catalogMatch) {
      const result = await handleCatalog(catalogMatch[1], catalogMatch[2], env, ctx);
      return json(result);
    }

    // /meta/series/:imdbId.json
    const metaMatch = path.match(/^\/meta\/series\/(tt\d+)\.json$/);
    if (metaMatch) {
      const result = await handleMeta(metaMatch[1], env, ctx);
      return json(result);
    }

    return new Response('Not found', { status: 404, headers: CORS });
  },
};
