/**
 * Cache: key = hash(normalizedQuery + prompt_version + config_version + context_ids).
 * Guarantees repeatability even if LLM fluctuates.
 */
const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');

const CACHE_DIR = path.join(process.cwd(), 'store', 'cache');
const inMemory = new Map();

function hashKey(str) {
  return crypto.createHash('sha256').update(str, 'utf8').digest('hex').slice(0, 32);
}

function buildKey(normalizedQuery, promptVersion, configVersion, contextIds) {
  const ids = Array.isArray(contextIds) ? contextIds.join(',') : String(contextIds || '');
  return [normalizedQuery, promptVersion, configVersion, ids].join('|');
}

async function get(normalizedQuery, promptVersion, configVersion, contextIds) {
  const key = hashKey(buildKey(normalizedQuery, promptVersion, configVersion, contextIds));
  if (inMemory.has(key)) return inMemory.get(key);
  try {
    await fs.mkdir(CACHE_DIR, { recursive: true });
    const f = path.join(CACHE_DIR, `${key}.json`);
    const data = await fs.readFile(f, 'utf8');
    const parsed = JSON.parse(data);
    inMemory.set(key, parsed);
    return parsed;
  } catch (_) {
    return null;
  }
}

async function set(normalizedQuery, promptVersion, configVersion, contextIds, value) {
  const key = hashKey(buildKey(normalizedQuery, promptVersion, configVersion, contextIds));
  inMemory.set(key, value);
  try {
    await fs.mkdir(CACHE_DIR, { recursive: true });
    const f = path.join(CACHE_DIR, `${key}.json`);
    await fs.writeFile(f, JSON.stringify(value), 'utf8');
  } catch (_) {}
  return value;
}

module.exports = { get, set, buildKey, hashKey };
