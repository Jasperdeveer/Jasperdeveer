require('dotenv').config();

const { addonBuilder, serveHTTP } = require('stremio-addon-sdk');
const trakt = require('./trakt');

const PORT = process.env.PORT || 7000;

const manifest = {
  id: 'community.stremio-trakt-episodes',
  version: '1.0.0',
  name: 'Trakt Episodes',
  description:
    'Loads correct seasons and episodes metadata from Trakt.tv for series.',
  logo: 'https://trakt.tv/assets/trakt.d2c8b4f3.png',
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
  behaviorHints: { configurable: false },
};

const builder = new addonBuilder(manifest);

// ── Helpers ──────────────────────────────────────────────────────────────────

function showToMeta(show) {
  const ids = show.ids || {};
  const imdbId = ids.imdb;
  if (!imdbId) return null;

  return {
    id: imdbId,
    type: 'series',
    name: show.title,
    year: show.year,
    poster: null, // Trakt doesn't provide images; Stremio fetches them via IMDB id
    description: show.overview || '',
    genres: show.genres || [],
    imdbRating: show.rating ? show.rating.toFixed(1) : undefined,
    runtime: show.runtime ? `${show.runtime} min` : undefined,
    status: show.status,
    country: show.country,
    network: show.network,
  };
}

function buildVideos(seasonsWithEpisodes) {
  const videos = [];

  for (const season of seasonsWithEpisodes) {
    for (const ep of season.episodes || []) {
      videos.push({
        id: `${ep.ids.imdb || ''}`,
        title: ep.title || `Episode ${ep.number}`,
        season: season.number,
        episode: ep.number,
        overview: ep.overview || '',
        released: ep.first_aired ? new Date(ep.first_aired).toISOString() : undefined,
        rating: ep.rating ? ep.rating.toFixed(1) : undefined,
        thumbnail: null,
      });
    }
  }

  return videos;
}

// ── Catalog handler ───────────────────────────────────────────────────────────

builder.defineCatalogHandler(async ({ type, id, extra }) => {
  if (type !== 'series') return { metas: [] };

  try {
    if (id === 'trakt-search' && extra.search) {
      const results = await trakt.searchShows(extra.search, 20);
      const metas = results
        .map((r) => showToMeta(r.show || r))
        .filter(Boolean);
      return { metas };
    }

    if (id === 'trakt-trending') {
      const results = await trakt.getTrending(20);
      const metas = results
        .map((r) => showToMeta(r.show || r))
        .filter(Boolean);
      return { metas };
    }

    if (id === 'trakt-popular') {
      const results = await trakt.getPopular(20);
      const metas = results.map((show) => showToMeta(show)).filter(Boolean);
      return { metas };
    }
  } catch (err) {
    console.error(`Catalog error [${id}]:`, err.message);
  }

  return { metas: [] };
});

// ── Meta handler ──────────────────────────────────────────────────────────────

builder.defineMetaHandler(async ({ type, id }) => {
  if (type !== 'series') return { meta: null };

  try {
    // id is the IMDB id (e.g. "tt0903747")
    const show = await trakt.searchByImdb(id);
    if (!show) {
      console.warn(`No Trakt result for IMDB id: ${id}`);
      return { meta: null };
    }

    const slug = show.ids.slug;
    const [summary, seasonsWithEpisodes] = await Promise.all([
      trakt.getShowSummary(slug),
      trakt.getAllSeasonsWithEpisodes(slug),
    ]);

    const meta = {
      id,
      type: 'series',
      name: summary.title,
      year: summary.year,
      description: summary.overview || '',
      genres: summary.genres || [],
      imdbRating: summary.rating ? summary.rating.toFixed(1) : undefined,
      runtime: summary.runtime ? `${summary.runtime} min` : undefined,
      status: summary.status,
      country: summary.country,
      network: summary.network,
      videos: buildVideos(seasonsWithEpisodes),
    };

    return { meta };
  } catch (err) {
    console.error(`Meta error [${id}]:`, err.message);
    return { meta: null };
  }
});

// ── Start server ──────────────────────────────────────────────────────────────

serveHTTP(builder.getInterface(), { port: PORT }, () => {
  console.log(`Trakt Episodes addon running on http://localhost:${PORT}`);
  console.log(`Install URL: http://localhost:${PORT}/manifest.json`);
});
