/**
 * Evaluates query + response + context to produce quality scores.
 * relevanceScore: keyword overlap with query
 * accuracyScore: response content found in context
 * hallucinationScore: content not found in context (higher = more hallucination)
 * toxicityScore: bad words list
 * qualityScore: composite
 */

function normalize(text) {
  if (!text || typeof text !== 'string') return '';
  return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

function tokenize(str) {
  const n = normalize(str);
  if (!n) return [];
  return n.split(/\s+/).filter(Boolean);
}

function relevanceScore(query, response) {
  const qWords = new Set(tokenize(query));
  const rWords = tokenize(response);
  if (qWords.size === 0) return 1;
  let match = 0;
  for (const w of rWords) {
    if (qWords.has(w)) match++;
  }
  return Math.min(1, (match / qWords.size) * 1.2);
}

function accuracyScore(response, context) {
  if (!context || context.length < 10) return 0.5;
  const ctx = normalize(context);
  const resp = normalize(response);
  const respWords = tokenize(resp).filter(w => w.length > 2);
  if (respWords.length === 0) return 1;
  let found = 0;
  for (const w of respWords) {
    if (ctx.includes(w)) found++;
  }
  return found / respWords.length;
}

function hallucinationScore(response, context) {
  if (!context || context.length < 10) return 0.2;
  const ctx = normalize(context);
  const respSentences = normalize(response).split(/[.!?]+/).filter(Boolean);
  if (respSentences.length === 0) return 0;
  let notFound = 0;
  for (const s of respSentences) {
    const trimmed = s.trim();
    if (trimmed.length < 5) continue;
    const keyWords = tokenize(trimmed).filter(w => w.length > 3).slice(0, 5);
    const inContext = keyWords.some(w => ctx.includes(w));
    if (!inContext) notFound++;
  }
  return Math.min(1, notFound / Math.max(1, respSentences.length));
}

const BAD_WORDS = new Set([
  'hate', 'violence', 'kill', 'hurt', 'abuse', 'toxic', 'stupid', 'idiot', 'damn',
]);

function toxicityScore(response) {
  const words = new Set(tokenize(response));
  let count = 0;
  for (const w of words) {
    if (BAD_WORDS.has(w)) count++;
  }
  if (count === 0) return 0;
  return Math.min(1, count * 0.25);
}

function qualityScore(scores) {
  const { relevanceScore: r, accuracyScore: a, hallucinationScore: h, toxicityScore: t } = scores;
  const hallPenalty = 1 - h;
  const toxPenalty = 1 - t;
  return (r * 0.25 + a * 0.35 + hallPenalty * 0.25 + toxPenalty * 0.15);
}

function evaluate(query, response, context = '') {
  const rel = relevanceScore(query, response);
  const acc = accuracyScore(response, context);
  const hall = hallucinationScore(response, context);
  const tox = toxicityScore(response);

  const scores = {
    relevanceScore: rel,
    accuracyScore: acc,
    hallucinationScore: hall,
    toxicityScore: tox,
  };
  scores.qualityScore = qualityScore(scores);
  return scores;
}

module.exports = {
  evaluate,
  relevanceScore,
  accuracyScore,
  hallucinationScore,
  toxicityScore,
  qualityScore,
};
