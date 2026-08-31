// Hier komt alles samen. Open Library levert de structuur, Hardcover en Google
// Books vullen de gaten. Het resultaat is één canoniek model dat de twee
// route-lagen (Readarr en Shelfarr) elk in hun eigen vorm gieten.

import * as ol from '../providers/openlibrary.js';
import * as hardcover from '../providers/hardcover.js';
import * as google from '../providers/googlebooks.js';
import { kvGet, kvPut } from '../lib/cache.js';
import { mapWithLimit } from '../lib/http.js';
import { olKeyToId, normaliseOlKey, seriesId } from '../lib/ids.js';
import {
  bestDescription,
  cleanDescription,
  cleanGenres,
  cleanSpaces,
  normaliseIsbn13,
  toIsoDate,
} from '../lib/text.js';

const ENRICH_TTL = 60 * 60 * 24 * 14;
const AUTHOR_INDEX_TTL = 60 * 60 * 24 * 3;

function num(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed) ? parsed : fallback;
}

function normaliseLanguage(value) {
  if (!value) {
    return null;
  }

  const raw = Array.isArray(value) ? value[0] : value;
  const key = typeof raw === 'object' ? raw?.key : raw;

  if (typeof key !== 'string') {
    return null;
  }

  // Open Library geeft "/languages/eng"; Google Books geeft "en".
  const code = key.split('/').filter(Boolean).pop().toLowerCase();
  const twoToThree = { en: 'eng', nl: 'dut', de: 'ger', fr: 'fre', es: 'spa', it: 'ita', sv: 'swe', da: 'dan', no: 'nor', pt: 'por' };

  return twoToThree[code] ?? code;
}

function isEbookFormat(format, ebookAccess) {
  if (typeof format === 'string' && /e-?book|electronic|kindle|epub|digital/i.test(format)) {
    return true;
  }

  return ebookAccess === 'public' || ebookAccess === 'borrowable';
}

function authorFromOl(record) {
  const key = normaliseOlKey(record?.key);
  const id = olKeyToId(key);

  if (!id) {
    return null;
  }

  const photo = Array.isArray(record?.photos) ? record.photos.find((p) => Number(p) > 0) : null;

  return {
    id,
    key,
    name: cleanSpaces(record?.name ?? record?.personal_name ?? '') || 'Unknown',
    description: cleanDescription(record?.bio ?? ''),
    image: photo ? ol.coverUrl(photo) : null,
    url: `https://openlibrary.org/authors/${key}`,
    ratings: { count: 0, average: 0 },
  };
}

/**
 * Bouwt een editie uit de velden die de Search-API per werk teruggeeft. Niet zo
 * rijk als een echte editie-call, maar goed genoeg om een werk direct bruikbaar
 * te maken zonder per boek een extra request te doen.
 */
function syntheticEdition(doc, work, contributors) {
  const editionKey = normaliseOlKey(doc.cover_edition_key) ?? normaliseOlKey(doc.edition_key?.[0]);
  const id = olKeyToId(editionKey) ?? work.id;

  return {
    id,
    key: editionKey,
    title: work.title,
    isbn13: normaliseIsbn13(doc.isbn),
    asin: null,
    language: normaliseLanguage(doc.language),
    description: work.description,
    format: null,
    editionInformation: null,
    publisher: Array.isArray(doc.publisher) ? cleanSpaces(doc.publisher[0]) : null,
    pages: num(doc.number_of_pages_median, 0) || null,
    releaseDate: work.releaseDate,
    ratings: { count: num(doc.ratings_count), average: num(doc.ratings_average) },
    image: ol.coverUrl(doc.cover_i) ?? ol.coverUrlByOlid(editionKey),
    url: editionKey ? `https://openlibrary.org/books/${editionKey}` : work.url,
    isEbook: isEbookFormat(null, doc.ebook_access),
    contributors,
  };
}

function editionFromOl(record, work, contributors) {
  const key = normaliseOlKey(record?.key);
  const id = olKeyToId(key);

  if (!id) {
    return null;
  }

  const identifiers = record?.identifiers ?? {};

  return {
    id,
    key,
    title: cleanSpaces(record?.title ?? work.title) || work.title,
    isbn13: normaliseIsbn13([...(record?.isbn_13 ?? []), ...(record?.isbn_10 ?? [])]),
    asin: identifiers?.amazon?.[0] ?? record?.asin ?? null,
    language: normaliseLanguage(record?.languages),
    description: cleanDescription(record?.description ?? '') || work.description,
    format: cleanSpaces(record?.physical_format ?? '') || null,
    editionInformation: cleanSpaces(record?.edition_name ?? '') || null,
    publisher: Array.isArray(record?.publishers) ? cleanSpaces(record.publishers[0]) : null,
    pages: num(record?.number_of_pages, 0) || null,
    releaseDate: toIsoDate(record?.publish_date) ?? work.releaseDate,
    ratings: { count: 0, average: 0 },
    image: ol.coverUrl(record?.covers?.[0]) ?? ol.coverUrlByOlid(key),
    url: `https://openlibrary.org/books/${key}`,
    isEbook: isEbookFormat(record?.physical_format, null),
    contributors,
  };
}

function workFromSearchDoc(doc, { preferredAuthorId = null } = {}) {
  const key = normaliseOlKey(doc?.key);
  const id = olKeyToId(key);

  if (!id) {
    return null;
  }

  const authors = (doc.author_key ?? [])
    .map((authorKey, index) => {
      const authorId = olKeyToId(authorKey);

      return authorId ? { id: authorId, key: normaliseOlKey(authorKey), name: doc.author_name?.[index] ?? null } : null;
    })
    .filter(Boolean);

  // Readarr koppelt een werk aan de auteur via de eerste contributor, dus de
  // opgevraagde auteur moet vooraan staan - anders verdwijnt het boek uit de lijst.
  if (preferredAuthorId) {
    authors.sort((a, b) => Number(b.id === preferredAuthorId) - Number(a.id === preferredAuthorId));
  }

  const contributors = authors.map((author, index) => ({
    id: author.id,
    role: index === 0 ? 'Author' : 'Contributor',
  }));

  const work = {
    id,
    key,
    title: cleanSpaces(doc.title ?? '') || 'Unknown',
    subtitle: cleanSpaces(doc.subtitle ?? '') || null,
    url: `https://openlibrary.org/works/${key}`,
    releaseDate: toIsoDate(doc.first_publish_year),
    description: '',
    genres: cleanGenres(doc.subject),
    relatedWorks: [],
    authors,
    series: [],
    ratings: { count: num(doc.ratings_count), average: num(doc.ratings_average) },
    editions: [],
  };

  work.editions = [syntheticEdition(doc, work, contributors)];

  return work;
}

function applyEnrichment(work, enrichment) {
  if (!enrichment) {
    return work;
  }

  work.description = bestDescription(work.description, enrichment.description);

  if (enrichment.genres?.length && work.genres.length < 3) {
    work.genres = cleanGenres([...work.genres, ...enrichment.genres]);
  }

  if (!work.releaseDate && enrichment.releaseYear) {
    work.releaseDate = toIsoDate(enrichment.releaseYear);
  }

  if (enrichment.series?.id && seriesId(enrichment.series.id)) {
    work.series = [
      {
        id: seriesId(enrichment.series.id),
        name: enrichment.series.name ?? 'Series',
        description: '',
        position: enrichment.series.position ?? null,
        primary: true,
      },
    ];
  }

  for (const edition of work.editions) {
    edition.description = bestDescription(edition.description, enrichment.description);

    if (!edition.pages && enrichment.pages) {
      edition.pages = enrichment.pages;
    }

    if (!edition.publisher && enrichment.publisher) {
      edition.publisher = enrichment.publisher;
    }

    // Hardcover- en Google-covers zijn vaak scherper dan die van Open Library,
    // maar we vervangen alleen als er nog niks was.
    if (!edition.image && enrichment.cover) {
      edition.image = enrichment.cover;
    }
  }

  return work;
}

/** Haalt bij Hardcover en Google Books op wat Open Library niet had. */
export async function fetchEnrichment(env, title, author, isbn13) {
  const [fromHardcover, fromGoogle] = await Promise.all([
    hardcover.isConfigured(env) ? hardcover.enrich(env, title, author).catch(() => null) : Promise.resolve(null),
    isbn13 ? google.byIsbn(env, isbn13) : google.byTitleAuthor(env, title, author),
  ]);

  if (!fromHardcover && !fromGoogle) {
    return null;
  }

  return {
    description: bestDescription(fromHardcover?.description, fromGoogle?.description),
    cover: fromHardcover?.cover ?? fromGoogle?.cover ?? null,
    pages: fromHardcover?.pages ?? fromGoogle?.pageCount ?? null,
    publisher: fromGoogle?.publisher ?? null,
    releaseYear: fromHardcover?.releaseYear ?? null,
    genres: cleanGenres(fromGoogle?.categories ?? []),
    series: fromHardcover?.series ?? null,
  };
}

/** Volledig werk: echte edities, echte identifiers, verrijkte beschrijving. */
export async function buildWork(env, workKey, { maxEditions = 40 } = {}) {
  const key = normaliseOlKey(workKey);
  const id = olKeyToId(key);

  if (!id) {
    return null;
  }

  const record = await ol.getWork(env, key);

  if (!record) {
    return null;
  }

  const authorKeys = (record.authors ?? [])
    .map((entry) => normaliseOlKey(entry?.author?.key ?? entry?.key))
    .filter(Boolean);

  const [authorRecords, editionsPayload, ratings] = await Promise.all([
    mapWithLimit(authorKeys.slice(0, 4), 4, (authorKey) => ol.getAuthor(env, authorKey).catch(() => null)),
    ol.getEditionsOfWork(env, key, maxEditions).catch(() => null),
    ol.getWorkRatings(env, key).catch(() => null),
  ]);

  const authors = authorRecords.map(authorFromOl).filter(Boolean);
  const contributors = authors.map((author, index) => ({
    id: author.id,
    role: index === 0 ? 'Author' : 'Contributor',
  }));

  const work = {
    id,
    key,
    title: cleanSpaces(record.title ?? '') || 'Unknown',
    subtitle: cleanSpaces(record.subtitle ?? '') || null,
    url: `https://openlibrary.org/works/${key}`,
    releaseDate: toIsoDate(record.first_publish_date),
    description: cleanDescription(record.description),
    genres: cleanGenres(record.subjects),
    relatedWorks: [],
    authors,
    series: [],
    ratings: {
      count: num(ratings?.summary?.count),
      average: num(ratings?.summary?.average),
    },
    editions: [],
  };

  const entries = Array.isArray(editionsPayload?.entries) ? editionsPayload.entries : [];

  work.editions = entries
    .map((entry) => editionFromOl(entry, work, contributors))
    .filter(Boolean)
    .sort((a, b) => Number(Boolean(b.isbn13)) - Number(Boolean(a.isbn13)));

  if (work.editions.length === 0) {
    // Zonder edities weigert Readarr het werk; bouw er dan één uit het werk zelf.
    work.editions = [
      {
        id,
        key,
        title: work.title,
        isbn13: null,
        asin: null,
        language: null,
        description: work.description,
        format: null,
        editionInformation: null,
        publisher: null,
        pages: null,
        releaseDate: work.releaseDate,
        ratings: work.ratings,
        image: ol.coverUrl(record.covers?.[0]),
        url: work.url,
        isEbook: false,
        contributors,
      },
    ];
  }

  if (!work.releaseDate) {
    // Open Library laat first_publish_date vaak leeg. De oudste editie is dan de
    // beste schatting - anders staat het boek in Readarr zonder jaartal.
    const dates = work.editions.map((edition) => edition.releaseDate).filter(Boolean).sort();
    work.releaseDate = dates[0] ?? null;
  }

  if (work.editions.length > 0 && work.ratings.count > 0) {
    // Readarr rekent de boekscore uit over de edities, dus de OL-score van het
    // werk moet op minstens één editie staan om zichtbaar te zijn.
    work.editions[0].ratings = work.ratings;
  }

  const cacheKey = `enrich:work:${key}`;
  let enrichment = await kvGet(env, cacheKey);

  if (!enrichment) {
    enrichment = await fetchEnrichment(env, work.title, authors[0]?.name, work.editions[0]?.isbn13);

    if (enrichment) {
      await kvPut(env, cacheKey, enrichment, ENRICH_TTL);
    }
  }

  return applyEnrichment(work, enrichment);
}

/** Auteur plus al hun werken, in twee tot drie requests. */
export async function buildAuthor(env, authorKey, { maxWorks = 500 } = {}) {
  const key = normaliseOlKey(authorKey);
  const id = olKeyToId(key);

  if (!id) {
    return null;
  }

  const [record, docs] = await Promise.all([
    ol.getAuthor(env, key),
    ol.searchWorksByAuthor(env, key, { limit: maxWorks }).catch(() => []),
  ]);

  if (!record) {
    return null;
  }

  const author = authorFromOl({ ...record, key: record.key ?? key });

  if (!author) {
    return null;
  }

  const enrichmentMap = (await kvGet(env, `enrich:author:${key}`)) ?? {};
  const works = [];

  for (const doc of docs) {
    const work = workFromSearchDoc(doc, { preferredAuthorId: id });

    if (!work) {
      continue;
    }

    // Werken waar deze auteur niet de eerste bijdrager van is, laat Readarr
    // toch vallen. Ze meesturen levert alleen ruis op.
    if (work.authors[0]?.id !== id) {
      continue;
    }

    works.push(applyEnrichment(work, enrichmentMap[work.key]));
  }

  const ratedWorks = works.filter((work) => work.ratings.count > 0);

  author.ratings = {
    count: ratedWorks.reduce((total, work) => total + work.ratings.count, 0),
    average: ratedWorks.length
      ? ratedWorks.reduce((total, work) => total + work.ratings.average * work.ratings.count, 0) /
        Math.max(1, ratedWorks.reduce((total, work) => total + work.ratings.count, 0))
      : 0,
  };

  const series = new Map();

  for (const work of works) {
    for (const entry of work.series) {
      const existing = series.get(entry.id) ?? { ...entry, links: [] };
      existing.links.push({ workId: work.id, position: entry.position, primary: entry.primary });
      series.set(entry.id, existing);
    }
  }

  return { author, works, series: [...series.values()] };
}

/**
 * Achtergrondtaak: verrijk de populairste werken van een auteur bij Hardcover en
 * Google Books en leg het resultaat in KV. De volgende refresh van Readarr pikt
 * het automatisch op. Bewust begrensd - een Worker heeft een subrequest-budget.
 */
export async function enrichAuthorWorks(env, authorKey, works, { batchSize = 20 } = {}) {
  const key = normaliseOlKey(authorKey);

  if (!key || works.length === 0) {
    return;
  }

  const cacheKey = `enrich:author:${key}`;
  const existing = (await kvGet(env, cacheKey)) ?? {};

  const candidates = works
    .filter((work) => !existing[work.key])
    .sort((a, b) => b.ratings.count - a.ratings.count)
    .slice(0, batchSize);

  if (candidates.length === 0) {
    return;
  }

  const results = await mapWithLimit(candidates, 4, async (work) => {
    const enrichment = await fetchEnrichment(
      env,
      work.title,
      work.authors[0]?.name,
      work.editions[0]?.isbn13,
    ).catch(() => null);

    return [work.key, enrichment];
  });

  for (const [workKey, enrichment] of results) {
    // Ook een leeg resultaat onthouden, anders blijven we het elke ronde opnieuw
    // proberen voor boeken die nergens te vinden zijn.
    existing[workKey] = enrichment ?? {};
  }

  await kvPut(env, cacheKey, existing, AUTHOR_INDEX_TTL);
}

export { workFromSearchDoc, applyEnrichment };
