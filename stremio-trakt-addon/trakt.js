const fetch = require('node-fetch');

const BASE_URL = 'https://api.trakt.tv';

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'trakt-api-version': '2',
    'trakt-api-key': process.env.TRAKT_CLIENT_ID || '',
  };
}

async function traktGet(path) {
  const res = await fetch(`${BASE_URL}${path}`, { headers: getHeaders() });
  if (!res.ok) {
    throw new Error(`Trakt API error ${res.status} for ${path}`);
  }
  return res.json();
}

async function searchByImdb(imdbId) {
  const results = await traktGet(`/search/imdb/${imdbId}?type=show`);
  return results && results[0] ? results[0].show : null;
}

async function getShowSummary(traktSlug) {
  return traktGet(`/shows/${traktSlug}?extended=full`);
}

async function getSeasons(traktSlug) {
  return traktGet(`/shows/${traktSlug}/seasons?extended=full`);
}

async function getEpisodes(traktSlug, seasonNumber) {
  return traktGet(`/shows/${traktSlug}/seasons/${seasonNumber}?extended=full`);
}

async function getAllSeasonsWithEpisodes(traktSlug) {
  const seasons = await getSeasons(traktSlug);
  // Filter out specials (season 0) unless explicitly wanted
  const mainSeasons = seasons.filter((s) => s.number > 0);

  const seasonsWithEpisodes = await Promise.all(
    mainSeasons.map(async (season) => {
      const episodes = await getEpisodes(traktSlug, season.number);
      return { ...season, episodes };
    })
  );

  return seasonsWithEpisodes;
}

async function searchShows(query, limit = 20) {
  const results = await traktGet(
    `/search/show?query=${encodeURIComponent(query)}&limit=${limit}&extended=full`
  );
  return results || [];
}

async function getTrending(limit = 20) {
  const results = await traktGet(`/shows/trending?limit=${limit}&extended=full`);
  return results || [];
}

async function getPopular(limit = 20) {
  const results = await traktGet(`/shows/popular?limit=${limit}&extended=full`);
  return results || [];
}

module.exports = {
  searchByImdb,
  getShowSummary,
  getSeasons,
  getEpisodes,
  getAllSeasonsWithEpisodes,
  searchShows,
  getTrending,
  getPopular,
};
