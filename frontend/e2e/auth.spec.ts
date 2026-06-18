import { test, expect } from "@playwright/test";

/**
 * E2E тесты аутентификации BlockTest.
 *
 * Требования для запуска:
 * - Фронтенд запущен на http://localhost:5173
 * - Бэкенд запущен на http://localhost:8000
 * - В .env указаны BLOCKTEST_ADMIN_EMAIL, BLOCKTEST_ADMIN_PASSWORD
 */

const TEST_USER_EMAIL = `e2e-auth-${Date.now()}@example.com`;
const TEST_USER_USERNAME = `e2e_auth_${Date.now()}`;
const TEST_USER_PASSWORD = "E2eTestPass123!";

// Учётные данные администратора из .env.example
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || process.env.BLOCKTEST_ADMIN_EMAIL || "admin@example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || process.env.BLOCKTEST_ADMIN_PASSWORD || "ChangeMeAdmin123!";


test.describe("Аутентификация", () => {
  test("Страница логина отображается корректно", async ({ page }) => {
    await page.goto("/login");

    // Проверяем наличие ключевых элементов
    await expect(page.locator(".eyebrow")).toContainText("BlockTest");
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test("Страница регистрации отображается корректно", async ({ page }) => {
    await page.goto("/register");

    await expect(page.locator(".eyebrow")).toContainText("BlockTest");
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test("Логин с неправильными данными показывает ошибку", async ({ page }) => {
    await page.goto("/login");

    await page.locator('input[type="email"]').fill("nonexistent@example.com");
    await page.locator('input[type="password"]').fill("wrongpassword123");
    await page.locator('button[type="submit"]').click();

    // Ожидаем появления ошибки
    await expect(page.locator(".state-card-error")).toBeVisible({ timeout: 5000 });
  });

  test("Успешная регистрация перенаправляет на страницу входа", async ({ page }) => {
    await page.goto("/register");

    await page.locator('input[type="email"]').fill(TEST_USER_EMAIL);
    await page.locator('input[placeholder="qa_user"]').fill(TEST_USER_USERNAME);
    await page.locator('input[type="password"]').fill(TEST_USER_PASSWORD);
    await page.locator('button[type="submit"]').click();

    // После регистрации пользователь перенаправляется на страницу входа с уведомлением
    await page.waitForURL("**/login", { timeout: 10000 });
    await expect(page.locator(".state-card")).toBeVisible({ timeout: 5000 });
  });

  test("Успешный вход администратора и переход на дашборд", async ({ page }) => {
    await page.goto("/login");

    await page.locator('input[type="email"]').fill(ADMIN_EMAIL);
    await page.locator('input[type="password"]').fill(ADMIN_PASSWORD);
    await page.locator('button[type="submit"]').click();

    // После входа перенаправляет на главную (Dashboard)
    await page.waitForURL("**/", { timeout: 10000 });

    // Проверяем, что дашборд загрузился
    await expect(page.locator("h1")).toBeVisible({ timeout: 10000 });
  });

  test("Навигация между страницами входа и регистрации", async ({ page }) => {
    await page.goto("/login");

    // Переход на страницу регистрации
    await page.locator('a[href="/register"]').click();
    await page.waitForURL("**/register");
    await expect(page.locator("h1")).toBeVisible();

    // Переход обратно на страницу входа
    await page.locator('a[href="/login"]').click();
    await page.waitForURL("**/login");
    await expect(page.locator("h1")).toBeVisible();
  });
});
