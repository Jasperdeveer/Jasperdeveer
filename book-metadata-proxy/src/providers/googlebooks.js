// Google Books is de derde bron. Het wint zelden op structuur, maar heeft vaak
// wel een beschrijving waar Open Library er geen heeft, plus betrouwbare
// uitgever-, taal- en paginagegevens per ISBN.

import { tryFetchJson } from '../lib/http.js';

const BASE = 'https://www.googleapis.com/books/v1/volumes';

function withKey(env, url) {
  return env?.GOOGLE_BOOKS_KEY ? `${url}&key=${encodeURIComponent(env.GOOGLE_BOOKS_KEY)}` : url;
}

function mapVolume(item) {
  const info = item?.volumeInfo;

  if (!info) {
    return null;
  }

  const identifiers = Array.isArray(info.industryIdentifiers) ? info.industryIdentifiers : [];

  return {
    title: info.title ?? null,
    subtitle: info.subtitle ?? null,
    description: info.description ?? null,
    publisher: info.publisher ?? null,
    publishedDate: info.publishedDate ?? null,
    pageCount: Number.isFinite(info.pageCount) ? info.pageCount : null,
    language: info.language ?? null,
    categories: Array.isArray(info.categories) ? info.categories : [],
    authors: Array.isArray(info.authors) ? info.authors : [],
    averageRating: Number.isFinite(info.averageRating) ? info.averageRating : null,
    ratingsCount: Number.isFinite(info.ratingsCount) ? info.ratingsCount : null,
    isbn13: identifiers.find((i) => i.type === 'ISBN_13')?.identifier ?? null,
    // De thumbnail-URL's zijn http en met zoom=1; https + zoom=2 geeft een
    // bruikbaardere cover in Readarr.
    cover: (info.imageLinks?.thumbnail ?? info.imageLinks?.smallThumbnail ?? null)
      ?.replace(/^http:/, 'https:')
      .replace(/&edge=curl/, '')
      .replace(/zoom=\d/, 'zoom=2') ?? null,
  };
}

export async function byIsbn(env, isbn) {
  if (!isbn) {
    return null;
  }

  const payload = await tryFetchJson(withKey(env, `${BASE}?q=isbn:${encodeURIComponent(isbn)}&maxResults=1`), {
    env,
    cacheTtl: 86400,
  });

  return mapVolume(payload?.items?.[0]);
}

export async function byTitleAuthor(env, title, author) {
  if (!title) {
    return null;
  }

  const terms = [`intitle:${JSON.stringify(title)}`];

  if (author) {
    terms.push(`inauthor:${JSON.stringify(author)}`);
  }

  const payload = await tryFetchJson(
    withKey(env, `${BASE}?q=${encodeURIComponent(terms.join('+'))}&maxResults=3&orderBy=relevance`),
    { env, cacheTtl: 86400 },
  );

  const items = Array.isArray(payload?.items) ? payload.items : [];
  const wanted = title.trim().toLowerCase();
  const exact = items.find((item) => String(item?.volumeInfo?.title ?? '').trim().toLowerCase() === wanted);

  return mapVolume(exact ?? items[0]);
}
