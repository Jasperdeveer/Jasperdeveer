// Hardcover is de kwaliteitslaag: het heeft de beste beschrijvingen, actuele
// covers en - belangrijk voor Readarr - echte serie-informatie met posities.
// De API is GraphQL en vereist een token van https://hardcover.app/account/api.

import { UpstreamError } from '../lib/http.js';

const ENDPOINT = 'https://api.hardcover.app/v1/graphql';

export function isConfigured(env) {
  return Boolean(env?.HARDCOVER_TOKEN);
}

async function graphql(env, query, variables, { timeoutMs = 15000 } = {}) {
  if (!isConfigured(env)) {
    return null;
  }

  const token = String(env.HARDCOVER_TOKEN).trim().replace(/^Bearer\s+/i, '');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(ENDPOINT, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        'User-Agent': `book-metadata-proxy/1.0 (+${env.CONTACT_EMAIL || 'unknown@example.com'})`,
      },
      body: JSON.stringify({ query, variables }),
    });

    if (response.status === 429) {
      const retryAfter = Number(response.headers.get('Retry-After'));

      throw new UpstreamError('Hardcover rate limit', {
        status: 429,
        url: ENDPOINT,
        retryAfter: Number.isFinite(retryAfter) ? retryAfter : 60,
      });
    }

    if (response.status === 401 || response.status === 403) {
      throw new UpstreamError('Hardcover token ongeldig', { status: response.status, url: ENDPOINT });
    }

    if (!response.ok) {
      throw new UpstreamError(`Hardcover ${response.status}`, { status: response.status, url: ENDPOINT });
    }

    const payload = await response.json();

    if (Array.isArray(payload?.errors) && payload.errors.length > 0) {
      throw new UpstreamError(payload.errors.map((e) => e.message).join(', '), {
        status: 400,
        url: ENDPOINT,
      });
    }

    return payload?.data ?? null;
  } finally {
    clearTimeout(timer);
  }
}

const SEARCH_QUERY = `
  query SearchBooks($query: String!, $perPage: Int!) {
    search(query: $query, query_type: "Book", per_page: $perPage) {
      results
    }
  }
`;

const BOOK_QUERY = `
  query GetBook($id: Int!) {
    books(where: { id: { _eq: $id } }) {
      id
      title
      description
      release_year
      cached_image
      contributions { author { id name } }
      default_physical_edition { pages }
      book_series { position series { id name } }
      featured_book_series { position series { id name } }
    }
  }
`;

function coverOf(doc) {
  const cached = doc?.cached_image;
  const image = doc?.image;

  return (typeof cached === 'object' ? cached?.url : cached) || (typeof image === 'object' ? image?.url : image) || null;
}

function normalisePosition(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  return String(value);
}

function seriesOf(book) {
  const featured = book?.featured_book_series;
  const entry =
    (featured && !Array.isArray(featured) ? featured : null) ??
    (Array.isArray(featured) ? featured[0] : null) ??
    (Array.isArray(book?.book_series) ? book.book_series[0] : null);

  if (!entry?.series?.id) {
    return null;
  }

  return {
    id: Number(entry.series.id),
    name: entry.series.name ?? null,
    position: normalisePosition(entry.position),
  };
}

/** Zoekt een boek op titel (+ auteur) en geeft het beste kandidaat-document terug. */
export async function findBook(env, title, author) {
  const query = [title, author].filter(Boolean).join(' ').trim();

  if (!query) {
    return null;
  }

  const data = await graphql(env, SEARCH_QUERY, { query, perPage: 5 });
  const hits = data?.search?.results?.hits;

  if (!Array.isArray(hits) || hits.length === 0) {
    return null;
  }

  const wanted = title.trim().toLowerCase();
  const documents = hits.map((hit) => hit?.document).filter(Boolean);

  // Liever een exacte titelmatch dan de populairste treffer: de zoekmachine van
  // Hardcover geeft anders graag een omnibus of studiegids terug.
  const exact = documents.find((doc) => String(doc.title ?? '').trim().toLowerCase() === wanted);
  const doc = exact ?? documents[0];

  return {
    id: Number(doc.id) || null,
    title: doc.title ?? null,
    description: doc.description ?? null,
    releaseYear: doc.release_year ?? null,
    cover: coverOf(doc),
    hasEbook: Boolean(doc.has_ebook),
    hasAudiobook: Boolean(doc.has_audiobook),
    authors: Array.isArray(doc.author_names) ? doc.author_names : [],
  };
}

/** Volledige details van één Hardcover-boek, inclusief serie en paginacount. */
export async function getBook(env, bookId) {
  const id = Number(bookId);

  if (!Number.isSafeInteger(id) || id <= 0) {
    return null;
  }

  const data = await graphql(env, BOOK_QUERY, { id });
  const book = data?.books?.[0];

  if (!book) {
    return null;
  }

  return {
    id: Number(book.id),
    title: book.title ?? null,
    description: book.description ?? null,
    releaseYear: book.release_year ?? null,
    cover: coverOf(book),
    pages: book.default_physical_edition?.pages ?? null,
    authors: (book.contributions ?? []).map((c) => c?.author?.name).filter(Boolean),
    series: seriesOf(book),
  };
}

/** Zoeken en meteen verdiepen - dit is wat de verrijkingsstap gebruikt. */
export async function enrich(env, title, author) {
  const found = await findBook(env, title, author);

  if (!found?.id) {
    return null;
  }

  const details = await getBook(env, found.id);

  return {
    ...found,
    ...(details ?? {}),
    description: details?.description || found.description || null,
    cover: details?.cover || found.cover || null,
  };
}
