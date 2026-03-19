const express = require('express');
const path = require('path');
const fs = require('fs').promises;

const deterministicRoutes = require('./src/routes/deterministic.routes');

const app = express();
const PORT = process.env.PORT || 3002;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const storeDir = path.join(process.cwd(), 'store');
async function ensureStore() {
  await fs.mkdir(storeDir, { recursive: true });
  const logsPath = path.join(storeDir, 'logs.json');
  try {
    await fs.access(logsPath);
  } catch {
    await fs.writeFile(logsPath, '[]', 'utf8');
  }
}

app.use('/', deterministicRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'deterministic-ai-platform' });
});

app.listen(PORT, async () => {
  await ensureStore();
  console.log(`Deterministic AI Platform running on http://localhost:${PORT}`);
  console.log(`Dashboard: http://localhost:${PORT}/deterministic.html`);
  console.log(`POST /deterministic-query`);
});

module.exports = app;
