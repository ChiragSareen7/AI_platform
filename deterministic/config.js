/**
 * DETERMINISTIC CONFIG — DO NOT MODIFY AT RUNTIME.
 * Same config = same output.
 */
module.exports = {
  version: '1.0',
  llm: {
    temperature: 0,
    top_p: 1,
    seed: 42,
    max_tokens: 500,
  },
  retrieval: {
    top_k: 3,
    agentRetrieveUrl: process.env.AGENT_RETRIEVE_URL || 'http://localhost:8000/retrieve',
  },
  groq: {
    apiKey: process.env.GROQ_API_KEY || '',
    model: process.env.GROQ_MODEL || 'llama-3.3-70b-versatile',
    baseUrl: 'https://api.groq.com/openai/v1',
  },
  validation: {
    minSimilarityThreshold: 0.8,
    maxHallucinationScore: 0,
  },
  consistencyTest: {
    runCount: 3,
  },
};
