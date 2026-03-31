/**
 * Deterministic query understanding module for RAG.
 * Transforms raw query into structured retrieval-friendly JSON.
 */
const llmService = require('./llm.service');

const CATEGORIES = ['hiring', 'products', 'policies', 'security', 'general'];

const ABBREVIATIONS = {
  u: 'you',
  ur: 'your',
  pls: 'please',
  plz: 'please',
  dev: 'developer',
  devs: 'developers',
  hr: 'human resources',
  info: 'information',
  asap: 'as soon as possible',
  btw: 'by the way',
  w: 'with',
  wfh: 'work from home',
};

const STOPWORDS = new Set([
  'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'to', 'for', 'of', 'in', 'on',
  'at', 'by', 'with', 'as', 'and', 'or', 'but', 'if', 'then', 'than', 'that', 'this',
  'these', 'those', 'do', 'does', 'did', 'can', 'could', 'would', 'should', 'may',
  'might', 'will', 'shall', 'i', 'you', 'we', 'they', 'it', 'my', 'your', 'our',
  'their', 'me', 'us', 'them', 'what', 'how', 'when', 'where', 'why', 'who', 'whom',
]);

const CATEGORY_KEYWORDS = {
  hiring: ['hire', 'hiring', 'job', 'jobs', 'internship', 'intern', 'recruit', 'recruitment', 'candidate', 'interview', 'role', 'position'],
  products: ['product', 'products', 'platform', 'feature', 'features', 'build', 'building', 'tool', 'controlhub', 'acquire', 'acquired', 'acquisition', 'merger'],
  policies: ['policy', 'policies', 'rule', 'rules', 'guideline', 'compliance', 'privacy', 'terms', 'sla', 'ownership'],
  security: ['security', 'secure', 'authentication', 'authorization', 'breach', 'incident', 'risk', 'encryption', 'vulnerability'],
};

function cleanText(query) {
  if (!query || typeof query !== 'string') return '';
  return query
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[^\w\s?.!,:'-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function expandAbbreviations(text) {
  const words = text.split(' ');
  return words
    .map((w) => {
      const lower = w.toLowerCase();
      const stripped = lower.replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, '');
      const expanded = ABBREVIATIONS[stripped];
      if (!expanded) return w;
      return w.toLowerCase() === stripped ? expanded : expanded;
    })
    .join(' ');
}

function normalizeQuery(query) {
  const cleaned = cleanText(query);
  if (!cleaned) return '';
  let expanded = expandAbbreviations(cleaned);
  expanded = expanded.replace(/\s+/g, ' ').trim();
  // Deterministic grammar cleanups for common ambiguous forms.
  expanded = expanded
    .replace(/\bwhat all\b/gi, 'what')
    .replace(/\bcompaines\b/gi, 'companies')
    .replace(/\baquired\b/gi, 'acquired')
    .replace(/\bhirng\b/gi, 'hiring')
    .replace(/\bnerxora\b/gi, 'nexora');
  expanded = expanded.replace(/\bhow you\b/gi, 'how do you');
  const sentence = expanded.charAt(0).toUpperCase() + expanded.slice(1);
  return /[?.!]$/.test(sentence) ? sentence : `${sentence}?`;
}

function classifyCategory(text) {
  const q = text.toLowerCase();
  for (const category of ['hiring', 'products', 'policies', 'security']) {
    const words = CATEGORY_KEYWORDS[category];
    if (words.some((w) => q.includes(w))) return category;
  }
  return 'general';
}

function detectIntent(text) {
  const q = text.toLowerCase();
  if (/\b(compare|difference|vs|versus|better)\b/.test(q)) return 'comparison';
  if (/\b(fix|error|issue|problem|not working|fail|debug)\b/.test(q)) return 'troubleshooting';
  if (/\b(apply|submit|book|schedule|create|start)\b/.test(q)) return 'transactional';
  if (/\b(explore|overview|about|understand|learn)\b/.test(q)) return 'exploratory';
  return 'informational';
}

function extractKeywords(text, category) {
  const tokens = text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .filter((t) => !STOPWORDS.has(t))
    .filter((t) => t.length > 2);
  const freq = {};
  for (const t of tokens) freq[t] = (freq[t] || 0) + 1;
  const sorted = Object.keys(freq).sort((a, b) => {
    if (freq[b] !== freq[a]) return freq[b] - freq[a];
    return a.localeCompare(b);
  });
  const seeded = [category, ...CATEGORY_KEYWORDS[category] || []];
  const merged = [];
  for (const s of seeded) {
    if (s && !merged.includes(s)) merged.push(s);
    if (merged.length >= 8) break;
  }
  for (const s of sorted) {
    if (!merged.includes(s)) merged.push(s);
    if (merged.length >= 8) break;
  }
  return merged.slice(0, 8);
}

function expandQuery(normalizedQuery, intent, category) {
  const base = normalizedQuery.replace(/[?.!]$/, '');
  const categoryContext = {
    hiring: 'including hiring process, screening, interview rounds, candidate evaluation criteria, and recruitment policy',
    products: 'including product portfolio, platforms, capabilities, roadmap, and active development initiatives',
    policies: 'including official policies, rules, governance requirements, and compliance conditions',
    security: 'including security controls, data protection, compliance standards, and incident response practices',
    general: 'including company overview, business context, services, and operational scope',
  };
  const intentContext = {
    informational: 'Provide factual details from official documents',
    transactional: 'Identify actionable steps and required conditions from documents',
    comparison: 'Highlight explicit differences and similarities from documented evidence',
    troubleshooting: 'Identify root causes and remediation guidance documented in knowledge base',
    exploratory: 'Provide broad structured overview grounded in available documents',
  };
  return `${intentContext[intent]}. ${base} ${categoryContext[category]}.`;
}

function detectPriority(text, intent) {
  const q = text.toLowerCase();
  if (/\b(urgent|asap|immediately|critical|security breach|incident)\b/.test(q)) return 'high';
  if (intent === 'troubleshooting' || intent === 'transactional') return 'high';
  if (/\b(compare|difference|overview|about|what|how)\b/.test(q)) return 'medium';
  return 'low';
}

function understandQuery(query) {
  const normalized_query = normalizeQuery(query);
  const category = classifyCategory(normalized_query);
  const intent = detectIntent(normalized_query);
  const expanded_query = expandQuery(normalized_query, intent, category);
  const keywords = extractKeywords(normalized_query, category);
  const filters = {
    category,
    priority: detectPriority(normalized_query, intent),
  };
  return {
    normalized_query,
    expanded_query,
    intent,
    category,
    keywords,
    confidence: 0.75,
    filters,
  };
}

async function understandQueryWithAI(query) {
  const base = understandQuery(query);
  // AI rewrite + intent detection with strict JSON, deterministic llm config.
  const prompt = `You are a query understanding engine for a RAG system.
Return STRICT JSON only with keys:
normalized_query, expanded_query, intent, category, keywords, filters, confidence

Rules:
- category must be one of: hiring, products, policies, security, general
- intent must be one of: informational, transactional, comparison, troubleshooting, exploratory
- filters must include category and priority (high|medium|low)
- confidence must be number between 0 and 1
- do not answer the query

User query:
${query}

Deterministic baseline:
${JSON.stringify(base)}
`;
  try {
    const raw = await llmService.execute(prompt);
    const cleaned = raw.replace(/```json\s*/gi, '').replace(/```/g, '').trim();
    const first = cleaned.indexOf('{');
    const last = cleaned.lastIndexOf('}');
    if (first === -1 || last === -1) return base;
    const parsed = JSON.parse(cleaned.slice(first, last + 1));
    const category = CATEGORIES.includes(parsed.category) ? parsed.category : base.category;
    const intent = ['informational', 'transactional', 'comparison', 'troubleshooting', 'exploratory'].includes(parsed.intent)
      ? parsed.intent
      : base.intent;
    const keywords = Array.isArray(parsed.keywords)
      ? parsed.keywords.map((k) => String(k).toLowerCase()).filter(Boolean).slice(0, 12)
      : base.keywords;
    const priority = ['high', 'medium', 'low'].includes(parsed?.filters?.priority)
      ? parsed.filters.priority
      : base.filters.priority;
    return {
      normalized_query: parsed.normalized_query ? String(parsed.normalized_query) : base.normalized_query,
      expanded_query: parsed.expanded_query ? String(parsed.expanded_query) : base.expanded_query,
      intent,
      category,
      keywords,
      confidence: typeof parsed.confidence === 'number' ? Math.max(0, Math.min(1, parsed.confidence)) : base.confidence,
      filters: { category, priority },
    };
  } catch (_) {
    return base;
  }
}

module.exports = {
  understandQuery,
  understandQueryWithAI,
  CATEGORIES,
};
