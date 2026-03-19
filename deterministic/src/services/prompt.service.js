/**
 * Strict prompt template — anti-hallucination, grounding only.
 */
const config = require('../../config');

const PROMPT_TEMPLATE = `You are an AI assistant for Nexora Systems.

STRICT RULES:
1. ONLY answer using the provided context.
2. DO NOT use external knowledge.
3. If the answer is not found in context, say: "Information not available in provided documents."
4. DO NOT guess or assume.
5. Cite the exact sentence from context that supports your answer.

Context:
{context}

Question:
{query}

Output Format (STRICT JSON only, no other text):
{
  "answer": "...",
  "confidence": number between 0 and 1,
  "source": "exact sentence from context"
}`;

function buildPrompt(query, contextChunks) {
  const context = (contextChunks || [])
    .map((c, i) => `[${i + 1}] ${typeof c === 'string' ? c : c.content || c}`)
    .join('\n\n');
  return PROMPT_TEMPLATE
    .replace('{context}', context || '(No context provided)')
    .replace('{query}', query || '');
}

function getPromptVersion() {
  return config.version || '1.0';
}

module.exports = { buildPrompt, getPromptVersion, PROMPT_TEMPLATE };
