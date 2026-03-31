const queryInput = document.getElementById('queryInput');
const runBtn = document.getElementById('runBtn');
const reportBtn = document.getElementById('reportBtn');
const statusEl = document.getElementById('status');
const bestResponseEl = document.getElementById('bestResponse');
const blueMetricsEl = document.getElementById('blueMetrics');
const reportEl = document.getElementById('report');
const tableBody = document.querySelector('#responsesTable tbody');

function jsonPretty(obj) {
  return JSON.stringify(obj, null, 2);
}

async function runQuery() {
  const query = queryInput.value.trim();
  if (!query) {
    statusEl.textContent = 'Enter a query first.';
    return;
  }

  statusEl.textContent = 'Running orchestration...';
  runBtn.disabled = true;

  try {
    const res = await fetch('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Query failed');

    bestResponseEl.textContent =
      `best_model: ${data.best_model}
` +
      `best_prompt: ${data.best_prompt}

` +
      `${data.best_answer}`;

    if ((data.errors || []).length) {
      statusEl.textContent = `Completed with errors: ${data.errors[0]}`;
    }

    blueMetricsEl.textContent = jsonPretty(data.blue_metrics || {});

    tableBody.innerHTML = '';
    for (const row of data.all_responses || []) {
      const tr = document.createElement('tr');
      const sem = row.metrics?.semantic;
      tr.innerHTML = `
        <td>${row.model}</td>
        <td>${row.prompt_version}</td>
        <td>${row.metrics?.accuracyScore ?? ''}</td>
        <td>${row.metrics?.hallucinationScore ?? ''}</td>
        <td>${sem?.accuracy ?? ''}</td>
        <td>${sem?.confidence ?? ''}</td>
        <td>${row.metrics?.latency ?? ''}</td>
        <td>${row.error ? String(row.error).slice(0, 90) : ''}</td>
        <td>${(row.response || '').slice(0, 220)}</td>
      `;
      tableBody.appendChild(tr);
    }

    statusEl.textContent = 'Done.';
    await loadReport();
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    runBtn.disabled = false;
  }
}

async function loadReport() {
  try {
    const res = await fetch('/report');
    const data = await res.json();
    reportEl.textContent = jsonPretty(data);
  } catch (err) {
    reportEl.textContent = `Failed to load report: ${err.message}`;
  }
}

runBtn.addEventListener('click', runQuery);
reportBtn.addEventListener('click', loadReport);
queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') runQuery();
});

loadReport();
