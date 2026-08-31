// Router. Twee oppervlakken op één Worker:
//
//   /v1/*        Readarr (BookInfo-contract, vervanger van api.bookinfo.club)
//   /search.json, /works/*, /authors/*, /isbn/*
//                Shelfarr (Open Library-contract)
//
// De Open Library-routes staan bewust ook op de root, zodat je Shelfarr via een
// host-override naar deze Worker kunt sturen zonder de paden te herschrijven.

import * as bookinfo from './routes/bookinfo.js';
import * as openlibrary from './routes/openlibrary.js';
import { UpstreamError } from './lib/http.js';
import { badRequest, json, notFound, rateLimited, serverError } from './lib/respond.js';

const INDEX = {
  name: 'book-metadata-proxy',
  description:
    'Rijkere boek-metadata voor Readarr en Shelfarr, samengesteld uit Open Library, Hardcover en Google Books.',
  surfaces: {
    readarr: {
      note: 'Zet dit adres in Readarr onder Settings > General > Metadata als Metadata Source.',
      endpoints: [
        'GET  /v1/author/{id}',
        'GET  /v1/author/changed?since={iso8601}',
        'GET  /v1/work/{id}',
        'GET  /v1/book/{id}  (302 naar /v1/work/{id})',
        'POST /v1/book/bulk  (body: JSON-array met editie-id\'s)',
      ],
      ids: 'Integer-id\'s zijn het cijferdeel van de Open Library-sleutel: OL45804W -> 45804.',
    },
    shelfarr: {
      note: 'Shelfarr heeft openlibrary.org hard in de code staan; wijs die host via DNS of een reverse proxy hierheen.',
      endpoints: [
        'GET /search.json?q={query}&limit={n}',
        'GET /works/{OL...W}.json',
        'GET /authors/{OL...A}.json',
        'GET /authors/{OL...A}/works.json',
        'GET /isbn/{isbn}.json',
      ],
    },
  },
};

function health(env) {
  return json({
    status: 'ok',
    providers: {
      openLibrary: true,
      hardcover: Boolean(env?.HARDCOVER_TOKEN),
      googleBooks: true,
      googleBooksKeyed: Boolean(env?.GOOGLE_BOOKS_KEY),
    },
    kv: Boolean(env?.METADATA),
  });
}

async function route(request, env, ctx) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, '') || '/';

  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  if (path === '/') {
    return json(INDEX);
  }

  if (path === '/health') {
    return health(env);
  }

  // --- Readarr -------------------------------------------------------------

  if (path === '/v1/author/changed') {
    return bookinfo.authorChanged(url);
  }

  if (path === '/v1/book/bulk') {
    if (request.method !== 'POST') {
      return badRequest('Gebruik POST voor /v1/book/bulk');
    }

    return bookinfo.bulk(request, env);
  }

  const readarrMatch = path.match(/^\/v1\/(author|work|book)\/(\d+)$/);

  if (readarrMatch) {
    const [, kind, id] = readarrMatch;

    if (kind === 'author') {
      return bookinfo.author(request, env, ctx, id);
    }

    if (kind === 'work') {
      return bookinfo.work(request, env, ctx, id);
    }

    return bookinfo.book(request, env, ctx, id);
  }

  // --- Shelfarr / Open Library --------------------------------------------
  // Ook bereikbaar onder /openlibrary/... om te kunnen testen zonder de host
  // van openlibrary.org om te leggen.

  const olPath = path.startsWith('/openlibrary/') ? path.slice('/openlibrary'.length) : path;

  if (olPath === '/search.json') {
    return openlibrary.search(request, env, url);
  }

  const workMatch = olPath.match(/^\/works\/(OL\d+W)\.json$/);

  if (workMatch) {
    return openlibrary.work(request, env, url, workMatch[1]);
  }

  const authorWorksMatch = olPath.match(/^\/authors\/(OL\d+A)\/works\.json$/);

  if (authorWorksMatch) {
    return openlibrary.authorWorks(request, env, url, authorWorksMatch[1]);
  }

  const authorMatch = olPath.match(/^\/authors\/(OL\d+A)\.json$/);

  if (authorMatch) {
    return openlibrary.author(request, env, url, authorMatch[1]);
  }

  const isbnMatch = olPath.match(/^\/isbn\/([0-9Xx-]+)\.json$/);

  if (isbnMatch) {
    return openlibrary.isbn(request, env, url, isbnMatch[1]);
  }

  return notFound('Onbekend endpoint - zie / voor de lijst');
}

export default {
  async fetch(request, env, ctx) {
    try {
      return await route(request, env, ctx);
    } catch (error) {
      if (error instanceof UpstreamError) {
        // Readarr kent 429 met Retry-After en wacht dan netjes; dat is beter dan
        // een 500 waarop het de refresh afbreekt.
        if (error.status === 429) {
          return rateLimited(error.retryAfter ?? 30);
        }

        return json({ error: error.message, upstream: error.url }, { status: 502 });
      }

      return serverError(error?.message ?? 'Onbekende fout');
    }
  },
};
