import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  bestDescription,
  cleanDescription,
  cleanGenres,
  isbn10To13,
  normaliseIsbn13,
  stripHtml,
  toIsoDate,
} from '../src/lib/text.js';

test('beschrijving werkt met beide vormen van Open Library', () => {
  assert.equal(cleanDescription('Gewoon tekst.'), 'Gewoon tekst.');
  assert.equal(cleanDescription({ type: '/type/text', value: 'Uit een object.' }), 'Uit een object.');
  assert.equal(cleanDescription(null), '');
});

test('bronvoetnoot van Open Library wordt weggehaald', () => {
  const input = 'Een echte beschrijving.\n\n([source][1])\n\n[1]: https://en.wikipedia.org/wiki/Boek';
  assert.equal(cleanDescription(input), 'Een echte beschrijving.');
});

test('html wordt tekst, niet weggegooid', () => {
  assert.equal(stripHtml('<p>Een<br>twee</p>').trim(), 'Een\ntwee');
  assert.equal(stripHtml('Fish &amp; Chips'), 'Fish & Chips');
});

test('langste zinnige beschrijving wint', () => {
  assert.equal(bestDescription('kort', 'Dit is een veel langere en bruikbare beschrijving.'),
    'Dit is een veel langere en bruikbare beschrijving.');
  // Te korte fragmenten tellen niet mee.
  assert.equal(bestDescription('n.v.t.', ''), '');
});

test('datums komen er als ISO uit, ook uit rommelige invoer', () => {
  assert.equal(toIsoDate(1949), '1949-01-01T00:00:00Z');
  assert.equal(toIsoDate('1949'), '1949-01-01T00:00:00Z');
  assert.equal(toIsoDate('March 1997'), '1997-03-01T00:00:00Z');
  assert.equal(toIsoDate('First published in 1970'), '1970-01-01T00:00:00Z');
  assert.equal(toIsoDate('onzin'), null);
  assert.equal(toIsoDate(null), null);
});

test('isbn-10 wordt omgezet naar isbn-13', () => {
  assert.equal(isbn10To13('0451524934'), '9780451524935');
  assert.equal(normaliseIsbn13(['geen', '0-451-52493-4']), '9780451524935');
  assert.equal(normaliseIsbn13(['9780241677377']), '9780241677377');
  assert.equal(normaliseIsbn13([]), null);
});

test('catalogusruis komt niet door als genre', () => {
  const genres = cleanGenres([
    'Fiction',
    'Open Library Staff Picks',
    'Accessible book',
    'Protected DAISY',
    'English',
    "Children's stories, English",
    'nyt:bestseller=2011-01-01',
    'Fiction',
    '1984',
  ]);

  assert.deepEqual(genres, ['Fiction', "Children's stories"]);
});
