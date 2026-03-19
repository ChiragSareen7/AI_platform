/**
 * LLM execution with deterministic config: temperature=0, seed=42.
 */
const config = require('../../config');

const { apiKey, model, baseUrl } = config.groq;
const { temperature, top_p, seed, max_tokens } = config.llm;

async function execute(prompt) {
  const url = `${baseUrl}/chat/completions`;
  const body = {
    model,
    messages: [{ role: 'user', content: prompt }],
    temperature,
    top_p,
    seed,
    max_tokens,
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`LLM failed: ${res.status} ${err}`);
  }
  const data = await res.json();
  const content = data.choices?.[0]?.message?.content?.trim() || '';
  return content;
}

module.exports = { execute };
