/**
 * Input normalization for deterministic pipeline.
 * Same input string → same normalized string.
 */
const NUMBER_WORDS = {
  zero: '0', one: '1', two: '2', three: '3', four: '4', five: '5',
  six: '6', seven: '7', eight: '8', nine: '9', ten: '10',
};

function normalizeInput(query) {
  if (query == null || typeof query !== 'string') return '';
  let s = query
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[^\w\s.,?\-']/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const words = s.split(' ');
  const normalized = words.map((w) => {
    const lower = w.toLowerCase();
    return NUMBER_WORDS[lower] !== undefined ? NUMBER_WORDS[lower] : w;
  });
  return normalized.join(' ');
}

module.exports = { normalizeInput };
