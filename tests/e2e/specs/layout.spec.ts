import { test, expect } from "@playwright/test";

test.describe("Responsive Layout Shell", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "admin@pyerp.com");
    await page.fill('[name="password"]', "admin123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/app/**");
  });

  test("desktop sidebar is visible at 1440px", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/app/dashboard");
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();
  });

  test("mobile hamburger opens sidebar overlay at 375px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/app/dashboard");
    const hamburger = page.locator('button[aria-label="Open menu"]');
    await hamburger.click();
    const sidebar = page.locator("aside").last();
    await expect(sidebar).toBeVisible();
  });

  test("header shows breadcrumb navigation", async ({ page }) => {
    await page.goto("/app/dashboard");
    const header = page.locator("header");
    await expect(header).toBeVisible();
  });

  test("company switcher dropdown is accessible", async ({ page }) => {
    await page.goto("/app/dashboard");
    const companyBtn = page.locator('button[aria-label="Switch company"]');
    await expect(companyBtn).toBeVisible();
  });

  test("no horizontal scroll at any viewport", async ({ page }) => {
    for (const width of [375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/app/dashboard");
      const scrollWidth = await page.evaluate(
        () => document.documentElement.scrollWidth
      );
      const windowWidth = await page.evaluate(() => window.innerWidth);
      expect(scrollWidth).toBeLessThanOrEqual(windowWidth);
    }
  });
});
