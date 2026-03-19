const { readPrompts, writePrompts, updatePromptPerformance } = require('./storage.service');

const DEFAULT_PROMPTS = {
  v1: 'Answer the user question clearly and helpfully. Prefer company documents when relevant; otherwise use general knowledge. Keep answers concise.',
  v2: 'Answer accurately using the provided context. Prioritize exact information from the documents. If the documents do not contain the answer, say so clearly. Be precise and cite sources when possible.',
  v3: 'You must answer ONLY using the provided context from company documents. Do not use external knowledge. If the context does not contain enough information to answer, respond: "The provided documents do not contain this information." Cite the source document for every claim.',
};

async function getPromptVersion(version) {
  const data = await readPrompts();
  const versions = data.versions && Object.keys(data.versions).length > 0 ? data.versions : DEFAULT_PROMPTS;
  return versions[version] || versions.v1 || DEFAULT_PROMPTS.v1;
}

async function getAllPrompts() {
  const data = await readPrompts();
  const versions = data.versions && Object.keys(data.versions).length > 0 ? data.versions : DEFAULT_PROMPTS;
  return versions;
}

async function setPromptVersion(version, text) {
  const data = await readPrompts();
  data.versions = data.versions || { ...DEFAULT_PROMPTS };
  data.versions[version] = text;
  await writePrompts(data);
  return data.versions[version];
}

async function getPerformance() {
  const data = await readPrompts();
  return data.performance || {};
}

async function recordRun(version, stats) {
  return updatePromptPerformance(version, stats);
}

module.exports = {
  getPromptVersion,
  getAllPrompts,
  setPromptVersion,
  getPerformance,
  recordRun,
  DEFAULT_PROMPTS,
};
