// Shelfarr-compatibele laag.
//
// Shelfarr heeft de Open Library-URL's hard in de code staan (alleen de keuze
// tussen Hardcover en Open Library is instelbaar, niet het adres). Daarom
// bootst deze laag het antwoordformaat van openlibrary.org na, zodat je
// Shelfarr er via een host-override naartoe kunt wijzen. Zie de README.
//
// De vorm blijft gelijk aan het origineel; alleen de inhoud is aangevuld met
// wat Hardcover en Google Books extra weten.

import * as ol from '../providers/openlibrary.js';
import * as hardcover from '../providers/hardcover.js';
import { fetchEnrichment } from '../core/enrich.js';
import { kvGet, kvPut } from '../lib/cache.js';
import { mapWithLimit, tryFetchJson } from '../lib/http.js';
import { normaliseOlKey } from '../lib/ids.js';
import { bestDescription, cleanDescription, normaliseIsbn13 } from '../lib/text.js';
import { json, notFound } from '../lib/respond.js';

const ENRICH_TTL = 60 * 60 * 24 * 14;

/**
 * GET /search.json
 *
 * Blijft dicht bij het origineel, maar zet Hardcover-treffers vooraan wanneer
 * Open Library met rommel terugkomt, en vult ontbrekende covers aan.
 */
export async function search(request, env, url) {
  const query = url.searchParams.get('q') ?? url.searchParams.get('title') ?? '';
  const limit = Math.min(Number.parseInt(url.searchParams.get('limit') ?? '20', 10) || 20, 100);

  if (!query.trim()) {
    return json({ numFound: 0, start: 0, docs: [] });
  }

  const [fromOl, fromHardcover] = await Promise.all([
    ol.searchWorks(env, query, { limit }).catch(() => ({ numFound: 0, docs: [] })),
    hardcover.isConfigured(env) ? hardcover.findBook(env, query).catch(() => null) : Promise.resolve(null),
  ]);

  const docs = fromOl.docs.map((doc) => ({
    ...doc,
    cover_url: ol.coverUrl(doc.cover_i) ?? ol.coverUrlByOlid(doc.cover_edition_key),
  }));

  if (fromHardcover) {
    // Beschrijving aan de best passende treffer hangen; Open Library geeft die
    // in zoekresultaten nooit mee en Shelfarr toont hem wel.
    const wanted = String(fromHardcover.title ?? '').trim().toLowerCase();
    const match = docs.find((doc) => String(doc.title ?? '').trim().toLowerCase() === wanted);

    if (match) {
      match.description = cleanDescription(fromHardcover.description);
      match.hardcover_id = fromHardcover.id;

      if (!match.cover_url && fromHardcover.cover) {
        match.cover_url = fromHardcover.cover;
      }
    }
  }

  return json({ numFound: fromOl.numFound, start: 0, docs }, { maxAge: 3600 });
}

/** GET /works/{OL...W}.json */
export async function work(request, env, url, rawKey) {
  const key = normaliseOlKey(rawKey);

  if (!key) {
    return notFound('Ongeldige werk-sleutel');
  }

  const record = await ol.getWork(env, key).catch(() => null);

  if (!record) {
    return notFound('Werk niet gevonden');
  }

  const authorKeys = (record.authors ?? [])
    .map((entry) => normaliseOlKey(entry?.author?.key ?? entry?.key))
    .filter(Boolean);

  const authors = await mapWithLimit(authorKeys.slice(0, 3), 3, (authorKey) =>
    ol.getAuthor(env, authorKey).catch(() => null),
  );

  const authorName = authors.find(Boolean)?.name ?? null;
  const cacheKey = `enrich:work:${key}`;
  let enrichment = await kvGet(env, cacheKey);

  if (!enrichment) {
    enrichment = await fetchEnrichment(env, record.title, authorName, null).catch(() => null);

    if (enrichment) {
      await kvPut(env, cacheKey, enrichment, ENRICH_TTL);
    }
  }

  const description = bestDescription(record.description, enrichment?.description);

  return json(
    {
      ...record,
      // Open Library's eigen vorm behouden, zodat bestaande parsers blijven werken.
      description: description || record.description,
      cover_url: ol.coverUrl(record.covers?.[0]) ?? enrichment?.cover ?? null,
      author_names: authors.filter(Boolean).map((author) => author.name),
      // Extra velden - Shelfarr negeert wat het niet kent.
      series: enrichment?.series ?? null,
      number_of_pages: enrichment?.pages ?? null,
    },
    { maxAge: 86400 },
  );
}

/** GET /authors/{OL...A}.json */
export async function author(request, env, url, rawKey) {
  const key = normaliseOlKey(rawKey);

  if (!key) {
    return notFound('Ongeldige auteur-sleutel');
  }

  const record = await ol.getAuthor(env, key).catch(() => null);

  if (!record) {
    return notFound('Auteur niet gevonden');
  }

  return json(
    {
      ...record,
      bio: cleanDescription(record.bio) || null,
      photo_url: ol.coverUrl(record.photos?.find((photo) => Number(photo) > 0)),
    },
    { maxAge: 86400 },
  );
}

/** GET /authors/{OL...A}/works.json - ongewijzigd doorgeven. */
export async function authorWorks(request, env, url, rawKey) {
  const key = normaliseOlKey(rawKey);

  if (!key) {
    return notFound('Ongeldige auteur-sleutel');
  }

  const limit = Math.min(Number.parseInt(url.searchParams.get('limit') ?? '50', 10) || 50, 1000);
  const offset = Number.parseInt(url.searchParams.get('offset') ?? '0', 10) || 0;

  const payload = await tryFetchJson(
    `https://openlibrary.org/authors/${key}/works.json?limit=${limit}&offset=${offset}`,
    { env, cacheTtl: 86400 },
  );

  return payload ? json(payload, { maxAge: 86400 }) : notFound('Auteur niet gevonden');
}

/** GET /isbn/{isbn}.json */
export async function isbn(request, env, url, rawIsbn) {
  // Streepjes eruit, maar niet omzetten naar ISBN-13: Open Library indexeert
  // sommige edities alleen onder hun ISBN-10.
  const value = String(rawIsbn ?? '').replace(/[^0-9Xx]/g, '');

  if (value.length !== 10 && value.length !== 13) {
    return notFound('Ongeldig ISBN');
  }

  const record = await ol.getByIsbn(env, value).catch(() => null);

  if (!record) {
    return notFound('ISBN niet gevonden');
  }

  const enrichment = await fetchEnrichment(
    env,
    record.title,
    null,
    normaliseIsbn13([...(record.isbn_13 ?? []), ...(record.isbn_10 ?? [])]),
  ).catch(() => null);

  return json(
    {
      ...record,
      description: bestDescription(record.description, enrichment?.description) || record.description,
      cover_url: ol.coverUrl(record.covers?.[0]) ?? enrichment?.cover ?? null,
      number_of_pages: record.number_of_pages ?? enrichment?.pages ?? null,
    },
    { maxAge: 86400 },
  );
}
