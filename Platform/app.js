const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const queryRoutes = require('./src/routes/query.routes');
const preferencesRoutes = require('./src/routes/preferences.routes');
const dashboardRoutes = require('./src/routes/dashboard.routes');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const storeDir = path.join(process.cwd(), 'store');

async function ensureStore() {
  await fs.mkdir(storeDir, { recursive: true });
  const files = {
    'logs.json': '[]',
    'metrics.json': JSON.stringify({ aggregated: {}, byPrompt: {}, lastUpdated: null }, null, 2),
    'prompts.json': JSON.stringify({ versions: {}, performance: {} }, null, 2),
    'preferences.json': JSON.stringify({
      maxLatency: 2000,
      maxTokens: 800,
      maxCost: 0.05,
      minAccuracy: 0.7,
      maxHallucination: 0.3,
      minRelevance: 0.5,
      minConfidence: 0.5,
      responseType: 'balanced',
      temperature: 0.7,
    }, null, 2),
  };
  for (const [name, defaultContent] of Object.entries(files)) {
    const filePath = path.join(storeDir, name);
    try {
      await fs.access(filePath);
    } catch {
      await fs.writeFile(filePath, defaultContent, 'utf8');
    }
  }
}

app.use('/', queryRoutes);
app.use('/', preferencesRoutes);
app.use('/', dashboardRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'ai-observability-platform' });
});

app.listen(PORT, async () => {
  await ensureStore();
  console.log(`AI Observability Platform running on http://localhost:${PORT}`);
  console.log(`Dashboard:    http://localhost:${PORT}/`);
  console.log(`Preferences:  http://localhost:${PORT}/preferences.html`);
  console.log(`POST /query   POST /preferences   GET /preferences`);
});

module.exports = app;
