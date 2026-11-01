import test from 'node:test';
import assert from 'node:assert/strict';
import { compareCells, matchesSearch, normalize } from '../src/members/sort.js';

test('normalize reads numbers and dates', () => {
  assert.equal(normalize('12'), 12);
  assert.equal(normalize('3.5'), 3.5);
  assert.ok(normalize('2025-03-30 12:00:00') instanceof Date);
  assert.equal(normalize('1A'), '1A');
  assert.equal(normalize('12abc'), '12abc');
});

test('numbers sort numerically, not alphabetically', () => {
  const sorted = ['10', '9', '100'].sort((a, b) => compareCells(a, b, true));
  assert.deepEqual(sorted, ['9', '10', '100']);
});

test('dates sort chronologically and descending reverses', () => {
  const dates = ['2025-03-30 12:00:00', '2024-12-01 08:00:00', '2025-01-15 09:30:00'];
  assert.deepEqual([...dates].sort((a, b) => compareCells(a, b, true)),
    ['2024-12-01 08:00:00', '2025-01-15 09:30:00', '2025-03-30 12:00:00']);
  assert.deepEqual([...dates].sort((a, b) => compareCells(a, b, false)),
    ['2025-03-30 12:00:00', '2025-01-15 09:30:00', '2024-12-01 08:00:00']);
});

test('text sorts alphabetically', () => {
  assert.deepEqual(['b', 'c', 'a'].sort((a, b) => compareCells(a, b, true)), ['a', 'b', 'c']);
});

test('empty cells always sink to the bottom', () => {
  for (const ascending of [true, false]) {
    const sorted = ['', 'b', '  ', 'a'].sort((a, b) => compareCells(a, b, ascending));
    assert.deepEqual(sorted.slice(0, 2).map((x) => x.trim()), ascending ? ['a', 'b'] : ['b', 'a']);
    assert.deepEqual(sorted.slice(2).map((x) => x.trim()), ['', '']);
  }
});

test('search looks through all cells, ignoring case', () => {
  const row = ['1', 'Ali Reza', '1A', ''];
  assert.equal(matchesSearch(row, 'reza'), true);
  assert.equal(matchesSearch(row, '1a'), true);
  assert.equal(matchesSearch(row, 'zzz'), false);
  assert.equal(matchesSearch(row, ''), true);
});
