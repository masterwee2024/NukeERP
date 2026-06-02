import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("login with valid credentials redirects to dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "admin@pyerp.com");
    await page.fill('[name="password"]', "admin123");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/app\//);
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "wrong@email.com");
    await page.fill('[name="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    await expect(page.locator("text=Login failed")).toBeVisible();
  });

  test("forgot password link navigates to reset page", async ({ page }) => {
    await page.goto("/login");
    await page.click("text=Forgot Password");
    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test("register link navigates to register page", async ({ page }) => {
    await page.goto("/login");
    await page.click("text=Register");
    await expect(page).toHaveURL(/\/register/);
  });

  test("unauthenticated user redirected to login", async ({ page }) => {
    await page.goto("/app/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});
