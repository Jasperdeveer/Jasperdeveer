// Losse antwoorden worden op de edge gecached via de cf.cacheTtl-optie in
// lib/http.js. KV is voor samengestelde data die duurder is om opnieuw te
// bouwen: auteur-indexen en Hardcover-verrijking.

const KV_VERSION = 'v1';

export async function kvGet(env, key) {
  if (!env?.METADATA) {
    return null;
  }

  try {
    return await env.METADATA.get(`${KV_VERSION}:${key}`, 'json');
  } catch {
    return null;
  }
}

export async function kvPut(env, key, value, ttlSeconds) {
  if (!env?.METADATA) {
    return false;
  }

  try {
    // KV eist minimaal 60 seconden TTL.
    await env.METADATA.put(`${KV_VERSION}:${key}`, JSON.stringify(value), {
      expirationTtl: Math.max(60, ttlSeconds),
    });

    return true;
  } catch {
    return false;
  }
}
