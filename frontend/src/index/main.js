// Login / change-password dialogs of the start page.
const overlays = [...document.querySelectorAll('.modal-overlay')];

function open(id) {
  for (const overlay of overlays) overlay.classList.toggle('is-open', overlay.id === id);
}

function close(overlay) {
  overlay.classList.remove('is-open');
}

document.addEventListener('click', (event) => {
  const opener = event.target.closest('[data-open-modal]');
  if (opener) {
    open(opener.dataset.openModal);
    return;
  }
  if (event.target.closest('[data-close-modal]')) {
    close(event.target.closest('.modal-overlay'));
    return;
  }
  if (event.target.classList.contains('modal-overlay')) close(event.target); // click on the backdrop
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') overlays.forEach(close);
});
