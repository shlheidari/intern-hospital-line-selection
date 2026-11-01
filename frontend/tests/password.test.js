import test from 'node:test';
import assert from 'node:assert/strict';
import { validatePassword } from '../src/password/validate.js';

test('a strong matching password is accepted', () => {
  const result = validatePassword('Abcdef1!x', 'Abcdef1!x');
  assert.deepEqual(result, { passwordError: '', confirmError: '', valid: true });
});

test('too short / missing character classes', () => {
  assert.match(validatePassword('Ab1!', 'Ab1!').passwordError, /حداقل ۸ کاراکتر/);
  assert.match(validatePassword('abcdefgh1!', 'abcdefgh1!').passwordError, /بزرگ، حروف کوچک، عدد و نماد/);
  assert.equal(validatePassword('abcdefgh1!', 'abcdefgh1!').valid, false); // no capital
  assert.equal(validatePassword('ABCDEFGH1!', 'ABCDEFGH1!').valid, false); // no lower case
  assert.equal(validatePassword('Abcdefgh!!', 'Abcdefgh!!').valid, false); // no digit
  assert.equal(validatePassword('Abcdefgh12', 'Abcdefgh12').valid, false); // no symbol
});

test('mismatching confirmation', () => {
  const result = validatePassword('Abcdef1!x', 'Abcdef1!y');
  assert.equal(result.confirmError, 'رمزهای عبور مطابقت ندارند.');
  assert.equal(result.valid, false);
});

test('non-English characters are rejected', () => {
  const result = validatePassword('Abcdef1!ب', 'Abcdef1!ب');
  assert.match(result.passwordError, /غیرانگلیسی/);
  assert.equal(result.valid, false);
});
