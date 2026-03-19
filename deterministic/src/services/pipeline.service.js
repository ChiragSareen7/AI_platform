/**
 * Full deterministic pipeline.
 */
const config = require('../../config');
const inputNormalizer = require('./inputNormalizer.service');
const queryClassifier = require('./queryClassifier.service');
const retrievalService = require('./retrieval.service');
const promptService = require('./prompt.service');
const llmService = require('./llm.service');
const validationService = require('./validation.service');
const cacheService = require('./cache.service');

const CONFIG_VERSION = config.version || '1.0';
const NO_CONTEXT_MESSAGE = 'No relevant data found.';
const CONFLICT_MESSAGE = 'Conflicting information found.';

async function runPipeline(query) {
  const normalizedQuery = inputNormalizer.normalizeInput(query);
  const category = queryClassifier.getCategory(normalizedQuery);
  let contextChunks = [];
  let similarityScores = [];
  try {
    const retrieved = await retrievalService.retrieve(normalizedQuery);
    contextChunks = retrieved.contextChunks || [];
    similarityScores = retrieved.similarityScores || [];
  } catch (err) {
    return {
      answer: NO_CONTEXT_MESSAGE,
      confidence: 0,
      source: '',
      contextChunks: [],
      similarityScores: [],
      hallucinationScore: 1,
      similarityScore: 0,
      cached: false,
      category,
      normalizedQuery,
      error: err.message,
    };
  }
  if (contextChunks.length === 0) {
    return {
      answer: NO_CONTEXT_MESSAGE,
      confidence: 0,
      source: '',
      contextChunks: [],
      similarityScores: [],
      hallucinationScore: 1,
      similarityScore: 0,
      cached: false,
      category,
      normalizedQuery,
    };
  }
  const contextIds = contextChunks.map((c) => (c.id || c.source || '') + '_' + (c.page ?? ''));
  const promptVersion = promptService.getPromptVersion();
  const cached = await cacheService.get(normalizedQuery, promptVersion, CONFIG_VERSION, contextIds);
  if (cached) {
    return {
      ...cached,
      cached: true,
      category,
      normalizedQuery,
    };
  }
  const prompt = promptService.buildPrompt(normalizedQuery, contextChunks);
  let rawContent;
  try {
    rawContent = await llmService.execute(prompt);
  } catch (err) {
    return {
      answer: 'LLM request failed.',
      confidence: 0,
      source: '',
      contextChunks,
      similarityScores,
      hallucinationScore: 1,
      similarityScore: 0,
      cached: false,
      category,
      normalizedQuery,
      error: err.message,
    };
  }
  const validated = validationService.parseAndValidateLlmOutput(rawContent, contextChunks);
  const result = {
    answer: validated.answer,
    confidence: validated.confidence,
    source: validated.source,
    contextChunks,
    similarityScores,
    hallucinationScore: validated.hallucinationScore,
    similarityScore: validated.similarityScore,
    cached: false,
    category,
    normalizedQuery,
  };
  await cacheService.set(normalizedQuery, promptVersion, CONFIG_VERSION, contextIds, result);
  return result;
}

module.exports = { runPipeline };
