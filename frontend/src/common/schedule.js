/**
 * Pure helpers for the line schedule board and the capacity data behind it.
 *
 * Terminology
 *  - line      "1A" ... "18B": one column of the board
 *  - unit      a department on a line, e.g. "جراحی-1A" (also the cell's title)
 *  - capacity  rows {line, unit, hospital, full, remain, ...}; the row whose
 *              hospital is "All" holds the seats of the whole line
 */

export const NONE_LABEL = 'هیچ کدام'; // the "no hospital" choice
export const ALL = 'All';
const ELECTIVE_MARK = 'الکتیو';

/** Column number (the `columnN` CSS class) of a table cell, or null. */
export function columnOf(cell) {
  const match = /(?:^|\s)column(\d+)(?:\s|$)/.exec(cell.class ?? '');
  return match ? Number(match[1]) : null;
}

/** "1A" -> 1, "1B" -> 2, "2A" -> 3 ... "18B" -> 36; anything else -> null. */
export function lineColumn(line) {
  const match = /^(\d+)([AB])$/.exec(line ?? '');
  if (!match) return null;
  const column = (Number(match[1]) - 1) * 2 + (match[2] === 'A' ? 1 : 2);
  return column >= 1 && column <= 36 ? column : null;
}

/** All capacity rows of a unit (cell title). */
export function unitRows(capacity, unit) {
  return capacity.filter((row) => row.unit === unit);
}

/** Hospitals of a unit that still have seats - what a student can choose from. */
export function hospitalChoices(capacity, unit) {
  return unitRows(capacity, unit)
    .filter((row) => row.hospital !== ALL && row.remain > 0)
    .map((row) => row.hospital);
}

/** Tooltip text: one "hospital: remain از full" line per capacity row. */
export function capacityTooltip(capacity, unit) {
  return unitRows(capacity, unit)
    .map((row) => `${row.hospital}:  ${row.remain} از ${row.full}`)
    .join('\n');
}

/** The per-line totals (rows whose hospital is "All"). */
export function lineSummaries(capacity) {
  return capacity.filter((row) => row.hospital === ALL);
}

/** Lines that still have a free seat, in table order. */
export function selectableLines(capacity) {
  return lineSummaries(capacity)
    .filter((row) => row.remain > 0)
    .map((row) => row.line);
}

export function isElective(label) {
  return (label ?? '').includes(ELECTIVE_MARK);
}

/**
 * The specialty of an elective choice: the first word of the name, or the first
 * two when it starts with "طب" ("طب کار ..."). A student may take each
 * specialty only once across the three electives.
 */
export function electiveSpecialty(hospital) {
  const words = (hospital ?? '').split(' ');
  return words[0] === 'طب' && words.length > 1 ? `${words[0]} ${words[1]}` : words[0];
}

/** Specialties already taken: from the hospitals chosen in the elective cells. */
export function takenSpecialties(hospitals) {
  return hospitals.filter(Boolean).map(electiveSpecialty);
}

/** Is an option hidden because its specialty was taken by an elective? */
export function isOptionBlocked(option, taken) {
  return option !== NONE_LABEL && taken.some((specialty) => option.includes(specialty));
}

/**
 * Index of the board cells by id, with everything a page needs to render and
 * handle a click. The cell's original `title` is the unit name used to look up
 * its capacity.
 */
export function indexCells(rows, capacity) {
  const cells = new Map();
  for (const row of rows) {
    for (const cell of row.cells) {
      if (cell.id === undefined) continue;
      const unit = cell.title ?? '';
      cells.set(cell.id, {
        id: cell.id,
        unit,
        label: cell.content ?? '',
        column: columnOf(cell),
        columnClass: (cell.class ?? '').split(' ')[0],
        hospitals: hospitalChoices(capacity, unit),
        tooltip: capacityTooltip(capacity, unit),
        hasCapacity: unitRows(capacity, unit).length > 0,
        elective: isElective(cell.content),
      });
    }
  }
  return cells;
}
