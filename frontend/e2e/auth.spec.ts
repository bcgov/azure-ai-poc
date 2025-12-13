import { expect, test } from '@playwright/test'

// Auth E2E tests are intentionally opt-in because real Entra sign-in often
// requires interactive MFA/conditional access and can be flaky in CI.
//
// To enable the redirect smoke test locally:
//   $Env:E2E_ENABLE_AUTH_REDIRECT_TEST='true'
//   npm run test:e2e   (or your Playwright command)

test.describe.parallel('Auth (Entra/MSAL)', () => {
  test('login button triggers redirect to Microsoft sign-in', async ({ page }) => {
    test.skip(
      process.env.E2E_ENABLE_AUTH_REDIRECT_TEST !== 'true',
      'Set E2E_ENABLE_AUTH_REDIRECT_TEST=true to enable this redirect smoke test',
    )

    await page.goto('/')

    const loginButton = page.getByRole('button', { name: /^login$/i })
    await expect(loginButton).toBeVisible()

    await Promise.all([
      page.waitForURL(
        /microsoftonline\.com\/.*authorize|login\.microsoftonline\.com\/.*authorize|oauth2\/v2\.0\/authorize/i,
        { timeout: 30_000 },
      ),
      loginButton.click(),
    ])
  })
})
