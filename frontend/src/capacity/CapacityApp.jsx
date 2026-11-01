import { useCallback, useMemo, useState } from 'react';
import { http } from '../common/api.js';
import ScheduleTable, { cellAttributes } from '../common/ScheduleTable.jsx';
import { indexCells } from '../common/schedule.js';
import UnitModal from './UnitModal.jsx';

/** Public capacity board: hover a cell for the seats, click it to see who chose it. */
export default function CapacityApp({ config }) {
  const { lineTable, capacity, urls } = config;
  const cells = useMemo(() => indexCells(lineTable, capacity), [lineTable, capacity]);
  const [details, setDetails] = useState(null);
  const close = useCallback(() => setDetails(null), []);

  const open = async (unit) => {
    try {
      const { data } = await http.post(urls.selector, { unitName: unit });
      setDetails({
        title: `بخش و لاین: ${unit} (${data.count} نفر)`,
        persons: data.persons,
      });
    } catch (error) {
      console.error('Error:', error);
      window.alert(error.response?.data?.message || 'بخش انتخاب شده ظرفیت ندارد');
    }
  };

  const renderCell = (cell, index) => {
    const info = cell.id === undefined ? undefined : cells.get(cell.id);
    return (
      <td
        key={index}
        {...cellAttributes(cell)}
        title={info?.tooltip}
        onClick={info ? () => open(info.unit) : undefined}
      >
        {cell.content}
      </td>
    );
  };

  return (
    <>
      <ScheduleTable rows={lineTable} renderCell={renderCell} columnGroup={false} />
      {details && <UnitModal {...details} onClose={close} />}
    </>
  );
}
