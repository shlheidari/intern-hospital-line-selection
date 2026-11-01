/** Seats per line, shown while no line is selected. */
export default function LineSummary({ summaries, visible }) {
  return (
    <div id="line_detail" style={{ display: visible ? 'block' : 'none' }}>
      <table className="table table-striped">
        <thead>
          <tr>
            <th>لاین</th>
            <th>ظرفیت کل</th>
            <th>ظرفیت باقی مانده</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((row) => (
            <tr key={row.id}>
              <td>{row.line}</td>
              <td>{row.full}</td>
              <td>{row.remain}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
