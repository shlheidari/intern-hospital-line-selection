// Live view of the members and selection tables with click-to-edit cells.
import { http } from '../common/api.js';
import { readConfig } from '../common/config.js';

const REFRESH_MS = 3000;
const config = readConfig();
const lastRendered = {};

function render(name, { columns, rows }) {
  const table = document.getElementById(`${name}-table`);
  const head = table.createTHead();
  head.innerHTML = '';
  const headerRow = head.insertRow();
  for (const column of columns) {
    const th = document.createElement('th');
    th.textContent = column;
    headerRow.append(th);
  }

  const body = table.tBodies[0];
  body.replaceChildren();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const column of columns) {
      const td = tr.insertCell();
      td.textContent = row[column] ?? '';
      if (column === 'id') continue;
      td.className = 'editable';
      td.dataset.table = name;
      td.dataset.id = row.id;
      td.dataset.column = column;
    }
  }
}

async function refresh(name) {
  const { data } = await http.get(config.urls[name]);
  const signature = JSON.stringify(data);
  if (signature === lastRendered[name]) return; // nothing changed, keep the page still
  lastRendered[name] = signature;
  render(name, data);
}

async function refreshAll() {
  if (document.hidden) return;
  try {
    await Promise.all(['members', 'selection'].map(refresh));
  } catch (error) {
    console.error('Could not load data:', error);
  }
}

document.addEventListener('click', async (event) => {
  const cell = event.target.closest('td.editable');
  if (!cell) return;
  const { table, id, column } = cell.dataset;
  const value = window.prompt(`Edit ${column} of row ${id}:`, cell.textContent);
  if (value === null) return;
  try {
    await http.post(config.urls.update, { table, id, column, value });
    cell.textContent = value;
  } catch (error) {
    window.alert(error.response?.data?.message ?? 'The change could not be saved.');
  }
  lastRendered[table] = undefined; // reload from the server to show what was stored
});

refreshAll();
setInterval(refreshAll, REFRESH_MS);
