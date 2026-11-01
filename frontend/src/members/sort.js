/** Sorting rules of the members table (pure, so they can be tested). */

const DATE_PATTERN = /(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/;

function isNumeric(text) {
  return text !== '' && !Number.isNaN(parseFloat(text)) && Number.isFinite(Number(text));
}

/** Numbers sort as numbers, "YYYY-MM-DD HH:MM:SS" as dates, anything else as text. */
export function normalize(text) {
  if (isNumeric(text)) return parseFloat(text);
  const parts = DATE_PATTERN.exec(text);
  if (parts) {
    const [year, month, day, hour, minute, second] = parts.slice(1).map(Number);
    return new Date(year, month - 1, day, hour, minute, second);
  }
  return text;
}

/** Comparator for cell texts; empty cells always sink to the bottom. */
export function compareCells(left, right, ascending) {
  const a = left.trim();
  const b = right.trim();
  if (a === '' && b !== '') return 1;
  if (b === '' && a !== '') return -1;
  if (a === '' && b === '') return 0;

  const x = normalize(a);
  const y = normalize(b);
  const result = typeof x === 'string' || typeof y === 'string'
    ? String(x).localeCompare(String(y))
    : x - y;
  return ascending ? result : -result;
}

/** Does a row's text contain the (already lower-cased) search text? */
export function matchesSearch(cellTexts, search) {
  return cellTexts.map((text) => text.toLowerCase()).join(' ').includes(search);
}
