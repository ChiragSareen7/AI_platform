const http = require('http');
const https = require('https');
const config = require('../config/defaultConfig');
const { estimateQueryResponseTokens } = require('../utils/tokenEstimator');

const AGENT_URL = config.agent.baseUrl.replace(/\/$/, '');
const CHAT_PATH = config.agent.chatPath.startsWith('/') ? config.agent.chatPath : `/${config.agent.chatPath}`;
const TIMEOUT_MS = config.agent.timeoutMs;

function parseUrl(urlStr) {
  const u = new URL(urlStr);
  const port = u.port || (u.protocol === 'https:' ? '443' : '80');
  return {
    protocol: u.protocol,
    hostname: u.hostname,
    port: Number(port),
    path: (u.pathname || '/') + (u.search || ''),
  };
}

function wrapAgentError(err) {
  if (!err) return new Error('Unknown error calling the AI agent');
  const code = err.code;
  const base = `${AGENT_URL}${CHAT_PATH}`;
  if (code === 'ECONNREFUSED') {
    return new Error(
      `Cannot connect to AI agent at ${base} (connection refused). Start the RAG server: cd AI_agent && python app.py`
    );
  }
  if (code === 'ENOTFOUND') {
    return new Error(`Cannot resolve AI agent host for ${base}: ${err.hostname || ''}`);
  }
  if (code === 'ETIMEDOUT' || code === 'ESOCKETTIMEDOUT') {
    return new Error(`AI agent request timed out (${TIMEOUT_MS}ms) — ${base}`);
  }
  const msg = (err.message && String(err.message).trim()) || err.code || String(err);
  return msg ? new Error(msg) : new Error('Unknown error calling the AI agent');
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
  const lib = isHttps ? https : http;

  const body = JSON.stringify({
    message: injectedMessage,
    session_id: agentConfig?.sessionId || 'platform',
  });

  const options = {
    hostname,
    port,
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
        const status = res.statusCode || 0;
        const snippet = (data || '').trim().slice(0, 240);
        try {
          const parsed = data ? JSON.parse(data) : {};
          if (status >= 400) {
            const detail = parsed.detail;
            const detailStr =
              typeof detail === 'string'
                ? detail
                : Array.isArray(detail)
                  ? JSON.stringify(detail)
                  : detail != null
                    ? String(detail)
                    : '';
            const msg = detailStr || parsed.message || `HTTP ${status}`;
            reject(new Error(msg || `AI agent returned HTTP ${status}`));
          } else {
            resolve(parsed);
          }
        } catch (e) {
          reject(
            new Error(
              snippet
                ? `Invalid JSON from AI agent (HTTP ${status}): ${snippet}`
                : `Empty response from AI agent (HTTP ${status}). Is ${AGENT_URL} the RAG server?`
            )
          );
        }
      });
    });
    req.on('error', (err) => reject(wrapAgentError(err)));
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Agent request timeout after ${TIMEOUT_MS}ms — ${url}`));
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
