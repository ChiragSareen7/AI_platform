const http = require('http');
const https = require('https');
const config = require('../config/defaultConfig');
const { estimateQueryResponseTokens } = require('../utils/tokenEstimator');

const AGENT_URL = config.agent.baseUrl;
const CHAT_PATH = config.agent.chatPath;
const TIMEOUT_MS = config.agent.timeoutMs;

function parseUrl(urlStr) {
  const u = new URL(urlStr);
  return {
    protocol: u.protocol,
    hostname: u.hostname,
    port: u.port || (u.protocol === 'https:' ? 443 : 80),
    path: u.pathname + u.search,
  };
}

/**
 * Call external AI agent POST /chat.
 * Injects prompt into the query (prepended as instruction).
 */
async function runAgentWithTracking(query, agentConfig, promptVersion, promptText) {
  const start = Date.now();
  const injectedMessage = promptText
    ? `[Instruction: ${promptText}]\n\nUser question: ${query}`
    : query;

  const url = `${AGENT_URL}${CHAT_PATH}`;
  const { hostname, port, path, protocol } = parseUrl(url);
  const isHttps = protocol === 'https:';
  const lib = isHttps ? require('https') : http;

  const body = JSON.stringify({
    message: injectedMessage,
    session_id: agentConfig?.sessionId || 'platform',
  });

  const options = {
    hostname,
    port: port || (isHttps ? 443 : 80),
    path: path || CHAT_PATH,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body, 'utf8'),
    },
    timeout: TIMEOUT_MS,
  };

  const response = await new Promise((resolve, reject) => {
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', (ch) => { data += ch; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode >= 400) {
            reject(new Error(parsed.detail || parsed.message || `HTTP ${res.statusCode}`));
          } else {
            resolve(parsed);
          }
        } catch (e) {
          reject(new Error(data || 'Invalid JSON'));
        }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Agent request timeout'));
    });
    req.setTimeout(TIMEOUT_MS);
    req.write(body);
    req.end();
  });

  const latency = Date.now() - start;
  const responseText = response.response || response.answer || '';
  const tokenUsage = response.tokenUsage
    ? { input: response.tokenUsage.input_tokens || 0, output: response.tokenUsage.output_tokens || 0, total: (response.tokenUsage.input_tokens || 0) + (response.tokenUsage.output_tokens || 0) }
    : estimateQueryResponseTokens(injectedMessage, responseText);

  return {
    query,
    response: responseText,
    latency,
    tokenUsage,
    promptVersion,
    config: agentConfig || {},
    sources: response.sources || [],
  };
}

module.exports = {
  runAgentWithTracking,
};
