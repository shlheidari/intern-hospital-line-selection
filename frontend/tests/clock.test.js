import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatClock, parseWallClock, ringDashArray, secondsBetween, tehranNow, timerColor,
} from '../src/common/clock.js';

test('parseWallClock reads the server format', () => {
  assert.equal(parseWallClock('2025-03-30 12:00:00'), Date.UTC(2025, 2, 30, 12, 0, 0));
  assert.equal(parseWallClock('2025-03-30T12:00:00'), Date.UTC(2025, 2, 30, 12, 0, 0));
  assert.equal(parseWallClock('2025-03-30 12:00:00.123456'), Date.UTC(2025, 2, 30, 12, 0, 0));
  assert.equal(parseWallClock('soon'), null);
  assert.equal(parseWallClock(undefined), null);
});

test('window length in seconds', () => {
  const start = parseWallClock('2025-03-30 12:00:00');
  const end = parseWallClock('2025-03-30 12:10:30');
  assert.equal(secondsBetween(start, end), 630);
});

test('tehranNow is the wall clock in Tehran (UTC+3:30)', () => {
  const utc = new Date(Date.UTC(2025, 0, 10, 8, 30, 15));
  assert.equal(tehranNow(utc), Date.UTC(2025, 0, 10, 12, 0, 15));
});

test('formatClock', () => {
  assert.equal(formatClock(125), '2:05');
  assert.equal(formatClock(59), '0:59');
  assert.equal(formatClock(3600), '60:00');
  assert.equal(formatClock(61.9), '1:01');
  assert.equal(formatClock(-5), '0:00');
});

test('timerColor thresholds', () => {
  assert.equal(timerColor(600), 'green');
  assert.equal(timerColor(61), 'green');
  assert.equal(timerColor(60), 'orange');
  assert.equal(timerColor(31), 'orange');
  assert.equal(timerColor(30), 'red');
  assert.equal(timerColor(0), 'red');
});

test('ringDashArray shrinks with the time left', () => {
  assert.equal(ringDashArray(600, 600), '283 283');
  assert.equal(ringDashArray(300, 600), '141 283');
  assert.equal(ringDashArray(0, 600), '0 283');
});
