import { useLayoutEffect, useState } from 'react';

const PAGE_SIZE = 10;

/**
 * Dialog listing the students on a unit, ten per page. Uses the Bootstrap 3
 * modal styles; opening/closing is handled here, not by Bootstrap's JavaScript.
 */
export default function UnitModal({ title, persons, onClose }) {
  const [page, setPage] = useState(1);
  const pages = Math.ceil(persons.length / PAGE_SIZE);
  const visible = persons.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // A layout effect, so the Escape handler is in place as soon as the dialog is on screen.
  useLayoutEffect(() => {
    const onKey = (event) => event.key === 'Escape' && onClose();
    document.body.classList.add('modal-open');
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.classList.remove('modal-open');
      document.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  return (
    <>
      <div
        className="modal fade in"
        id="unitModal"
        style={{ display: 'block' }}
        tabIndex="-1"
        role="dialog"
        aria-labelledby="unitModalLabel"
        onClick={(event) => event.target === event.currentTarget && onClose()}
      >
        <div className="modal-dialog modal-lg" role="document">
          <div className="modal-content">
            <div className="modal-header">
              <button type="button" className="close" aria-label="Close" onClick={onClose}>
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="unitModalLabel">{title}</h4>
            </div>
            <div className="modal-body">
              <div id="unitInfo">
                <ul className="list-group">
                  {visible.map((person, index) => (
                    <li className="list-group-item" key={index}>
                      <strong>نام و نام خانوادگی:</strong> {person.name}<br />
                      <strong>بیمارستان:</strong> {person.hospital}
                    </li>
                  ))}
                </ul>
              </div>
              <nav aria-label="Page navigation">
                <ul className="pagination" id="pagination">
                  {Array.from({ length: pages }, (_, index) => index + 1).map((number) => (
                    <li
                      key={number}
                      className={`page-item ${number === page ? 'active' : ''}`}
                      onClick={(event) => { event.preventDefault(); setPage(number); }}
                    >
                      <a className="page-link" href="#">{number}</a>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-default" onClick={onClose}>بستن</button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade in" />
    </>
  );
}
