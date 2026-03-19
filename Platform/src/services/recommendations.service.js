/**
 * Generates actionable recommendations to improve agent quality and determinism
 * based on actual metrics vs preferences and prompt performance.
 */

function getRecommendations(metrics, comparison, preferences, promptPerformance = {}) {
  const recs = [];
  const c = comparison || {};
  const m = metrics || {};
  const sys = m.system || {};
  const quality = m.aiQuality || {};
  const prefs = preferences || {};

  const latency = sys.latency ?? 0;
  const tokens = sys.tokenUsage?.total ?? 0;
  const cost = sys.costPerRequest ?? 0;
  const accuracy = quality.accuracyScore ?? 0;
  const hallucination = quality.hallucinationScore ?? 0;
  const relevance = quality.relevanceScore ?? 0;

  const maxLatency = prefs.maxLatency ?? 2000;
  const maxTokens = prefs.maxTokens ?? 800;
  const minAccuracy = prefs.minAccuracy ?? 0.7;
  const maxHallucination = prefs.maxHallucination ?? 0.3;
  const temp = prefs.temperature ?? 0.7;

  if (c.latencyStatus === 'bad' || latency > maxLatency) {
    recs.push({
      id: 'latency',
      title: 'Reduce latency',
      action: 'Lower max tokens (e.g. 400–500) and use the "Concise" response type so the agent returns shorter answers faster.',
      priority: 'high',
    });
  }

  if (c.accuracyStatus === 'bad' || accuracy < minAccuracy) {
    recs.push({
      id: 'accuracy',
      title: 'Improve accuracy',
      action: 'Switch to prompt v2 (more accurate) or v3 (strict RAG-only) in Control Center. Ensure your RAG documents are up to date.',
      priority: 'high',
    });
  }

  if (c.hallucinationStatus === 'bad' || hallucination > maxHallucination) {
    recs.push({
      id: 'hallucination',
      title: 'Reduce hallucination',
      action: 'Use prompt v3 (strict RAG) and lower temperature (e.g. 0.2–0.3) for more deterministic, document-grounded answers.',
      priority: 'high',
    });
  }

  if (temp > 0.5) {
    recs.push({
      id: 'determinism',
      title: 'More deterministic outputs',
      action: `Lower temperature from ${temp} to 0.2–0.4 in Control Center. Lower temperature reduces randomness and makes responses more consistent.`,
      priority: 'medium',
    });
  }

  if (c.tokenStatus === 'bad' || tokens > maxTokens) {
    recs.push({
      id: 'tokens',
      title: 'Stay within token budget',
      action: 'Reduce max tokens in Control Center or choose "Concise" response type.',
      priority: 'medium',
    });
  }

  if (relevance < 0.5 && recs.every(r => r.id !== 'accuracy')) {
    recs.push({
      id: 'relevance',
      title: 'Improve relevance',
      action: 'Rephrase queries to match document wording, or use prompt v2/v3 to force grounding in retrieved context.',
      priority: 'medium',
    });
  }

  const perfEntries = Object.entries(promptPerformance).filter(([, p]) => p && p.usageCount > 0);
  if (perfEntries.length >= 2) {
    const best = perfEntries.reduce((a, b) => (a[1].avgHallucination <= b[1].avgHallucination ? a : b));
    const worst = perfEntries.reduce((a, b) => (a[1].avgHallucination >= b[1].avgHallucination ? a : b));
    if (best[0] !== worst[0] && best[1].avgHallucination < worst[1].avgHallucination - 0.05) {
      recs.push({
        id: 'prompt_choice',
        title: 'Use better-performing prompt',
        action: `Prompt "${best[0]}" has lower average hallucination (${(best[1].avgHallucination * 100).toFixed(1)}%) than "${worst[0]}". Consider defaulting to "${best[0]}" for more reliable answers.`,
        priority: 'low',
      });
    }
  }

  return recs.sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.priority] ?? 1) - (order[b.priority] ?? 1);
  });
}

module.exports = {
  getRecommendations,
};
