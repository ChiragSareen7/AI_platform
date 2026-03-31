/**
 * Production retrieval:
 * - query expansion aware
 * - hybrid scoring (vector + keyword)
 * - dynamic top-k
 * - score thresholding fallback
 * - rerank + compression
 */
const config = require('../../config');
const { calculateSimilarity } = require('../utils/similarity');

const RETRIEVE_URL = config.retrieval.agentRetrieveUrl;
const MIN_SCORE_THRESHOLD = 0.2;

function tokenize(s) {
  return String(s || '').toLowerCase().replace(/[^\w\s]/g, ' ').split(/\s+/).filter(Boolean);
}

function keywordScore(text, keywords) {
  const t = new Set(tokenize(text));
  if (!keywords || keywords.length === 0) return 0;
  let hit = 0;
  for (const k of keywords) {
    if (t.has(String(k).toLowerCase())) hit++;
  }
  return hit / Math.max(1, keywords.length);
}

function chooseDynamicK(queryUnderstanding) {
  const q = queryUnderstanding?.expanded_query || queryUnderstanding?.normalized_query || '';
  const words = tokenize(q);
  const confidence = queryUnderstanding?.confidence ?? 0.5;
  // specific query -> smaller k
  const specific = words.length >= 10 || confidence >= 0.8 || queryUnderstanding?.filters?.priority === 'high';
  return specific ? 2 : 5;
}

function compressContent(content, keywords) {
  const sentences = String(content || '')
    .split(/[.!?]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (!sentences.length) return String(content || '');
  const kset = new Set((keywords || []).map((k) => String(k).toLowerCase()));
  const picked = [];
  for (const s of sentences) {
    const tokens = tokenize(s);
    const hasSignal = tokens.some((t) => kset.has(t));
    if (hasSignal) picked.push(s);
    if (picked.length >= 4) break;
  }
  return (picked.length ? picked : sentences.slice(0, 3)).join('. ') + '.';
}

function dedupeAndCompress(chunks, keywords) {
  const out = [];
  for (const c of chunks) {
    const content = c.content || '';
    let duplicate = false;
    for (const e of out) {
      if (calculateSimilarity(content, e.content) > 0.92) {
        duplicate = true;
        break;
      }
    }
    if (!duplicate) {
      out.push({
        ...c,
        content: compressContent(content, keywords),
      });
    }
  }
  return out;
}

async function retrieveOnce(query) {
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
  return {
    contextChunks: data.contextChunks || [],
    similarityScores: data.similarityScores || [],
  };
}

async function retrieve(query, queryUnderstanding = null) {
  const dynamicK = chooseDynamicK(queryUnderstanding || {});
  const expanded = queryUnderstanding?.expanded_query || query;
  const keywords = queryUnderstanding?.keywords || [];

  const semantic = await retrieveOnce(expanded);
  // Run keyword-level vector searches so each key term contributes candidates.
  const keywordSets = [];
  for (const kw of keywords.slice(0, 6)) {
    try {
      // Keep deterministic ordering by iterating in stable keyword order.
      const r = await retrieveOnce(String(kw));
      keywordSets.push(r);
    } catch (_) {
      // Ignore individual keyword retrieval failures; semantic path still runs.
    }
  }

  // Merge by id/source-page, weighted score = 0.7 vector + 0.3 keyword score
  const merged = new Map();
  function addSet(set, vectorWeight) {
    for (let i = 0; i < set.contextChunks.length; i++) {
      const chunk = set.contextChunks[i];
      const vectorScore = Number(set.similarityScores[i] ?? 0);
      const key = chunk.id || `${chunk.source || 'unknown'}_${chunk.page ?? 0}`;
      const kw = keywordScore(chunk.content, keywords);
      const score = (vectorWeight * vectorScore) + ((1 - vectorWeight) * kw);
      const rerank = calculateSimilarity(expanded, chunk.content || '');
      const combined = (0.8 * score) + (0.2 * rerank);
      const existing = merged.get(key);
      if (!existing || combined > existing.finalScore) {
        merged.set(key, {
          ...chunk,
          vectorScore,
          keywordScore: kw,
          rerankScore: rerank,
          finalScore: combined,
        });
      }
    }
  }
  addSet(semantic, 0.7);
  for (const ks of keywordSets) addSet(ks, 0.6);

  let ranked = Array.from(merged.values()).sort((a, b) => {
    if (b.finalScore !== a.finalScore) return b.finalScore - a.finalScore;
    return String(a.id || '').localeCompare(String(b.id || ''));
  });

  // thresholding fallback: if weak top score, retry with normalized query only
  if (!ranked.length || Number(ranked[0].finalScore) < MIN_SCORE_THRESHOLD) {
    const fallback = await retrieveOnce(queryUnderstanding?.normalized_query || query);
    for (let i = 0; i < fallback.contextChunks.length; i++) {
      const chunk = fallback.contextChunks[i];
      ranked.push({
        ...chunk,
        vectorScore: Number(fallback.similarityScores[i] ?? 0),
        keywordScore: keywordScore(chunk.content, keywords),
        rerankScore: calculateSimilarity(expanded, chunk.content || ''),
        finalScore: Number(fallback.similarityScores[i] ?? 0),
      });
    }
    ranked = ranked.sort((a, b) => b.finalScore - a.finalScore);
  }

  const picked = dedupeAndCompress(ranked.slice(0, Math.max(dynamicK, 3)), keywords).slice(0, 3);
  const contextChunks = picked.map((c) => ({
    content: c.content,
    source: c.source,
    page: c.page,
    category: c.category,
    id: c.id,
  }));
  const similarityScores = picked.map((c) => Number(c.finalScore || 0));
  return {
    contextChunks,
    similarityScores,
    retrievalMeta: {
      dynamicK,
      threshold: MIN_SCORE_THRESHOLD,
      candidateCount: ranked.length,
      usedExpandedQuery: expanded,
    },
  };
}

module.exports = { retrieve };
