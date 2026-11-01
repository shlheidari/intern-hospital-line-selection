import { validatePassword } from './validate.js';

const form = document.getElementById('passwordForm');

form.addEventListener('submit', (event) => {
  const result = validatePassword(form.new_password1.value, form.new_password2.value);
  document.getElementById('passwordError').textContent = result.passwordError;
  document.getElementById('confirmError').textContent = result.confirmError;
  if (!result.valid) event.preventDefault();
});

// The close button of the flash messages (Bootstrap's data-dismiss="alert").
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-dismiss="alert"]');
  if (button) button.closest('.alert')?.remove();
});
