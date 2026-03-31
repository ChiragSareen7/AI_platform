/**
 * Hallucination control: compare answer sentences to context.
 * If hallucinationScore > 0 → reject and return safe message.
 */
const { calculateSimilarity } = require('../utils/similarity');

const MIN_SIMILARITY = 0.10;
const REJECT_MESSAGE = 'Answer could not be verified from documents.';

function splitIntoSentences(text) {
  if (!text || typeof text !== 'string') return [];
  return text
    .replace(/\n/g, ' ')
    .split(/[.!?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 10);
}

function validateAnswer(answerText, contextChunks) {
  const chunkTexts = (contextChunks || []).map((c) =>
    (typeof c === 'string' ? c : c.content || '').trim()
  );
  const fullContext = chunkTexts.join(' ');
  if (!fullContext.trim()) {
    return {
      valid: false,
      hallucinationScore: 1,
      similarityScore: 0,
      answer: REJECT_MESSAGE,
      confidence: 0,
      source: '',
    };
  }
  const sentences = splitIntoSentences(answerText);
  if (sentences.length === 0) {
    return {
      valid: true,
      hallucinationScore: 0,
      similarityScore: 1,
      answer: answerText,
      confidence: 1,
      source: '',
    };
  }
  let unsupported = 0;
  const sentenceSupport = [];
  for (const sent of sentences) {
    // Compare against each chunk AND the full joined context;
    // take the best score so short chunks don't penalise unfairly.
    let best = calculateSimilarity(sent, fullContext);
    for (const ct of chunkTexts) {
      const sim = calculateSimilarity(sent, ct);
      if (sim > best) best = sim;
    }
    sentenceSupport.push({ sentence: sent, bestSimilarity: best });
    if (best < MIN_SIMILARITY) unsupported++;
  }
  const hallucinationScore = unsupported / sentences.length;
  const similarityScore = 1 - hallucinationScore;
  const valid = hallucinationScore <= 0;
  const validationScore = sentenceSupport.length
    ? sentenceSupport.reduce((acc, s) => acc + s.bestSimilarity, 0) / sentenceSupport.length
    : 0;
  return {
    valid,
    hallucinationScore,
    similarityScore,
    validationScore,
    sentenceSupport,
    answer: valid ? answerText : REJECT_MESSAGE,
    confidence: valid ? 1 : 0,
    source: '',
  };
}

/**
 * Parse LLM JSON output; fix if malformed.
 */
function parseAndValidateLlmOutput(rawContent, contextChunks) {
  let answer = '';
  let confidence = 0;
  let source = '';
  try {
    const stripped = rawContent.replace(/```json\s*/gi, '').replace(/```\s*/g, '').trim();
    const firstBrace = stripped.indexOf('{');
    const lastBrace = stripped.lastIndexOf('}');
    if (firstBrace === -1 || lastBrace === -1) {
      return validateAnswer(rawContent, contextChunks);
    }
    const jsonStr = stripped.slice(firstBrace, lastBrace + 1);
    const parsed = JSON.parse(jsonStr);
    answer = parsed.answer != null ? String(parsed.answer) : '';
    confidence = typeof parsed.confidence === 'number' ? Math.max(0, Math.min(1, parsed.confidence)) : 0;
    source = parsed.source != null ? String(parsed.source) : '';
  } catch (_) {
    answer = rawContent;
  }
  const validated = validateAnswer(answer, contextChunks);
  return {
    ...validated,
    confidence: validated.valid ? confidence : 0,
    source: source || validated.source,
  };
}

module.exports = {
  validateAnswer,
  parseAndValidateLlmOutput,
  REJECT_MESSAGE,
};
