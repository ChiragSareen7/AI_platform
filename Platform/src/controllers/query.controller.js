const config = require('../config/defaultConfig');
const agentService = require('../services/agent.service');
const metricsService = require('../services/metrics.service');
const evaluationService = require('../services/evaluation.service');
const controlService = require('../services/control.service');
const promptService = require('../services/prompt.service');
const storageService = require('../services/storage.service');
const preferencesService = require('../services/preferences.service');
const comparisonService = require('../services/comparison.service');
const recommendationsService = require('../services/recommendations.service');
const { behaviorStability } = require('../utils/similarity');

const QUALITY_THRESHOLD = config.evaluation.qualityThreshold;
const MAX_RETRIES = config.evaluation.maxRetries;

async function runQuery(req, res) {
  const query = req.body?.query;
  if (!query || typeof query !== 'string') {
    return res.status(400).json({ error: 'Missing or invalid "query" in body' });
  }

  const preferences = await preferencesService.readPreferences();

  const attempts = [];
  let currentPromptVersion = await promptService.getPromptVersion('v1');
  let currentPromptVersionId = await controlService.getInitialPromptVersion(preferences);
  currentPromptVersion = await promptService.getPromptVersion(currentPromptVersionId);
  let currentConfig = {
    maxTokens: preferences.maxTokens ?? config.model.defaultMaxTokens,
    temperature: preferences.temperature ?? config.model.defaultTemperature,
    sessionId: 'platform',
  };
  let lastResult = null;
  let lastMetrics = null;
  let lastEvaluation = null;
  let errorOccurred = false;
  const allResponses = [];

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const result = await agentService.runAgentWithTracking(
        query,
        currentConfig,
        currentPromptVersionId,
        currentPromptVersion
      );
      lastResult = result;
      allResponses.push(result.response);

      const context = (result.sources || []).map(s => typeof s === 'string' ? s : s.content || JSON.stringify(s)).join('\n');
      const evaluation = evaluationService.evaluate(query, result.response, context);
      lastEvaluation = evaluation;

      const costPerRequest = metricsService.computeCost(result.tokenUsage || { input: 0, output: 0 });
      let metrics = metricsService.buildMetrics({
        latency: result.latency,
        tokenUsage: result.tokenUsage || { input: 0, output: 0, total: 0 },
        costPerRequest,
        hallucinationScore: evaluation.hallucinationScore,
        accuracyScore: evaluation.accuracyScore,
        relevanceScore: evaluation.relevanceScore,
        toxicityScore: evaluation.toxicityScore,
        retryRate: attempt / (attempt + 1),
        errorRate: 0,
        behaviorStability: attempt > 0 ? behaviorStability(allResponses) : 1,
      });
      lastMetrics = metrics;

      attempts.push({
        response: result.response,
        metrics,
        promptVersion: currentPromptVersionId,
        config: currentConfig,
        evaluation,
      });

      console.log('[Query] attempt', attempt + 1, 'qualityScore', evaluation.qualityScore.toFixed(3), 'latency', result.latency, 'prompt', currentPromptVersionId);

      await promptService.recordRun(currentPromptVersionId, {
        latency: result.latency,
        tokenUsage: result.tokenUsage,
        accuracyScore: evaluation.accuracyScore,
        hallucinationScore: evaluation.hallucinationScore,
      });

      if (evaluation.qualityScore >= QUALITY_THRESHOLD || attempt === MAX_RETRIES) {
        break;
      }

      const adjusted = await controlService.adjustConfig(metrics, currentConfig, currentPromptVersionId, preferences);
      const prevPrompt = currentPromptVersionId;
      currentConfig = adjusted.newConfig;
      currentPromptVersionId = adjusted.newPromptVersion;
      currentPromptVersion = await promptService.getPromptVersion(currentPromptVersionId);
      if (prevPrompt !== currentPromptVersionId) {
        console.log('[Query] prompt switch:', prevPrompt, '->', currentPromptVersionId);
      }
      console.log('[Query] config updated, retrying...');
    } catch (err) {
      errorOccurred = true;
      const msg =
        (err && typeof err.message === 'string' && err.message.trim()) ||
        (err && err.code && `${err.code}`) ||
        String(err);
      console.error('[Query] attempt', attempt + 1, 'error:', msg);
      lastMetrics = metricsService.buildMetrics({
        errorRate: 1,
        retryRate: attempt / (attempt + 1),
        behaviorStability: attempt > 0 ? behaviorStability(allResponses) : 0,
      });
      attempts.push({
        response: null,
        error: msg,
        metrics: lastMetrics,
        promptVersion: currentPromptVersionId,
        config: currentConfig,
      });
      if (attempt === MAX_RETRIES) break;
      const adjusted = await controlService.adjustConfig(lastMetrics, currentConfig, currentPromptVersionId, preferences);
      currentConfig = adjusted.newConfig;
      currentPromptVersionId = adjusted.newPromptVersion;
      currentPromptVersion = await promptService.getPromptVersion(currentPromptVersionId);
    }
  }

  const finalStability = allResponses.length > 1 ? behaviorStability(allResponses) : 1;
  if (lastMetrics) {
    lastMetrics = metricsService.mergeStability(
      lastMetrics,
      attempts.length - 1,
      errorOccurred,
      finalStability
    );
  }

  const comparison = comparisonService.compare(lastMetrics, preferences);
  const promptPerformance = await promptService.getPerformance();
  const recommendations = recommendationsService.getRecommendations(
    lastMetrics,
    comparison,
    preferences,
    promptPerformance
  );

  const finalAnswer = lastResult?.response ?? (attempts[attempts.length - 1]?.error || 'No response from agent.');

  const logEntry = {
    query,
    attempts,
    finalAnswer,
    metrics: lastMetrics,
    preferences,
    comparison,
    recommendations,
    promptVersion: currentPromptVersionId,
    config: currentConfig,
    timestamp: new Date().toISOString(),
  };
  await storageService.appendLog(logEntry);

  return res.json({
    final_answer: finalAnswer,
    metrics: lastMetrics,
    preferences,
    comparison,
    recommendations,
    config_used: currentConfig,
    prompt_version: currentPromptVersionId,
    attempts,
  });
}

module.exports = {
  runQuery,
};
