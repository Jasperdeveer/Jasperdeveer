// Deze tests bewaken het contract dat uit de broncode van Readarr komt
// (NzbDrone.Core/MetadataSource/BookInfo). Ze zijn de reden dat de rest van de
// code doet wat het doet - breek ze niet zonder die code er weer bij te pakken.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { authorStub, bookResource, seriesResource, workResource } from '../src/routes/bookinfo.js';
import { workFromSearchDoc } from '../src/core/enrich.js';

const doc = {
  key: '/works/OL45804W',
  title: 'Fantastic Mr Fox',
  author_key: ['OL9388A', 'OL34184A'],
  author_name: ['Iemand anders', 'Roald Dahl'],
  first_publish_year: 1970,
  cover_i: 6498519,
  isbn: ['0451524934'],
  publisher: ['Puffin'],
  number_of_pages_median: 96,
  language: ['eng'],
  subject: ['Fiction', 'Foxes'],
  ratings_count: 120,
  ratings_average: 4.2,
};

test('Readarr leest case-sensitive: sleutels moeten PascalCase zijn', () => {
  // System.Text.Json met PropertyNameCaseInsensitive = false accepteert alleen
  // exact deze namen; camelCase levert stil een leeg object op.
  const work = workResource(workFromSearchDoc(doc), { includeAuthors: true });

  assert.deepEqual(Object.keys(work).sort(), [
    'Authors', 'Books', 'ForeignId', 'Genres', 'RelatedWorks', 'ReleaseDate', 'Series', 'Title', 'Url',
  ]);

  assert.deepEqual(Object.keys(work.Books[0]).sort(), [
    'AverageRating', 'Asin', 'Contributors', 'Description', 'EditionInformation', 'ForeignId',
    'Format', 'ImageUrl', 'IsEbook', 'Isbn13', 'Language', 'NumPages', 'Publisher', 'RatingCount',
    'ReleaseDate', 'Title', 'Url',
  ].sort());

  assert.deepEqual(Object.keys(authorStub({ id: 1, name: 'X' })).sort(), [
    'AverageRating', 'Description', 'ForeignId', 'ImageUrl', 'Name', 'RatingCount', 'Series', 'Url', 'Works',
  ]);
});

test('ForeignId is een getal, niet een string', () => {
  // Readarr deserialiseert naar int; een string faalt hard.
  const work = workResource(workFromSearchDoc(doc));

  assert.equal(typeof work.ForeignId, 'number');
  assert.equal(typeof work.Books[0].ForeignId, 'number');
  assert.equal(typeof work.Books[0].Contributors[0].ForeignId, 'number');
});

test('de opgevraagde auteur staat vooraan, anders valt het boek weg', () => {
  // MapAuthor houdt alleen werken over waarvan GetAuthorId gelijk is aan de
  // opgevraagde auteur, en die kijkt naar Contributors[0].
  const work = workResource(workFromSearchDoc(doc, { preferredAuthorId: 34184 }));

  assert.equal(work.Books[0].Contributors[0].ForeignId, 34184);
  assert.equal(work.Books[0].Contributors[0].Role, 'Author');
});

test('elk werk heeft minstens één editie met een contributor', () => {
  // MapBulkBook doet .First() op Books en op Contributors; leeg = exception.
  const work = workResource(workFromSearchDoc(doc));

  assert.ok(work.Books.length > 0);
  assert.ok(work.Books.every((book) => book.Contributors.length > 0));
});

test('lijstvelden zijn nooit null', () => {
  // PollBook weigert een werk waarvan Books of Authors null is.
  const work = workResource(workFromSearchDoc({ key: '/works/OL1W', title: 'Kaal' }), { includeAuthors: true });

  for (const field of ['Genres', 'RelatedWorks', 'Books', 'Series', 'Authors']) {
    assert.ok(Array.isArray(work[field]), `${field} moet een array zijn`);
  }
});

test('serie-koppelingen hebben de vorm die MapSeriesLinks verwacht', () => {
  const series = seriesResource({
    id: 42,
    name: 'Discworld',
    links: [{ workId: 45804, position: '3', primary: true }],
  });

  assert.deepEqual(series, {
    ForeignId: 42,
    Title: 'Discworld',
    Description: '',
    LinkItems: [{ ForeignWorkId: 45804, PositionInSeries: '3', SeriesPosition: 3, Primary: true }],
  });
  // PositionInSeries is een string, SeriesPosition een int - dat is niet hetzelfde veld.
  assert.equal(typeof series.LinkItems[0].PositionInSeries, 'string');
  assert.equal(typeof series.LinkItems[0].SeriesPosition, 'number');
});

test('een editie zonder gegevens levert null op, niet undefined', () => {
  // undefined verdwijnt uit JSON.stringify; Readarr ziet dan een ontbrekend veld.
  const book = bookResource({ id: 1, title: 'X', contributors: [] });

  assert.equal(JSON.parse(JSON.stringify(book)).Isbn13, null);
  assert.equal(JSON.parse(JSON.stringify(book)).Publisher, null);
});
