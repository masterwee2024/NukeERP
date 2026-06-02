import { test, expect } from "@playwright/test";

test.describe("Dynamic Menu System", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "admin@pyerp.com");
    await page.fill('[name="password"]', "admin123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/app/**");
  });

  test("sidebar renders menu items from API", async ({ page }) => {
    await page.waitForSelector("nav");
    const menuItems = page.locator("nav a, nav button");
    await expect(menuItems.first()).toBeVisible();
  });

  test("clicking a menu item navigates to correct route", async ({ page }) => {
    const dashboardLink = page.locator("a").filter({ hasText: "Dashboard" });
    await dashboardLink.click();
    await expect(page).toHaveURL(/\/app\/dashboard/);
  });

  test("menu groups expand on click", async ({ page }) => {
    const group = page.locator("button, a").filter({ hasText: /financial|scm|crm|hrm/i });
    await group.first().click();
    await expect(page.locator("a, button")).toHaveCount(0);
  });
});
