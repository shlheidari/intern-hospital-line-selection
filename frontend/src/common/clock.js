/**
 * Time helpers for the countdown. The server stores a student's window as
 * wall-clock Tehran time ("YYYY-MM-DD HH:MM:SS"), so both "now" and the end of
 * the window are compared as wall-clock values; the browser's own time zone
 * does not matter.
 */

export const TEHRAN = 'Asia/Tehran';
const DASH_LENGTH = 283; // circumference of the SVG ring

/** "2025-03-30 12:00:00" -> milliseconds (wall clock read as UTC), or null. */
export function parseWallClock(text) {
  const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/.exec(text ?? '');
  if (!match) return null;
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number);
  return Date.UTC(year, month - 1, day, hour, minute, second);
}

/** The current Tehran wall-clock time, in the same representation. */
export function tehranNow(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: TEHRAN, hourCycle: 'h23',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).formatToParts(date);
  const get = (type) => Number(parts.find((part) => part.type === type).value);
  return Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'));
}

export function secondsBetween(fromMs, toMs) {
  return (toMs - fromMs) / 1000;
}

/** 125 -> "2:05" */
export function formatClock(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest < 10 ? `0${rest}` : rest}`;
}

/** Ring colour: red in the last 30 seconds, orange in the last 60. */
export function timerColor(secondsLeft) {
  if (secondsLeft <= 30) return 'red';
  if (secondsLeft <= 60) return 'orange';
  return 'green';
}

/** Value of the SVG `stroke-dasharray` for the part of the window left. */
export function ringDashArray(secondsLeft, limitSeconds) {
  const raw = secondsLeft / limitSeconds;
  const fraction = Math.max(0, raw - (1 / limitSeconds) * (1 - raw));
  return `${(fraction * DASH_LENGTH).toFixed(0)} ${DASH_LENGTH}`;
}
