// Eén plek voor alle uitgaande calls: nette User-Agent, timeout, en respect
// voor 429/Retry-After. Open Library blokkeert clients zonder contactadres,
// dus dat zit hier hard in.

export class UpstreamError extends Error {
  constructor(message, { status = 0, url = '', retryAfter = null } = {}) {
    super(message);
    this.name = 'UpstreamError';
    this.status = status;
    this.url = url;
    this.retryAfter = retryAfter;
  }
}

function userAgent(env) {
  const contact = env?.CONTACT_EMAIL || 'unknown@example.com';

  return `book-metadata-proxy/1.0 (+${contact})`;
}

function parseRetryAfter(response) {
  const header = response.headers.get('Retry-After');

  if (!header) {
    return null;
  }

  const seconds = Number(header);

  if (Number.isFinite(seconds)) {
    return Math.max(1, Math.min(3600, Math.round(seconds)));
  }

  const date = Date.parse(header);

  return Number.isNaN(date) ? null : Math.max(1, Math.round((date - Date.now()) / 1000));
}

/**
 * Haalt JSON op. Geeft null bij 404 (dat is een geldig antwoord: bestaat niet),
 * gooit UpstreamError bij echte fouten.
 */
export async function fetchJson(url, { env, method = 'GET', headers = {}, body, timeoutMs = 10000, cacheTtl = 0 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method,
      body,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'User-Agent': userAgent(env),
        ...headers,
      },
      // Laat Cloudflare het edge-antwoord bewaren; scheelt fors bij Readarr,
      // dat tijdens een library-refresh dezelfde werken snel achter elkaar opvraagt.
      ...(cacheTtl > 0 ? { cf: { cacheTtl, cacheEverything: true } } : {}),
    });

    if (response.status === 404) {
      return null;
    }

    if (response.status === 429) {
      throw new UpstreamError('Upstream rate limit', {
        status: 429,
        url,
        retryAfter: parseRetryAfter(response),
      });
    }

    if (!response.ok) {
      throw new UpstreamError(`Upstream ${response.status}`, { status: response.status, url });
    }

    return await response.json();
  } catch (error) {
    if (error instanceof UpstreamError) {
      throw error;
    }

    if (error.name === 'AbortError') {
      throw new UpstreamError('Upstream timeout', { status: 504, url });
    }

    throw new UpstreamError(error.message || 'Upstream failure', { status: 502, url });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Verrijking mag nooit een antwoord blokkeren: als Hardcover of Google Books
 * hapert, valt de proxy stilletjes terug op wat Open Library al gaf.
 */
export async function tryFetchJson(...args) {
  try {
    return await fetchJson(...args);
  } catch {
    return null;
  }
}

/** Voert taken uit met begrensde parallelliteit (Workers heeft een subrequest-budget). */
export async function mapWithLimit(items, limit, task) {
  const results = new Array(items.length);
  let cursor = 0;

  const workers = new Array(Math.min(limit, items.length)).fill(null).map(async () => {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await task(items[index], index);
    }
  });

  await Promise.all(workers);

  return results;
}
