// Readarr-compatibele laag (vervanger van api.bookinfo.club).
//
// Let op de PascalCase-sleutels: Readarr deserialiseert de auteur- en
// werk-endpoints met System.Text.Json en PropertyNameCaseInsensitive = false.
// camelCase levert daar stilletjes lege objecten op.

import { buildAuthor, buildWork, enrichAuthorWorks } from '../core/enrich.js';
import * as ol from '../providers/openlibrary.js';
import { idToOlKey, normaliseOlKey, olKeyToId } from '../lib/ids.js';
import { mapWithLimit } from '../lib/http.js';
import { json, notFound, badRequest } from '../lib/respond.js';

export function bookResource(edition) {
  return {
    ForeignId: edition.id,
    Asin: edition.asin ?? null,
    Description: edition.description || null,
    Isbn13: edition.isbn13 ?? null,
    Title: edition.title,
    Language: edition.language ?? null,
    Format: edition.format ?? null,
    EditionInformation: edition.editionInformation ?? null,
    Publisher: edition.publisher ?? null,
    ImageUrl: edition.image ?? null,
    IsEbook: Boolean(edition.isEbook),
    NumPages: edition.pages ?? null,
    RatingCount: Math.round(edition.ratings?.count ?? 0),
    AverageRating: Number(edition.ratings?.average ?? 0),
    Url: edition.url ?? null,
    ReleaseDate: edition.releaseDate ?? null,
    Contributors: (edition.contributors ?? []).map((contributor) => ({
      ForeignId: contributor.id,
      Role: contributor.role,
    })),
  };
}

export function workResource(work, { includeAuthors = false } = {}) {
  return {
    ForeignId: work.id,
    Title: work.title,
    Url: work.url,
    ReleaseDate: work.releaseDate ?? null,
    Genres: work.genres ?? [],
    RelatedWorks: work.relatedWorks ?? [],
    Books: (work.editions ?? []).map(bookResource),
    Series: [],
    Authors: includeAuthors ? (work.authors ?? []).map(authorStub) : [],
  };
}

export function authorStub(author) {
  return {
    ForeignId: author.id,
    Name: author.name ?? 'Unknown',
    Description: author.description ?? null,
    ImageUrl: author.image ?? null,
    Url: author.url ?? `https://openlibrary.org/authors/${author.key ?? ''}`,
    RatingCount: Math.round(author.ratings?.count ?? 0),
    AverageRating: Number(author.ratings?.average ?? 0),
    Works: [],
    Series: [],
  };
}

export function seriesResource(entry) {
  return {
    ForeignId: entry.id,
    Title: entry.name ?? 'Series',
    Description: entry.description ?? '',
    LinkItems: (entry.links ?? []).map((link) => ({
      ForeignWorkId: link.workId,
      PositionInSeries: link.position ?? '',
      SeriesPosition: Number.parseInt(link.position, 10) || 0,
      Primary: Boolean(link.primary),
    })),
  };
}

function limits(env) {
  return {
    maxWorks: Number.parseInt(env?.MAX_AUTHOR_WORKS ?? '500', 10) || 500,
    maxEditions: Number.parseInt(env?.MAX_WORK_EDITIONS ?? '40', 10) || 40,
    batchSize: Number.parseInt(env?.ENRICH_BATCH_SIZE ?? '20', 10) || 20,
  };
}

/** GET /v1/author/changed?since=... */
export function authorChanged(url) {
  // We houden geen wijzigingslog bij. Limited: true vertelt Readarr eerlijk dat
  // het antwoord onbruikbaar is, waarna het gewoon een volledige refresh doet.
  return json({
    Limited: true,
    Since: url.searchParams.get('since') ?? new Date(0).toISOString(),
    Ids: [],
  });
}

/** GET /v1/author/{id} */
export async function author(request, env, ctx, rawId) {
  const key = idToOlKey(rawId, 'author');

  if (!key) {
    return badRequest('Ongeldig auteur-id');
  }

  const { maxWorks, batchSize } = limits(env);
  const result = await buildAuthor(env, key, { maxWorks });

  if (!result) {
    return notFound('Auteur niet gevonden');
  }

  // Verrijking loopt door nadat het antwoord verstuurd is; de volgende refresh
  // van Readarr krijgt de betere beschrijvingen en series binnen.
  ctx?.waitUntil?.(enrichAuthorWorks(env, key, result.works, { batchSize }).catch(() => {}));

  return json({
    ...authorStub(result.author),
    Works: result.works.map((work) => workResource(work)),
    Series: result.series.map(seriesResource),
  });
}

/** GET /v1/work/{id} */
export async function work(request, env, ctx, rawId) {
  const key = idToOlKey(rawId, 'work');

  if (!key) {
    return badRequest('Ongeldig werk-id');
  }

  const { maxEditions } = limits(env);
  const built = await buildWork(env, key, { maxEditions });

  if (!built) {
    return notFound('Werk niet gevonden');
  }

  if (built.authors.length === 0) {
    // Readarr gooit een exception op een werk zonder auteurs; liever een nette 404.
    return notFound('Werk zonder bruikbare auteur');
  }

  const series = built.series.map((entry) =>
    seriesResource({ ...entry, links: [{ workId: built.id, position: entry.position, primary: entry.primary }] }),
  );

  return json({
    ...workResource(built, { includeAuthors: true }),
    Series: series,
  });
}

/** GET /v1/book/{id} - Readarr verwacht hier een redirect naar het werk. */
export async function book(request, env, ctx, rawId) {
  const key = idToOlKey(rawId, 'edition');

  if (!key) {
    return badRequest('Ongeldig editie-id');
  }

  const record = await ol.getEdition(env, key);
  const workKey = normaliseOlKey(record?.works?.[0]?.key);
  const workId = olKeyToId(workKey);

  if (!workId) {
    return notFound('Editie niet gevonden');
  }

  const target = new URL(request.url);
  target.pathname = `/v1/work/${workId}`;
  target.search = '';

  return new Response(null, {
    status: 302,
    headers: { Location: target.toString(), 'Cache-Control': 'public, max-age=86400' },
  });
}

/** POST /v1/book/bulk - body is een JSON-array met editie-id's. */
export async function bulk(request, env) {
  let ids;

  try {
    ids = await request.json();
  } catch {
    return badRequest('Body moet een JSON-array met editie-id\'s zijn');
  }

  if (!Array.isArray(ids)) {
    return badRequest('Body moet een JSON-array met editie-id\'s zijn');
  }

  const { maxEditions } = limits(env);
  // Begrensd: elke editie kost meerdere upstream-calls en een Worker heeft een
  // subrequest-budget per request.
  const wanted = ids.slice(0, 20);

  const editionKeys = await mapWithLimit(wanted, 4, async (id) => {
    const key = idToOlKey(id, 'edition');

    if (!key) {
      return null;
    }

    const record = await ol.getEdition(env, key).catch(() => null);

    return normaliseOlKey(record?.works?.[0]?.key);
  });

  const uniqueWorkKeys = [...new Set(editionKeys.filter(Boolean))];
  const works = (
    await mapWithLimit(uniqueWorkKeys, 3, (workKey) =>
      buildWork(env, workKey, { maxEditions }).catch(() => null),
    )
  ).filter(Boolean);

  const authors = new Map();
  const series = new Map();

  for (const built of works) {
    for (const entry of built.authors) {
      if (!authors.has(entry.id)) {
        authors.set(entry.id, authorStub(entry));
      }
    }

    for (const entry of built.series) {
      const existing = series.get(entry.id) ?? { ...entry, links: [] };
      existing.links.push({ workId: built.id, position: entry.position, primary: entry.primary });
      series.set(entry.id, existing);
    }
  }

  // MapBulkBook loopt over elk werk en pakt de eerste contributor; een werk
  // zonder auteur in de Authors-lijst laat Readarr crashen.
  const usable = works.filter((built) => built.editions.some((edition) => edition.contributors.length > 0));

  return json({
    Works: usable.map((built) => workResource(built)),
    Series: [...series.values()].map(seriesResource),
    Authors: [...authors.values()],
  });
}
