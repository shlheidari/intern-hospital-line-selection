import { expect, test } from '@playwright/test';

const STUDENT = '990000001';
const PASSWORD = 'demo-pass-123';
const NONE = 'هیچ کدام';

/** Fails a test on any browser console error or uncaught exception. */
function watchErrors(page) {
  const problems = [];
  page.on('console', (message) => message.type() === 'error' && problems.push(message.text()));
  page.on('pageerror', (error) => problems.push(error.message));
  return problems;
}

const board = (page) => page.locator('#sheet0');
const cellLabelled = (page, label) =>
  page.locator('td[id]:visible', { has: page.locator(':scope > div > div > span', { hasText: new RegExp(`^${label}$`) }) }).first();

test('a student chooses a line and hospitals and submits', async ({ page }) => {
  const problems = watchErrors(page);
  const dialogs = [];
  page.on('dialog', (dialog) => { dialogs.push(dialog.message()); dialog.accept(); });

  await page.goto('/');
  await page.click('.btn-success');
  await page.fill('#logi input[name=username]', STUDENT);
  await page.fill('#logi input[name=password]', PASSWORD);
  await page.click('button.lbutton');

  // the board stays empty until a line is chosen
  await expect(page.locator('#select_line select')).toBeVisible();
  await expect(board(page).locator('td[id]:visible')).toHaveCount(0);
  await expect(page.locator('#line_detail')).toBeVisible();

  await page.selectOption('#select_line select', '1A');
  await expect(page.locator('#line_detail')).toBeHidden();
  await expect(board(page).locator('td[id]:visible')).not.toHaveCount(0);

  // surgery: the list starts with "none", then the hospitals with free seats
  const surgery = cellLabelled(page, 'جراحی');
  await surgery.locator(':scope > div > div > span').first().click();
  const options = surgery.locator('table.stylet td');
  await expect(options.first()).toHaveText(NONE);
  const hospital = (await options.nth(1).textContent()).trim();
  await options.nth(1).click();
  await expect(surgery.locator(':scope > div > div > div > span')).toHaveText(hospital);

  // a specialty can be taken once across the three electives
  const first = cellLabelled(page, 'الکتیو-اول');
  await first.locator(':scope > div > div > span').first().click();
  const pick = first.locator('table.stylet td').nth(1);
  const elective = (await pick.textContent()).trim();
  await pick.click();
  await expect(first.locator(':scope > div > div > div > span')).toHaveText(elective);

  const second = cellLabelled(page, 'الکتیو-دوم');
  await second.locator(':scope > div > div > span').first().click();
  const specialty = elective.split(' ')[0];
  for (const text of await second.locator('table.stylet td').allTextContents()) {
    expect(text.trim() === NONE || !text.includes(specialty), text).toBe(true);
  }

  // submitting: the server warns about missing units, then asks to confirm
  await page.click('#button button');
  await expect(page).toHaveURL(/\/line\/$|\/$/);
  await expect(page.locator('.alert')).toContainText('انتخاب های شما با موفقیت ثبت شد');
  expect(dialogs[0]).toContain('موارد الزامی زیر انتخاب نشده اند');
  expect(dialogs[1]).toContain(`جراحی: ${hospital}`);
  expect(problems).toEqual([]);
});

test('the capacity board opens the list of students of a unit', async ({ page }) => {
  const problems = watchErrors(page);
  await page.goto('/capacity/');
  await expect(board(page).locator('td[id]')).not.toHaveCount(0);
  await board(page).locator('td[id="37"]').click();
  await expect(page.locator('#unitModalLabel')).toContainText('جراحی-1A');
  await page.keyboard.press('Escape');
  await expect(page.locator('#unitModal')).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('the members list can be searched and sorted', async ({ page }) => {
  const problems = watchErrors(page);
  await page.goto('/member/');
  const names = () => page.locator('#dtBasicExample tbody tr:visible td:nth-child(2)').allTextContents();
  expect(await names()).toHaveLength(3);

  await page.fill('#searchInput', 'student 2');
  expect(await names()).toEqual(['Demo Student 2']);
  await page.fill('#searchInput', '');

  await page.locator('th.sortable').nth(1).click(); // ascending
  await page.locator('th.sortable').nth(1).click(); // descending
  expect((await names())[0]).toBe('Demo Student 3');
  expect(problems).toEqual([]);
});

test('the change-password form validates before sending', async ({ page }) => {
  const problems = watchErrors(page);
  await page.goto('/');
  await page.click('.btn-warning');
  await page.fill('#chan input[name=username]', '990000002');
  await page.fill('#chan input[name=password]', PASSWORD);
  await page.click('button.cbutton');

  await page.fill('#id_old_password', PASSWORD);
  await page.fill('#id_new_password1', 'abc');
  await page.fill('#id_new_password2', 'abd');
  await page.click('#passwordForm button[type=submit]');
  await expect(page.locator('#passwordError')).not.toBeEmpty();
  await expect(page.locator('#confirmError')).toHaveText('رمزهای عبور مطابقت ندارند.');
  expect(problems).toEqual([]);
});
