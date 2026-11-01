import { compareCells, matchesSearch } from './sort.js';

const table = document.getElementById('dtBasicExample');
const body = table.tBodies[0];
const headers = [...table.querySelectorAll('th.sortable')];

const cellTexts = (row) => [...row.cells].map((cell) => cell.textContent);

document.getElementById('searchInput').addEventListener('input', (event) => {
  const search = event.target.value.toLowerCase();
  for (const row of body.rows) {
    row.style.display = matchesSearch(cellTexts(row), search) ? '' : 'none';
  }
});

for (const header of headers) {
  header.addEventListener('click', () => {
    const ascending = !header.classList.contains('asc');
    for (const other of headers) other.classList.remove('asc', 'desc');
    header.classList.add(ascending ? 'asc' : 'desc');

    const column = header.cellIndex;
    const rows = [...body.rows].sort((a, b) =>
      compareCells(a.cells[column].textContent, b.cells[column].textContent, ascending));
    body.append(...rows);
  });
}
