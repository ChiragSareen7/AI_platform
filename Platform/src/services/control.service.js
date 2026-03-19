const config = require('../config/defaultConfig');

/**
 * Adjusts config and prompt version based on metrics and user preferences.
 * Returns { newConfig, newPromptVersion }.
 */
async function adjustConfig(metrics, currentConfig, currentPromptVersion, preferences = {}) {
  const quality = metrics?.aiQuality || {};
  const system = metrics?.system || {};
  const stability = metrics?.stability || {};
  const hallucinationScore = quality.hallucinationScore ?? 0;
  const accuracyScore = quality.accuracyScore ?? 0;
  const latency = system.latency ?? 0;
  const tokenUsage = system.tokenUsage?.total ?? system.tokenUsage ?? 0;
  const behaviorStability = stability.behaviorStability ?? 1;

  const maxLatency = preferences.maxLatency ?? 2000;
  const maxTokens = preferences.maxTokens ?? 800;
  const minAccuracy = preferences.minAccuracy ?? 0.7;
  const maxHallucination = preferences.maxHallucination ?? 0.3;
  const responseType = preferences.responseType ?? 'balanced';
  const userTemperature = preferences.temperature ?? config.model.defaultTemperature;

  let newPromptVersion = currentPromptVersion;
  const newConfig = { ...currentConfig };

  newConfig.temperature = userTemperature;

  if (responseType === 'concise') {
    newPromptVersion = 'v1';
    newConfig.maxTokens = Math.min(newConfig.maxTokens ?? maxTokens, 400);
    console.log('[Control] responseType=concise -> v1, lower maxTokens');
  } else if (responseType === 'detailed') {
    newConfig.maxTokens = Math.min(config.model.maxMaxTokens, (newConfig.maxTokens ?? maxTokens) + 200);
    if (newPromptVersion === 'v1') newPromptVersion = 'v2';
    console.log('[Control] responseType=detailed -> more tokens');
  } else if (responseType === 'strict') {
    newPromptVersion = 'v3';
    console.log('[Control] responseType=strict -> v3 (RAG only)');
  }

  if (hallucinationScore > maxHallucination) {
    newPromptVersion = 'v3';
    console.log('[Control] Hallucination above preference -> v3 (strict RAG)');
  }

  if (accuracyScore < minAccuracy && newPromptVersion !== 'v3') {
    newPromptVersion = 'v2';
    console.log('[Control] Accuracy below preference -> v2');
  }

  if (latency > maxLatency) {
    newConfig.maxTokens = Math.max(
      config.model.minMaxTokens,
      (newConfig.maxTokens ?? maxTokens) - 100
    );
    if (newPromptVersion !== 'v3') newPromptVersion = 'v1';
    console.log('[Control] Latency above preference -> reduce maxTokens, shorter prompt');
  }

  if (tokenUsage > maxTokens) {
    newConfig.maxTokens = Math.max(
      config.model.minMaxTokens,
      (newConfig.maxTokens ?? maxTokens) - 50
    );
    console.log('[Control] Token usage above preference -> reduce maxTokens');
  }

  if (behaviorStability < 0.7) {
    newConfig.temperature = Math.max(
      config.model.minTemperature,
      (newConfig.temperature ?? userTemperature) - 0.1
    );
    console.log('[Control] Low behavior stability -> reduce temperature');
  }

  return {
    newConfig,
    newPromptVersion,
  };
}

async function getInitialPromptVersion(preferences = {}) {
  const responseType = preferences.responseType ?? 'balanced';
  if (responseType === 'concise') return 'v1';
  if (responseType === 'strict') return 'v3';
  return 'v1';
}

module.exports = {
  adjustConfig,
  getInitialPromptVersion,
};
