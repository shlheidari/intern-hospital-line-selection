import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { describeError, http } from '../common/api.js';
import ScheduleTable from '../common/ScheduleTable.jsx';
import {
  NONE_LABEL, columnOf, indexCells, isOptionBlocked, lineColumn, lineSummaries,
  selectableLines, takenSpecialties,
} from '../common/schedule.js';
import BoardCell from './BoardCell.jsx';
import Countdown from './Countdown.jsx';
import LineSelect, { PROMPT } from './LineSelect.jsx';
import LineSummary from './LineSummary.jsx';

const POLL_MS = 1000; // how often we check that the account is not used elsewhere

/** A selection in progress stored on the server (page reloaded mid-turn). */
function restore(saved, user, cells) {
  const mine = saved.length > 1 && saved[0].choice === user;
  if (!mine) return { line: '', choices: {} };
  const choices = {};
  for (const row of saved.slice(2)) {
    if (cells.has(row.iden)) choices[row.iden] = row.choice;
  }
  return { line: saved[1].choice, choices };
}

export default function SelectApp({ config }) {
  const { lineTable, capacity, saved, user, student, unitKeys, urls } = config;
  const cells = useMemo(() => indexCells(lineTable, capacity), [lineTable, capacity]);
  const summaries = useMemo(() => lineSummaries(capacity), [capacity]);
  const lines = useMemo(() => selectableLines(capacity), [capacity]);
  const initial = useMemo(() => restore(saved, user, cells), [saved, user, cells]);

  const [line, setLine] = useState(initial.line); // '' = no line chosen
  const [shownLine, setShownLine] = useState(initial.line || null); // line whose column is visible
  const [choices, setChoices] = useState(initial.choices); // cell id -> hospital
  const [openCell, setOpenCell] = useState(null);
  const [busy, setBusy] = useState(false);
  const leaving = useRef(false);

  const leave = useCallback((message) => {
    if (leaving.current) return;
    leaving.current = true;
    window.alert(message);
    window.location.href = urls.index;
  }, [urls.index]);

  const fail = useCallback((error) => {
    console.error('Error details:', error);
    leave(describeError(error));
  }, [leave]);

  // Sign the student out of this page if the account is used from elsewhere.
  useEffect(() => {
    const timer = setInterval(async () => {
      if (leaving.current) return;
      try {
        await http.post(urls.concurrentLogin);
      } catch (error) {
        const message = error.response?.data?.message;
        if (message) leave(message);
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [urls.concurrentLogin, leave]);

  const changeLine = async (value) => {
    const chosenLine = lineColumn(value) ? value : '';
    setLine(chosenLine);
    setShownLine(null);
    setChoices({});
    setOpenCell(null);
    setBusy(true);
    try {
      await http.post(urls.selected, { final: [{ line: chosenLine || 'N' }] });
      setShownLine(chosenLine || null);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };

  const openList = (info) => {
    setOpenCell(info.hospitals.length > 0 ? info.id : null);
  };

  const pick = async (info, option) => {
    const hospital = option === NONE_LABEL ? '' : option;
    setOpenCell(null);
    setBusy(true);
    try {
      await http.post(urls.selected, {
        sel: [{
          a: info.label,
          b: hospital,
          c: choices[info.id] ?? '',
          d: unitKeys[info.label] ?? '',
          i: info.id,
          line_c: info.columnClass,
        }],
      });
      setChoices((previous) => {
        const next = { ...previous };
        if (hospital) next[info.id] = hospital;
        else delete next[info.id];
        return next;
      });
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    setBusy(true);
    try {
      const { data: check } = await http.post(urls.validate, {});
      if (!check.valid) {
        setBusy(false);
        const proceed = window.confirm(
          `${check.message}\n\nآیا مایل به ثبت نهایی با انتخاب‌های فعلی هستید؟`,
        );
        if (!proceed) return;
        setBusy(true);
      }
      const { data: summary } = await http.get(urls.options);
      setBusy(false);
      const sure = window.confirm(
        `موارد انتخاب شده شما:\n${summary.options}\n\nآیا از انتخاب خود مطمئن هستید؟`,
      );
      if (sure) {
        setBusy(true);
        leaving.current = true; // stop checking, we are leaving
        window.location.href = urls.finish;
      }
    } catch (error) {
      setBusy(false);
      console.error('Submission error:', error);
      window.alert(error.response?.data?.message
        || (error.request ? 'اتصال اینترنت خود را بررسی کنید.' : 'خطایی در ارتباط با سرور رخ داد.'));
    }
  };

  // Only the board column of the chosen line (and the label column) is shown.
  const shownColumns = new Set(shownLine ? [0, lineColumn(shownLine)] : []);
  // A specialty may be taken once across the three electives.
  const electiveChoices = [...cells.values()].filter((c) => c.elective).map((c) => choices[c.id]);
  const taken = takenSpecialties(electiveChoices);

  const renderCell = (cell, index) => {
    const info = cell.id === undefined ? undefined : cells.get(cell.id);
    const options = info
      ? info.hospitals.filter((hospital) => !(info.elective && isOptionBlocked(hospital, taken)))
      : [];
    return (
      <BoardCell
        key={index}
        cell={cell}
        info={info}
        visible={shownColumns.has(columnOf(cell))}
        chosen={info ? choices[info.id] ?? '' : ''}
        open={info !== undefined && openCell === info.id}
        options={options}
        onOpen={openList}
        onPick={pick}
      />
    );
  };

  return (
    <>
      <Countdown
        startTime={student.startTime}
        endTime={student.endTime}
        onExpire={() => leave('زمان انتخاب شما به پایان رسید')}
      />
      <div id="loading-spinner" style={{ display: busy ? 'block' : 'none' }}>
        <i className="glyphicon glyphicon-refresh" />
      </div>
      <LineSelect lines={lines} value={line || PROMPT} onChange={changeLine} />
      <LineSummary summaries={summaries} visible={line === ''} />
      <ScheduleTable rows={lineTable} renderCell={renderCell} />
      <div id="button">
        <button type="button" className="final-button" onClick={finish}>ثبت نهایی</button>
      </div>
    </>
  );
}
