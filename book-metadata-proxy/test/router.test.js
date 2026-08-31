import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';

const env = { CONTACT_EMAIL: 'test@example.com' };
const ctx = { waitUntil() {} };
const call = (path, init) => worker.fetch(new Request(`https://proxy.test${path}`, init), env, ctx);

test('index en health werken zonder netwerk', async () => {
  assert.equal((await call('/')).status, 200);

  const health = await (await call('/health')).json();
  assert.equal(health.status, 'ok');
  assert.equal(health.providers.hardcover, false);
});

test('author/changed meldt eerlijk dat het geen wijzigingslog heeft', async () => {
  // Limited: true laat Readarr terugvallen op een volledige refresh.
  const body = await (await call('/v1/author/changed?since=2024-01-01T00:00:00Z')).json();

  assert.equal(body.Limited, true);
  assert.deepEqual(body.Ids, []);
});

test('changed wordt niet als auteur-id gelezen', async () => {
  // /v1/author/changed moet vóór /v1/author/{id} matchen.
  const body = await (await call('/v1/author/changed')).json();
  assert.equal(body.Limited, true);
});

test('bulk weigert GET en onzin-bodies', async () => {
  assert.equal((await call('/v1/book/bulk')).status, 400);
  assert.equal((await call('/v1/book/bulk', { method: 'POST', body: 'geen json' })).status, 400);
  assert.equal(
    (await call('/v1/book/bulk', { method: 'POST', body: JSON.stringify({ niet: 'array' }) })).status,
    400,
  );
});

test('onbekende paden geven 404, geen 500', async () => {
  for (const path of ['/onzin', '/v1/author/abc', '/works/onzin.json', '/v1/']) {
    assert.equal((await call(path)).status, 404, path);
  }
});

test('CORS-preflight wordt beantwoord', async () => {
  const response = await call('/v1/work/1', { method: 'OPTIONS' });

  assert.equal(response.status, 204);
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), '*');
});
