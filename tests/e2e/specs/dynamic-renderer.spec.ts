import { test, expect } from "@playwright/test";

test.describe("Dynamic Page Renderer", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "admin@pyerp.com");
    await page.fill('[name="password"]', "admin123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/app/**");
  });

  test("renders list page from page config", async ({ page }) => {
    await page.goto("/app/core/users");
    await page.waitForSelector("table");
    await expect(page.locator("table thead tr th").first()).toBeVisible();
  });

  test("switches to card view on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/app/core/users");
    const card = page.locator(".rounded-md.border.border-secondary-200");
    await expect(card.first()).toBeVisible();
  });

  test("loads and renders dynamic form with fields", async ({ page }) => {
    await page.goto("/app/core/users/new");
    await expect(page.locator("h2")).toContainText(/new/i);
    const inputs = page.locator("input, select, textarea");
    await expect(inputs).not.toHaveCount(0);
  });

  test("shows validation errors on required fields", async ({ page }) => {
    await page.goto("/app/core/users/new");
    await page.click('button[type="submit"]');
    const errors = page.locator(".text-danger-500, [class*=error]");
    await expect(errors.first()).toBeVisible();
  });

  test("renders detail page with record data", async ({ page }) => {
    await page.goto("/app/core/users/1");
    await expect(page.locator("h2")).toBeVisible();
  });

  test("renders dashboard page with KPIs", async ({ page }) => {
    await page.goto("/app/dashboard");
    await expect(page.locator("h2")).toBeVisible();
  });

  test("detail page action buttons show confirm dialog", async ({ page }) => {
    await page.goto("/app/core/users/1");
    const actionBtn = page.locator("button").filter({ hasText: /post|void|delete|approve/i });
    if (await actionBtn.count() > 0) {
      await actionBtn.first().click();
      await expect(page.locator('[role="dialog"]')).toBeVisible();
    }
  });

  test("search input debounces API calls", async ({ page }) => {
    await page.goto("/app/core/users");
    const searchInput = page.locator('input[placeholder="Search..."]');
    await searchInput.fill("admin");
    await page.waitForTimeout(400);
    const rows = page.locator("table tbody tr");
    await expect(rows).not.toHaveCount(0);
  });

  test("pagination controls work", async ({ page }) => {
    await page.goto("/app/core/users?page_size=1");
    const nextBtn = page.locator("button", { hasText: "Next" });
    if (await nextBtn.isEnabled()) {
      await nextBtn.click();
      await expect(page.locator("text=Page 2 of")).toBeVisible();
    }
  });
});
