import { test } from 'node:test';
import assert from 'node:assert/strict';
import { idToOlKey, normaliseOlKey, olKeyToId, olPath, seriesId } from '../src/lib/ids.js';

test('sleutel en id zijn heen en terug hetzelfde', () => {
  for (const [key, kind] of [['OL45804W', 'work'], ['OL7353617M', 'edition'], ['OL34184A', 'author']]) {
    const id = olKeyToId(key);
    assert.equal(idToOlKey(id, kind), key);
  }
});

test('accepteert zowel volledige paden als kale sleutels', () => {
  assert.equal(normaliseOlKey('/works/OL45804W'), 'OL45804W');
  assert.equal(normaliseOlKey('OL45804W'), 'OL45804W');
  assert.equal(olKeyToId('/authors/OL34184A'), 34184);
});

test('weigert onbruikbare invoer in plaats van iets te verzinnen', () => {
  for (const bad of [null, undefined, '', 'OL', 'ABC123W', 'OL12X', 42, '/works/']) {
    assert.equal(olKeyToId(bad), null, `olKeyToId(${JSON.stringify(bad)})`);
  }

  assert.equal(idToOlKey(0, 'work'), null);
  assert.equal(idToOlKey(-1, 'work'), null);
  assert.equal(idToOlKey(12, 'onzin'), null);
});

test('blijft binnen int32, want Readarr leest de id als int', () => {
  assert.equal(olKeyToId('OL2147483647W'), 2147483647);
  assert.equal(olKeyToId('OL2147483648W'), null);
  assert.equal(seriesId(2147483648), null);
  assert.equal(seriesId(99), 99);
});

test('olPath geeft het pad dat Open Library zelf gebruikt', () => {
  assert.equal(olPath('OL45804W'), '/works/OL45804W');
  assert.equal(olPath('OL7353617M'), '/books/OL7353617M');
  assert.equal(olPath('OL34184A'), '/authors/OL34184A');
});
