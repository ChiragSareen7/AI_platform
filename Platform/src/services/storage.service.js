const fs = require('fs').promises;
const path = require('path');

const STORE_DIR = path.join(process.cwd(), 'store');
const LOGS_FILE = path.join(STORE_DIR, 'logs.json');
const METRICS_FILE = path.join(STORE_DIR, 'metrics.json');
const PROMPTS_FILE = path.join(STORE_DIR, 'prompts.json');

async function ensureStore() {
  await fs.mkdir(STORE_DIR, { recursive: true });
}

async function readJson(filePath, defaultValue = null) {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return JSON.parse(data);
  } catch (err) {
    if (err.code === 'ENOENT') return defaultValue;
    throw err;
  }
}

async function writeJson(filePath, data) {
  await ensureStore();
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), 'utf8');
}

async function appendLog(entry) {
  const logs = await readJson(LOGS_FILE, []);
  logs.push({
    ...entry,
    timestamp: entry.timestamp || new Date().toISOString(),
  });
  await writeJson(LOGS_FILE, logs);
  return entry;
}

async function getLogs(limit = 100) {
  const logs = await readJson(LOGS_FILE, []);
  return logs.slice(-limit);
}

async function readMetrics() {
  return readJson(METRICS_FILE, {
    aggregated: {},
    byPrompt: {},
    lastUpdated: null,
  });
}

async function writeMetrics(metrics) {
  await writeJson(METRICS_FILE, {
    ...metrics,
    lastUpdated: new Date().toISOString(),
  });
}

async function updateAggregatedMetrics(update) {
  const current = await readMetrics();
  const aggregated = { ...(current.aggregated || {}), ...update };
  await writeMetrics({ ...current, aggregated });
  return aggregated;
}

async function readPrompts() {
  return readJson(PROMPTS_FILE, {
    versions: {},
    performance: {},
  });
}

async function writePrompts(data) {
  await writeJson(PROMPTS_FILE, data);
  return data;
}

async function updatePromptPerformance(version, stats) {
  const data = await readPrompts();
  const performance = data.performance || {};
  const existing = performance[version] || {
    avgLatency: 0,
    avgTokens: 0,
    avgAccuracy: 0,
    avgHallucination: 0,
    usageCount: 0,
  };
  const n = existing.usageCount + 1;
  performance[version] = {
    avgLatency: (existing.avgLatency * existing.usageCount + (stats.latency || 0)) / n,
    avgTokens: (existing.avgTokens * existing.usageCount + (stats.tokenUsage?.total || 0)) / n,
    avgAccuracy: (existing.avgAccuracy * existing.usageCount + (stats.accuracyScore ?? 0)) / n,
    avgHallucination: (existing.avgHallucination * existing.usageCount + (stats.hallucinationScore ?? 0)) / n,
    usageCount: n,
  };
  data.performance = performance;
  await writePrompts(data);
  return performance[version];
}

module.exports = {
  appendLog,
  getLogs,
  readMetrics,
  writeMetrics,
  updateAggregatedMetrics,
  readPrompts,
  writePrompts,
  updatePromptPerformance,
  LOGS_FILE,
  METRICS_FILE,
  PROMPTS_FILE,
};
