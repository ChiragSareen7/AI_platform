const path = require('path');
const fs = require('fs').promises;

const STORE_DIR = path.join(process.cwd(), 'store');
const PREFERENCES_FILE = path.join(STORE_DIR, 'preferences.json');

const DEFAULT_PREFERENCES = {
  maxLatency: 2000,
  maxTokens: 800,
  maxCost: 0.05,
  minAccuracy: 0.7,
  maxHallucination: 0.3,
  minRelevance: 0.5,
  minConfidence: 0.5,
  responseType: 'balanced',
  temperature: 0.7,
};

const RESPONSE_TYPES = ['concise', 'detailed', 'strict', 'balanced'];

async function ensureStore() {
  await fs.mkdir(STORE_DIR, { recursive: true });
}

async function readPreferences() {
  try {
    const data = await fs.readFile(PREFERENCES_FILE, 'utf8');
    const parsed = JSON.parse(data);
    return { ...DEFAULT_PREFERENCES, ...parsed };
  } catch (err) {
    if (err.code === 'ENOENT') return { ...DEFAULT_PREFERENCES };
    throw err;
  }
}

async function writePreferences(prefs) {
  await ensureStore();
  const merged = { ...DEFAULT_PREFERENCES, ...prefs };
  if (RESPONSE_TYPES.includes(merged.responseType)) {
    // keep as-is
  } else {
    merged.responseType = 'balanced';
  }
  await fs.writeFile(PREFERENCES_FILE, JSON.stringify(merged, null, 2), 'utf8');
  return merged;
}

function getDefaults() {
  return { ...DEFAULT_PREFERENCES };
}

module.exports = {
  readPreferences,
  writePreferences,
  getDefaults,
  DEFAULT_PREFERENCES,
  RESPONSE_TYPES,
};
