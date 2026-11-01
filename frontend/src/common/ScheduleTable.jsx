/** Number of columns of the board: 1 label column + 36 lines (1A ... 18B). */
export const COLUMN_COUNT = 37;

/**
 * Attributes every board cell carries (taken from the spreadsheet export).
 * `title` is left to the caller because each page shows its own tooltip.
 */
export function cellAttributes(cell) {
  return {
    id: cell.id,
    className: cell.class,
    colSpan: cell.colspan,
    rowSpan: cell.rowspan,
  };
}

/**
 * The line schedule board. The pages decide what a cell contains and when it is
 * shown by passing `renderCell(cell, index)`, which returns a `<td>`. Pass
 * `columnGroup={false}` to leave the column widths to the browser.
 */
export default function ScheduleTable({ rows, renderCell, columnGroup = true }) {
  return (
    <table border="0" cellPadding="0" cellSpacing="0" id="sheet0" className="sheet0 gridlines">
      {columnGroup && (
        <colgroup>
          {Array.from({ length: COLUMN_COUNT }, (_, column) => (
            <col key={column} className={`col${column}`} />
          ))}
        </colgroup>
      )}
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} className={row.class}>
            {row.cells.map((cell, index) => renderCell(cell, index))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
