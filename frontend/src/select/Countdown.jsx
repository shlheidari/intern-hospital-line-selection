import { useEffect, useRef, useState } from 'react';
import {
  formatClock, parseWallClock, ringDashArray, secondsBetween, tehranNow, timerColor,
} from '../common/clock.js';

const RING_PATH = 'M 50, 50 m -45, 0 a 45,45 0 1,0 90,0 a 45,45 0 1,0 -90,0';

/** Ring + clock showing how long the student's selection window has left. */
export default function Countdown({ startTime, endTime, onExpire }) {
  const start = parseWallClock(startTime);
  const end = parseWallClock(endTime);
  const limit = secondsBetween(start, end);
  const [left, setLeft] = useState(() => secondsBetween(tehranNow(), end));
  const expire = useRef(onExpire);
  expire.current = onExpire;

  useEffect(() => {
    const timer = setInterval(() => {
      const remaining = secondsBetween(tehranNow(), end);
      setLeft(remaining);
      if (remaining <= 0) {
        clearInterval(timer);
        expire.current();
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [end]);

  return (
    <div id="timerr">
      <div className="base-timer">
        <svg className="base-timer__svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
          <g className="base-timer__circle">
            <circle className="base-timer__path-elapsed" cx="50" cy="50" r="45" />
            <path
              id="base-timer-path-remaining"
              className={`base-timer__path-remaining ${timerColor(left)}`}
              strokeDasharray={ringDashArray(left, limit)}
              d={RING_PATH}
            />
          </g>
        </svg>
        <span id="base-timer-label" className="base-timer__label">{formatClock(left)}</span>
      </div>
    </div>
  );
}
