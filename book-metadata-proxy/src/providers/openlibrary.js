// Open Library is de ruggengraat: het is de enige gratis bron met stabiele
// ID's én een volledige auteur -> werken -> edities structuur. Hardcover en
// Google Books vullen aan, maar de skeletstructuur komt hiervandaan.

import { fetchJson } from '../lib/http.js';
import { normaliseOlKey } from '../lib/ids.js';

const BASE = 'https://openlibrary.org';
export const COVERS = 'https://covers.openlibrary.org';

// Deze velden geven per werk genoeg om meteen een bruikbare editie te bouwen,
// zonder per werk een extra call te doen.
const SEARCH_FIELDS = [
  'key',
  'title',
  'subtitle',
  'author_key',
  'author_name',
  'first_publish_year',
  'publish_year',
  'cover_i',
  'cover_edition_key',
  'edition_key',
  'edition_count',
  'isbn',
  'lccn',
  'number_of_pages_median',
  'publisher',
  'language',
  'subject',
  'ratings_average',
  'ratings_count',
  'ebook_access',
  'first_sentence',
].join(',');

export function coverUrl(coverId, size = 'L') {
  return Number.isFinite(Number(coverId)) && Number(coverId) > 0
    ? `${COVERS}/b/id/${coverId}-${size}.jpg`
    : null;
}

export function coverUrlByOlid(editionKey, size = 'L') {
  const key = normaliseOlKey(editionKey);

  return key ? `${COVERS}/b/olid/${key}-${size}.jpg` : null;
}

export function getAuthor(env, authorKey) {
  return fetchJson(`${BASE}/authors/${authorKey}.json`, { env, cacheTtl: 86400 });
}

export function getWork(env, workKey) {
  return fetchJson(`${BASE}/works/${workKey}.json`, { env, cacheTtl: 86400 });
}

export function getEdition(env, editionKey) {
  return fetchJson(`${BASE}/books/${editionKey}.json`, { env, cacheTtl: 86400 });
}

export function getEditionsOfWork(env, workKey, limit = 40) {
  return fetchJson(`${BASE}/works/${workKey}/editions.json?limit=${limit}`, { env, cacheTtl: 86400 });
}

export function getWorkRatings(env, workKey) {
  return fetchJson(`${BASE}/works/${workKey}/ratings.json`, { env, cacheTtl: 86400 });
}

export function getByIsbn(env, isbn) {
  return fetchJson(`${BASE}/isbn/${encodeURIComponent(isbn)}.json`, { env, cacheTtl: 86400 });
}

/**
 * Alle werken van een auteur in zo min mogelijk calls. De Search-API geeft per
 * werk meteen ISBN's, uitgever, paginacount en ratings mee - de losse
 * /authors/{id}/works.json doet dat niet.
 */
export async function searchWorksByAuthor(env, authorKey, { limit = 500 } = {}) {
  const perPage = Math.min(limit, 100);
  const docs = [];
  let page = 1;
  let total = Infinity;

  while (docs.length < limit && docs.length < total && page <= 10) {
    const url =
      `${BASE}/search.json?q=${encodeURIComponent(`author_key:${authorKey}`)}` +
      `&fields=${SEARCH_FIELDS}&limit=${perPage}&page=${page}&sort=old`;

    const payload = await fetchJson(url, { env, timeoutMs: 20000, cacheTtl: 3600 });

    if (!payload || !Array.isArray(payload.docs) || payload.docs.length === 0) {
      break;
    }

    total = Number.isFinite(payload.numFound) ? payload.numFound : docs.length + payload.docs.length;
    docs.push(...payload.docs);
    page += 1;
  }

  return docs.slice(0, limit);
}

export async function searchWorks(env, query, { limit = 20 } = {}) {
  const url =
    `${BASE}/search.json?q=${encodeURIComponent(query)}` +
    `&fields=${SEARCH_FIELDS}&limit=${Math.min(limit, 100)}`;

  const payload = await fetchJson(url, { env, timeoutMs: 20000, cacheTtl: 3600 });

  return {
    numFound: payload?.numFound ?? 0,
    docs: Array.isArray(payload?.docs) ? payload.docs : [],
  };
}
