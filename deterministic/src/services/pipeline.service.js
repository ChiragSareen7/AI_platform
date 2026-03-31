/**
 * Full deterministic pipeline.
 */
const config = require('../../config');
const queryUnderstandingService = require('./queryUnderstanding.service');
const retrievalService = require('./retrieval.service');
const promptService = require('./prompt.service');
const llmService = require('./llm.service');
const validationService = require('./validation.service');
const cacheService = require('./cache.service');

const CONFIG_VERSION = config.version || '1.0';
const NO_CONTEXT_MESSAGE = 'No relevant data found.';
const CONFLICT_MESSAGE = 'Conflicting information found.';

async function runPipeline(query) {
  const originalQuery = query;
  const understanding = await queryUnderstandingService.understandQueryWithAI(query);
  const normalizedQuery = understanding.normalized_query;
  const expandedQuery = understanding.expanded_query;
  const category = understanding.category;
  let contextChunks = [];
  let similarityScores = [];
  let retrievalMeta = null;
  try {
    const retrieved = await retrievalService.retrieve(expandedQuery || normalizedQuery, understanding);
    contextChunks = retrieved.contextChunks || [];
    similarityScores = retrieved.similarityScores || [];
    retrievalMeta = retrieved.retrievalMeta || null;
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
      queryUnderstanding: understanding,
      retrievalMeta,
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
      queryUnderstanding: understanding,
      retrievalMeta,
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
      queryUnderstanding: understanding,
      retrievalMeta,
    };
  }
  // Answer should be based on the original user query, while retrieval uses expanded query.
  const prompt = promptService.buildPrompt(originalQuery || expandedQuery || normalizedQuery, contextChunks);
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
      queryUnderstanding: understanding,
      retrievalMeta,
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
    validationScore: validated.validationScore,
    sentenceSupport: validated.sentenceSupport,
    cached: false,
    category,
    normalizedQuery,
    queryUnderstanding: understanding,
    retrievalMeta,
  };
  await cacheService.set(normalizedQuery, promptVersion, CONFIG_VERSION, contextIds, result);
  return result;
}

module.exports = { runPipeline };
