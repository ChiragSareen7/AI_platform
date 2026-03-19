/**
 * Default configuration for the observability platform and agent calls.
 */

module.exports = {
  agent: {
    baseUrl: process.env.AGENT_URL || 'http://localhost:8000',
    chatPath: '/chat',
    timeoutMs: 30000,
  },
  evaluation: {
    qualityThreshold: 0.6,
    maxRetries: 3,
  },
  model: {
    defaultMaxTokens: 800,
    minMaxTokens: 100,
    maxMaxTokens: 2000,
    defaultTemperature: 0.3,
    minTemperature: 0,
    maxTemperature: 1,
  },
  costPer1kInput: 0.0001,
  costPer1kOutput: 0.0002,
};
