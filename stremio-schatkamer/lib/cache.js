'use strict';

// Simple in-memory LRU-style cache to avoid hammering Schatkamer with Puppeteer requests
const store = new Map();
const TTL = 10 * 60 * 1000; // 10 minutes

function get(key) {
  const entry = store.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > TTL) {
    store.delete(key);
    return null;
  }
  return entry.value;
}

function set(key, value) {
  // Evict oldest entries if cache grows too large
  if (store.size > 500) {
    const oldest = store.keys().next().value;
    store.delete(oldest);
  }
  store.set(key, { value, ts: Date.now() });
}

module.exports = { get, set };
