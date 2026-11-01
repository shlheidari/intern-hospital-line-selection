/** Client-side checks of the change-password form (the server validates again). */

/** Returns the message for each field ('' when fine) and whether the form may be sent. */
export function validatePassword(password, confirmation) {
  let passwordError = '';
  let confirmError = '';

  if (password.length < 8) {
    passwordError = 'رمز عبور باید حداقل ۸ کاراکتر باشد.';
  }
  if (!/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password)
      || !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    passwordError = 'رمز عبور باید شامل حروف بزرگ، حروف کوچک، عدد و نماد باشد.';
  }
  if (password !== confirmation) {
    confirmError = 'رمزهای عبور مطابقت ندارند.';
  }
  if (/[^\x00-\x7F]/.test(password)) {
    passwordError = 'رمز عبور نمی‌تواند شامل حروف غیرانگلیسی (مانند فارسی) باشد.';
  }
  return { passwordError, confirmError, valid: !passwordError && !confirmError };
}
