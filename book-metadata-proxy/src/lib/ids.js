// Readarr's BookInfo-contract eist integer-ID's (int32) voor auteurs, werken en
// edities. Open Library gebruikt sleutels als "OL45804W". Het numerieke deel
// past ruim binnen int32 en is per soort uniek, dus de vertaling is stateless
// en volledig omkeerbaar - geen database of ID-registry nodig.

const MAX_INT32 = 2147483647;

export const OL_KIND = {
  work: 'W',
  edition: 'M',
  author: 'A',
};

/** "/works/OL45804W" | "OL45804W" -> "OL45804W" (null als het geen sleutel is) */
export function normaliseOlKey(key) {
  if (typeof key !== 'string') {
    return null;
  }

  const bare = key.trim().split('/').filter(Boolean).pop();

  return bare && /^OL\d+[WMA]$/.test(bare) ? bare : null;
}

/** "OL45804W" -> 45804. Geeft null bij onbruikbare of te grote sleutels. */
export function olKeyToId(key) {
  const bare = normaliseOlKey(key);

  if (!bare) {
    return null;
  }

  const id = Number(bare.slice(2, -1));

  return Number.isSafeInteger(id) && id > 0 && id <= MAX_INT32 ? id : null;
}

/** 45804 + 'work' -> "OL45804W" */
export function idToOlKey(id, kind) {
  const suffix = OL_KIND[kind];
  const numeric = Number(id);

  if (!suffix || !Number.isSafeInteger(numeric) || numeric <= 0 || numeric > MAX_INT32) {
    return null;
  }

  return `OL${numeric}${suffix}`;
}

/** Pad zoals Open Library het zelf teruggeeft: "/works/OL45804W" */
export function olPath(key) {
  const bare = normaliseOlKey(key);

  if (!bare) {
    return null;
  }

  const segment = { W: 'works', M: 'books', A: 'authors' }[bare.slice(-1)];

  return `/${segment}/${bare}`;
}

/**
 * Hardcover-serie-ID's zijn al integers. We houden ze in een eigen ruimte,
 * want Readarr bewaart serie-ID's los van boek- en auteur-ID's.
 */
export function seriesId(hardcoverSeriesId) {
  const id = Number(hardcoverSeriesId);

  return Number.isSafeInteger(id) && id > 0 && id <= MAX_INT32 ? id : null;
}
