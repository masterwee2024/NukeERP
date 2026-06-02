import { test, expect } from "@playwright/test";

test.describe("Confirm Dialog", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "admin@pyerp.com");
    await page.fill('[name="password"]', "admin123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/app/**");
  });

  test("dialog appears on danger action", async ({ page }) => {
    await page.goto("/app");
    const dangerBtn = page.locator("button").filter({ hasText: /delete|remove/i });
    if (await dangerBtn.count() > 0) {
      await dangerBtn.first().click();
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();
    }
  });

  test("Escape key closes dialog", async ({ page }) => {
    await page.goto("/app");
    const dangerBtn = page.locator("button").filter({ hasText: /delete|remove/i });
    if (await dangerBtn.count() > 0) {
      await dangerBtn.first().click();
      await page.keyboard.press("Escape");
      await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    }
  });

  test("Enter key confirms dialog", async ({ page }) => {
    await page.goto("/app");
    const dangerBtn = page.locator("button").filter({ hasText: /delete|remove/i });
    if (await dangerBtn.count() > 0) {
      await dangerBtn.first().click();
      await page.keyboard.press("Enter");
      await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    }
  });

  test("backdrop click cancels dialog", async ({ page }) => {
    await page.goto("/app");
    const dangerBtn = page.locator("button").filter({ hasText: /delete|remove/i });
    if (await dangerBtn.count() > 0) {
      await dangerBtn.first().click();
      const backdrop = page.locator(".bg-black\\/50");
      await backdrop.click({ position: { x: 1, y: 1 } });
      await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    }
  });

  test("has accessible dialog attributes", async ({ page }) => {
    await page.goto("/app");
    const dangerBtn = page.locator("button").filter({ hasText: /delete|remove/i });
    if (await dangerBtn.count() > 0) {
      await dangerBtn.first().click();
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toHaveAttribute("aria-modal", "true");
    }
  });
});
