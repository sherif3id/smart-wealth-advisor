import { expect, test } from '@playwright/test';

test('authoritative persisted journey, honest ML state, RTL, and logout revocation', async ({ page, context }) => {
  const email = `playwright-${Date.now()}@example.com`;
  await page.goto('/');

  await expect(page.getByText('Choose your language')).toBeVisible();
  await page.getByText('Full English experience').click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');

  await page.getByRole('button', { name: 'Create account' }).click();
  await page.getByLabel('Name').fill('Playwright User');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill('StrongPass9!');
  await page.getByRole('button', { name: 'Register' }).click();

  await expect(page.getByText('First, tell us about yourself')).toBeVisible();
  await page.locator('input').nth(0).fill('Playwright User');
  await page.locator('input').nth(1).fill('35');
  await page.locator('select').nth(1).selectOption('EGP');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Open my dashboard' }).click();

  await expect(page.getByText('Authoritative data summary')).toBeVisible();
  await expect(page.getByText('EGP 35,000')).toBeVisible();

  const api = context.request;
  const summary = await api.get('/api/core/financial-summary');
  expect(summary.ok()).toBeTruthy();
  const initial = await summary.json();
  expect(Number(initial.total_income)).toBe(3000);
  expect(Number(initial.total_expenses)).toBe(1800);
  expect(Number(initial.net_worth)).toBe(35000);

  const transaction = await api.post('/api/core/transactions', {
    data: {
      kind: 'expense', amount: 125, currency: 'EGP',
      occurred_on: new Date().toISOString().slice(0, 10),
      description: 'Playwright persisted expense', category: 'Food',
    },
  });
  expect(transaction.status()).toBe(201);

  await page.getByRole('button', { name: 'Transactions', exact: true }).click();
  await expect(page.getByText('Playwright persisted expense')).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Transactions', exact: true }).click();
  await expect(page.getByText('Playwright persisted expense')).toBeVisible();

  await page.getByRole('button', { name: 'Insights', exact: true }).click();
  await expect(page.getByText('Synthetic demo model')).toBeVisible();
  await expect(page.getByText(/not real-world validation or production forecasts/)).toBeVisible();
  await expect(page.getByText('Next-month expenses')).toBeVisible();
  await expect(page.getByText(/Centroid distance—not confidence/)).toBeVisible();

  await page.getByRole('button', { name: 'Simulator', exact: true }).click();
  await expect(page.getByText('MONTE CARLO', { exact: true })).toBeVisible();
  await expect(page.getByText(/EGP 77,/).first()).toBeVisible();
  await expect(page.getByText(/Results are not guarantees/)).toBeVisible();

  const report = await api.post('/api/core/reports', { data: { kind: 'health', locale: 'en' } });
  expect(report.status()).toBe(201);
  const reportBody = await report.json();
  expect(reportBody.data.data_as_of).toBeTruthy();
  expect(reportBody.data.methodology.version).toBeTruthy();
  expect(reportBody.data.assumptions.length).toBeGreaterThan(0);

  await page.getByRole('button', { name: 'Reports', exact: true }).click();
  await expect(page.getByText('Recent snapshots stored in the database')).toBeVisible();

  await page.getByRole('button', { name: 'ع', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByText('لوحة التحكم', { exact: true })).toBeVisible();
  await expect(page.getByText('متوازن · خطة تعليمية')).toBeVisible();

  await page.getByRole('button', { name: 'تسجيل الخروج' }).click();
  await expect(page.getByText('مرحبًا بعودتك')).toBeVisible();
  const afterLogout = await api.get('/api/core/auth/me');
  expect(afterLogout.status()).toBe(401);
});
