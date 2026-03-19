/**
 * Deterministic RAG retrieval: call agent /retrieve, top_k=3, fixed.
 */
const config = require('../../config');

const RETRIEVE_URL = config.retrieval.agentRetrieveUrl;
const TOP_K = 3;

async function retrieve(query) {
  const res = await fetch(RETRIEVE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Retrieve failed: ${res.status} ${err}`);
  }
  const data = await res.json();
  const contextChunks = (data.contextChunks || []).slice(0, TOP_K);
  const similarityScores = (data.similarityScores || []).slice(0, TOP_K);
  return { contextChunks, similarityScores };
}

module.exports = { retrieve };
