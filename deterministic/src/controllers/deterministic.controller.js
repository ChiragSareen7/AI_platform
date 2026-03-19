const pipelineService = require('../services/pipeline.service');
const testService = require('../services/test.service');
const fs = require('fs').promises;
const path = require('path');

const LOGS_FILE = path.join(process.cwd(), 'store', 'logs.json');

async function ensureStore() {
  const storeDir = path.join(process.cwd(), 'store');
  await fs.mkdir(storeDir, { recursive: true });
  try {
    await fs.access(LOGS_FILE);
  } catch {
    await fs.writeFile(LOGS_FILE, '[]', 'utf8');
  }
}

async function appendLog(entry) {
  await ensureStore();
  const logs = JSON.parse(await fs.readFile(LOGS_FILE, 'utf8').catch(() => '[]'));
  logs.push(entry);
  await fs.writeFile(LOGS_FILE, JSON.stringify(logs, null, 2), 'utf8');
}

async function deterministicQuery(req, res) {
  const query = req.body?.query;
  if (!query || typeof query !== 'string') {
    return res.status(400).json({ error: 'Missing or invalid "query" in body' });
  }
  const runDeterminismCheck = req.body?.runDeterminismCheck === true;
  let result;
  try {
    result = await pipelineService.runPipeline(query);
  } catch (err) {
    return res.status(500).json({
      answer: 'Pipeline error.',
      confidence: 0,
      source: '',
      hallucinationScore: 1,
      similarityScore: 0,
      cached: false,
      deterministicCheck: null,
      error: err.message,
    });
  }
  let deterministicCheck = null;
  if (runDeterminismCheck) {
    const testResult = await testService.runSameQueryMultipleTimes(
      pipelineService.runPipeline,
      query,
      3
    );
    deterministicCheck = {
      isDeterministic: testResult.deterministic,
      similarity: testResult.avgSimilarity,
    };
    result.deterministicCheck = deterministicCheck;
  }
  const logEntry = {
    query,
    normalizedQuery: result.normalizedQuery,
    context: result.contextChunks?.length ?? 0,
    response: result.answer,
    hallucinationScore: result.hallucinationScore,
    similarityScore: result.similarityScore,
    deterministic: deterministicCheck?.isDeterministic ?? null,
    cached: result.cached,
    timestamp: new Date().toISOString(),
  };
  await appendLog(logEntry);
  return res.json({
    answer: result.answer,
    confidence: result.confidence,
    source: result.source,
    hallucinationScore: result.hallucinationScore,
    similarityScore: result.similarityScore,
    cached: result.cached,
    contextChunks: result.contextChunks,
    similarityScores: result.similarityScores,
    category: result.category,
    deterministicCheck: result.deterministicCheck || null,
  });
}

module.exports = { deterministicQuery };
