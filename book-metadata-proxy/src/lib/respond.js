const BASE_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Access-Control-Allow-Origin': '*',
};

export function json(body, { status = 200, maxAge = 0 } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...BASE_HEADERS,
      ...(maxAge > 0 ? { 'Cache-Control': `public, max-age=${maxAge}` } : {}),
    },
  });
}

export function notFound(message = 'Niet gevonden') {
  return json({ error: message }, { status: 404 });
}

export function badRequest(message = 'Ongeldig verzoek') {
  return json({ error: message }, { status: 400 });
}

export function serverError(message = 'Interne fout') {
  return json({ error: message }, { status: 500 });
}

export function rateLimited(retryAfter = 30) {
  return new Response(JSON.stringify({ error: 'Upstream rate limit' }), {
    status: 429,
    headers: { ...BASE_HEADERS, 'Retry-After': String(retryAfter) },
  });
}
