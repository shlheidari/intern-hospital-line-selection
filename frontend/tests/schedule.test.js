import test from 'node:test';
import assert from 'node:assert/strict';
import {
  NONE_LABEL, capacityTooltip, columnOf, electiveSpecialty, hospitalChoices, indexCells,
  isElective, isOptionBlocked, lineColumn, lineSummaries, selectableLines, takenSpecialties,
} from '../src/common/schedule.js';

const capacity = [
  { line: '1A', unit: '1 A-1A', hospital: 'All', full: 8, remain: 7 },
  { line: '1B', unit: '1 B-1B', hospital: 'All', full: 5, remain: 0 },
  { line: '1A', unit: 'جراحی-1A', hospital: 'شریعتی', full: 4, remain: 4 },
  { line: '1A', unit: 'جراحی-1A', hospital: 'سینا', full: 2, remain: 0 },
  { line: '1A', unit: 'جراحی-1A', hospital: 'امام', full: 3, remain: 1 },
];

test('lineColumn maps every line to its board column', () => {
  assert.equal(lineColumn('1A'), 1);
  assert.equal(lineColumn('1B'), 2);
  assert.equal(lineColumn('2A'), 3);
  assert.equal(lineColumn('10B'), 20);
  assert.equal(lineColumn('18B'), 36);
  const columns = [];
  for (let n = 1; n <= 18; n += 1) columns.push(lineColumn(`${n}A`), lineColumn(`${n}B`));
  assert.deepEqual(columns, Array.from({ length: 36 }, (_, i) => i + 1));
});

test('lineColumn rejects anything that is not a line', () => {
  for (const bad of ['', 'N', '0A', '19A', '1C', 'A1', undefined, null, 'لطفا']) {
    assert.equal(lineColumn(bad), null, String(bad));
  }
});

test('columnOf reads the columnN class', () => {
  assert.equal(columnOf({ class: 'column12 style3 s' }), 12);
  assert.equal(columnOf({ class: 'column0 style1 null' }), 0);
  assert.equal(columnOf({ class: 'style3' }), null);
  assert.equal(columnOf({}), null);
  assert.equal(columnOf({ class: 'mycolumn3' }), null);
});

test('hospitalChoices lists only hospitals with seats left', () => {
  assert.deepEqual(hospitalChoices(capacity, 'جراحی-1A'), ['شریعتی', 'امام']);
  assert.deepEqual(hospitalChoices(capacity, '1 A-1A'), []); // "All" is not a hospital
  assert.deepEqual(hospitalChoices(capacity, 'unknown'), []);
});

test('capacityTooltip has one line per capacity row', () => {
  assert.equal(capacityTooltip(capacity, 'جراحی-1A'),
    'شریعتی:  4 از 4\nسینا:  0 از 2\nامام:  1 از 3');
  assert.equal(capacityTooltip(capacity, 'unknown'), '');
});

test('line summaries and selectable lines', () => {
  assert.deepEqual(lineSummaries(capacity).map((row) => row.line), ['1A', '1B']);
  assert.deepEqual(selectableLines(capacity), ['1A']);
});

test('electiveSpecialty is the first word, or two for "طب ..."', () => {
  assert.equal(electiveSpecialty('بیهوشی امام'), 'بیهوشی');
  assert.equal(electiveSpecialty('طب کار شریعتی'), 'طب کار');
  assert.equal(electiveSpecialty('طب'), 'طب');
  assert.equal(electiveSpecialty('اورو'), 'اورو');
});

test('a specialty can be taken once across the electives', () => {
  const taken = takenSpecialties(['بیهوشی امام', '', undefined, 'طب کار سینا']);
  assert.deepEqual(taken, ['بیهوشی', 'طب کار']);
  assert.equal(isOptionBlocked('بیهوشی سینا', taken), true);
  assert.equal(isOptionBlocked('طب کار امام', taken), true);
  assert.equal(isOptionBlocked('نورولوژی امام', taken), false);
  assert.equal(isOptionBlocked(NONE_LABEL, taken), false);
  assert.equal(isOptionBlocked('بیهوشی سینا', []), false);
});

test('isElective recognises elective labels', () => {
  assert.equal(isElective('الکتیو-اول'), true);
  assert.equal(isElective('جراحی'), false);
  assert.equal(isElective(undefined), false);
});

test('indexCells combines cells with their capacity', () => {
  const rows = [{ id: 1, class: 'row0', cells: [
    { class: 'column0 style1 null', content: '' },
    { id: '5', title: 'جراحی-1A', class: 'column1 style3 s', content: 'جراحی' },
    { id: '6', title: 'عفونی-1A', class: 'column1 style3 s', content: '' },
  ] }];
  const cells = indexCells(rows, capacity);
  assert.deepEqual([...cells.keys()], ['5', '6']);
  const surgery = cells.get('5');
  assert.equal(surgery.column, 1);
  assert.equal(surgery.columnClass, 'column1');
  assert.deepEqual(surgery.hospitals, ['شریعتی', 'امام']);
  assert.equal(surgery.hasCapacity, true);
  assert.equal(surgery.elective, false);
  assert.equal(cells.get('6').hasCapacity, false);
  assert.deepEqual(cells.get('6').hospitals, []);
});
