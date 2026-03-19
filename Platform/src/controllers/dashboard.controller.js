const storageService = require('../services/storage.service');
const promptService = require('../services/prompt.service');
const preferencesService = require('../services/preferences.service');
const recommendationsService = require('../services/recommendations.service');

async function getLogsSummary(req, res) {
  try {
    const limit = Math.min(parseInt(req.query.limit, 10) || 50, 100);
    const logs = await storageService.getLogs(limit);
    const summary = logs.map((log) => ({
      query: log.query,
      finalAnswer: log.finalAnswer ? String(log.finalAnswer).slice(0, 300) : '',
      metrics: log.metrics,
      comparison: log.comparison,
      promptVersion: log.promptVersion,
      config: log.config,
      timestamp: log.timestamp,
      attemptCount: (log.attempts || []).length,
    }));
    return res.json({ logs: summary.reverse(), total: summary.length });
  } catch (err) {
    console.error('[Dashboard] getLogsSummary error:', err);
    return res.status(500).json({ error: 'Failed to load logs summary' });
  }
}

async function getPromptPerformance(req, res) {
  try {
    const performance = await promptService.getPerformance();
    const versions = await promptService.getAllPrompts();
    return res.json({
      performance,
      versions: Object.keys(versions),
    });
  } catch (err) {
    console.error('[Dashboard] getPromptPerformance error:', err);
    return res.status(500).json({ error: 'Failed to load prompt performance' });
  }
}

async function getRecommendations(req, res) {
  try {
    const logs = await storageService.getLogs(1);
    const last = logs[logs.length - 1];
    const preferences = await preferencesService.readPreferences();
    const promptPerformance = await promptService.getPerformance();
    const recommendations = recommendationsService.getRecommendations(
      last?.metrics,
      last?.comparison,
      preferences,
      promptPerformance
    );
    return res.json({
      recommendations,
      lastRun: last ? { query: last.query, timestamp: last.timestamp } : null,
    });
  } catch (err) {
    console.error('[Dashboard] getRecommendations error:', err);
    return res.status(500).json({ error: 'Failed to load recommendations' });
  }
}

module.exports = {
  getLogsSummary,
  getPromptPerformance,
  getRecommendations,
};
