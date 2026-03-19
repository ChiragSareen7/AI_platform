/**
 * Rule-based query classification. NO ML, NO randomness.
 * Categories: hiring | product | policy | general
 */
const KEYWORDS = {
  hiring: ['job', 'jobs', 'internship', 'intern', 'hire', 'hiring', 'career', 'recruit', 'apply', 'application', 'candidate', 'position', 'vacancy', 'responsibilities', 'qualifications'],
  product: ['product', 'products', 'feature', 'features', 'platform', 'tool', 'solution', 'controlhub', 'nexora', 'deploy', 'api', 'integration'],
  policy: ['policy', 'policies', 'data', 'compliance', 'security', 'privacy', 'ownership', 'client', 'customer', 'sla', 'terms'],
  general: [],
};

function getCategory(query) {
  if (!query || typeof query !== 'string') return 'general';
  const q = query.toLowerCase().trim();
  const words = q.split(/\s+/);
  for (const [category, keywords] of Object.entries(KEYWORDS)) {
    if (category === 'general') continue;
    const found = keywords.some((kw) => words.some((w) => w.includes(kw) || kw.includes(w)));
    if (found) return category;
  }
  return 'general';
}

module.exports = { getCategory, KEYWORDS };
