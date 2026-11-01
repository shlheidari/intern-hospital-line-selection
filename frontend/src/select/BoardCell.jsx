import { cellAttributes } from '../common/ScheduleTable.jsx';
import { NONE_LABEL } from '../common/schedule.js';

/**
 * One cell of the board for a student choosing hospitals.
 *
 * `info` (from indexCells) is present for cells that have an id; cells without
 * capacity are greyed out. Clicking a cell opens the list of hospitals
 * (`options`); clicking an option reports it through `onPick`.
 */
export default function BoardCell({ cell, info, visible, chosen, open, options, onOpen, onPick }) {
  const dark = info && !info.hasCapacity;
  const attributes = cellAttributes(cell);
  if (dark) attributes.className = `${cell.class} dark-cell`;

  return (
    <td
      {...attributes}
      title={info?.hasCapacity ? info.tooltip : cell.title}
      hidden={!visible}
      onClick={info ? () => onOpen(info) : undefined}
    >
      <div>
        {info && options.length > 0 && (
          <table id={`t${cell.id}`} className={open ? 'stylet open' : 'stylet'}>
            <tbody>
              {[NONE_LABEL, ...options].map((option) => (
                <tr key={option}>
                  <td
                    onClick={(event) => {
                      event.stopPropagation();
                      onPick(info, option);
                    }}
                  >
                    {option}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div>
          <span>{cell.content}</span>
          <div><span>{chosen}</span></div>
        </div>
      </div>
    </td>
  );
}
