// Open Library, Hardcover en Google Books leveren beschrijvingen in drie
// verschillende vormen en met wisselende rommel eromheen. Hier wordt dat
// gelijkgetrokken tot iets dat in Readarr en Shelfarr leesbaar is.

const HTML_TAG = /<[^>]*>/g;
const ENTITIES = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#39;': "'",
  '&apos;': "'",
  '&nbsp;': ' ',
};

export function stripHtml(value) {
  if (typeof value !== 'string') {
    return '';
  }

  return value
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(HTML_TAG, '')
    .replace(/&[a-z#0-9]+;/gi, (entity) => ENTITIES[entity.toLowerCase()] ?? entity);
}

export function cleanSpaces(value) {
  if (typeof value !== 'string') {
    return '';
  }

  return value.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
}

/**
 * Open Library geeft beschrijvingen soms als string en soms als
 * { type: '/type/text', value: '...' }. Ook staat er vaak een
 * "([source][1])"-voetnoot onderaan die niets toevoegt.
 */
export function cleanDescription(value) {
  const raw = typeof value === 'object' && value !== null ? value.value : value;
  const text = cleanSpaces(stripHtml(raw));

  if (!text) {
    return '';
  }

  // Volgorde telt: eerst de linkdefinities onderaan weg, pas daarna de
  // "([source][1])"-verwijzing - anders staat die niet meer aan het eind.
  return text
    .replace(/\n*-{3,}\n*\[source\][\s\S]*$/i, '')
    .replace(/^\s*\[\d+\]:\s*https?:\/\/\S+\s*$/gim, '')
    .replace(/\n*\(\[source\]\[\d+\]\)\s*$/i, '')
    .trim();
}

/** Van meerdere bronnen wint de langste zinnige beschrijving. */
export function bestDescription(...candidates) {
  return candidates
    .map(cleanDescription)
    .filter((text) => text.length >= 20)
    .sort((a, b) => b.length - a.length)[0] ?? '';
}

/** Eerste niet-lege waarde. */
export function firstOf(...candidates) {
  return candidates.find((value) => value !== undefined && value !== null && value !== '') ?? null;
}

// Open Library's subjects zijn een mengbak van echte genres, catalogusvlaggen
// en collectienamen. Zonder filter komt Readarr binnen met genres als
// "Protected DAISY" en "Open Library Staff Picks".
const SUBJECT_NOISE = [
  /^open library/i,
  /^accessible book$/i,
  /^protected daisy$/i,
  /^in library$/i,
  /^overdrive/i,
  /^large type books?$/i,
  /^reading level/i,
  /^lending library/i,
  /^internet archive/i,
  /^popular print disabled/i,
  /^nyt:/i,
  /^new york times bestseller/i,
  /^textbooks?$/i,
];

// Talen worden als subject opgevoerd, maar zijn geen genre.
const LANGUAGE_SUBJECTS = new Set([
  'english', 'dutch', 'german', 'french', 'spanish', 'italian', 'russian',
  'swedish', 'danish', 'norwegian', 'portuguese', 'japanese', 'chinese', 'latin',
]);

/** Onderwerpen van Open Library bevatten veel ruis; hou het bruikbaar. */
export function cleanGenres(subjects, limit = 20) {
  if (!Array.isArray(subjects)) {
    return [];
  }

  const seen = new Set();
  const genres = [];

  for (const subject of subjects) {
    if (typeof subject !== 'string') {
      continue;
    }

    // "Children's stories, English" -> "Children's stories"
    const value = cleanSpaces(subject).replace(
      /,\s*(English|Dutch|German|French|Spanish|Italian|Russian|Japanese|Chinese|Latin)$/i,
      '',
    );
    const key = value.toLowerCase();

    if (
      !value ||
      value.length > 60 ||
      seen.has(key) ||
      /^\d+$/.test(value) ||
      value.includes(':') ||
      LANGUAGE_SUBJECTS.has(key) ||
      SUBJECT_NOISE.some((pattern) => pattern.test(value))
    ) {
      continue;
    }

    seen.add(key);
    genres.push(value);

    if (genres.length >= limit) {
      break;
    }
  }

  return genres;
}

/** Readarr verwacht ISO-datums; Open Library levert van alles. */
export function toIsoDate(value) {
  if (!value) {
    return null;
  }

  if (typeof value === 'number') {
    return Number.isInteger(value) && value > 0 && value < 3000
      ? `${String(value).padStart(4, '0')}-01-01T00:00:00Z`
      : null;
  }

  if (typeof value !== 'string') {
    return null;
  }

  const text = value.trim();
  const yearOnly = text.match(/^(\d{4})$/);

  if (yearOnly) {
    return `${yearOnly[1]}-01-01T00:00:00Z`;
  }

  const parsed = Date.parse(text);

  if (Number.isNaN(parsed)) {
    // "1997" verstopt in "First published in 1997" of "March 1997".
    const year = text.match(/\b(1[0-9]{3}|20[0-9]{2})\b/);

    return year ? `${year[1]}-01-01T00:00:00Z` : null;
  }

  return new Date(parsed).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

/** ISBN-10 -> ISBN-13, zodat edities zonder ISBN-13 er toch een krijgen. */
export function isbn10To13(isbn10) {
  if (typeof isbn10 !== 'string') {
    return null;
  }

  const digits = isbn10.replace(/[^0-9Xx]/g, '');

  if (digits.length !== 10) {
    return null;
  }

  const body = `978${digits.slice(0, 9)}`;
  let sum = 0;

  for (let i = 0; i < 12; i += 1) {
    sum += Number(body[i]) * (i % 2 === 0 ? 1 : 3);
  }

  return `${body}${(10 - (sum % 10)) % 10}`;
}

export function normaliseIsbn13(candidates) {
  for (const candidate of [].concat(candidates ?? [])) {
    if (typeof candidate !== 'string') {
      continue;
    }

    const digits = candidate.replace(/[^0-9Xx]/g, '');

    if (digits.length === 13) {
      return digits;
    }

    const converted = isbn10To13(digits);

    if (converted) {
      return converted;
    }
  }

  return null;
}
