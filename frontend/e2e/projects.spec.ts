import { test, expect } from "@playwright/test";

/**
 * E2E тесты для управления проектами BlockTest.
 *
 * Требования для запуска:
 * - Фронтенд запущен на http://localhost:5173
 * - Бэкенд запущен на http://localhost:8000
 * - В .env указаны BLOCKTEST_ADMIN_EMAIL, BLOCKTEST_ADMIN_PASSWORD
 */

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || process.env.BLOCKTEST_ADMIN_EMAIL || "admin@example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || process.env.BLOCKTEST_ADMIN_PASSWORD || "ChangeMeAdmin123!";
const PROJECT_NAME = `E2E Тест Проект ${Date.now()}`;
const PROJECT_DESCRIPTION = "Проект создан через E2E тест Playwright";


/** Утилита для входа в систему */
async function loginAsAdmin(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.locator('input[type="email"]').fill(ADMIN_EMAIL);
  await page.locator('input[type="password"]').fill(ADMIN_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL("**/", { timeout: 10000 });
}


test.describe("Управление проектами", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("Переход на страницу проектов с дашборда", async ({ page }) => {
    // Находим ссылку на проекты
    await page.locator('a[href="/projects"]').first().click();
    await page.waitForURL("**/projects", { timeout: 10000 });

    await expect(page.locator("h1")).toBeVisible();
  });

  test("Создание нового проекта", async ({ page }) => {
    await page.goto("/projects");

    // Заполняем форму создания проекта
    const nameInput = page.locator('input[placeholder="Введите название проекта"]').last();

    // Ищем форму создания - она обычно в первой секции
    const formSection = page.locator(".section-card").first();
    const nameField = formSection.locator("input").first();
    const descriptionField = formSection.locator("textarea, input").last();

    await nameField.fill(PROJECT_NAME);
    // Если есть поле описания, заполняем его тоже
    if (await descriptionField.isVisible()) {
      await descriptionField.fill(PROJECT_DESCRIPTION);
    }

    // Нажимаем кнопку создания
    await formSection.locator('button[type="submit"]').click();

    // Ожидаем, что проект появится в списке
    await expect(page.locator("text=" + PROJECT_NAME)).toBeVisible({ timeout: 10000 });
  });

  test("Поиск проектов по названию", async ({ page }) => {
    await page.goto("/projects");

    // Ожидаем загрузки страницы
    await expect(page.locator("h1")).toBeVisible({ timeout: 5000 });

    // Вводим поисковый запрос
    const searchInput = page.locator('input[placeholder="Введите название проекта"]').first();
    await searchInput.fill("BlockTest");

    // Ожидаем обновления результатов (debounce)
    await page.waitForTimeout(500);

    // Проверяем, что отображаются результаты поиска
    // (если есть проекты с таким именем, список не будет пустым)
    const projectsList = page.locator(".list-grid, .list-card");
    // Ожидаем либо карточки проектов, либо сообщение "нет проектов"
    await expect(
      page.locator(".list-card, .state-card")
    ).toBeVisible({ timeout: 10000 });
  });

  test("Навигация к деталям проекта", async ({ page }) => {
    await page.goto("/projects");

    await expect(page.locator("h1")).toBeVisible({ timeout: 5000 });

    // Если есть проекты, кликаем на первый
    const openButton = page.locator("text=Открыть").first();
    if (await openButton.isVisible({ timeout: 5000 })) {
      await openButton.click();

      // Проверяем, что URL изменился на страницу проекта
      await page.waitForURL("**/projects/*", { timeout: 10000 });
      await expect(page.locator("h1")).toBeVisible({ timeout: 5000 });
    }
  });

  test("Страница запусков доступна после входа", async ({ page }) => {
    await page.goto("/runs");

    await expect(page.locator("h1")).toBeVisible({ timeout: 10000 });
  });

  test("Дашборд отображает статистику", async ({ page }) => {
    // Уже на дашборде после beforeEach
    await expect(page.locator(".stats-grid")).toBeVisible({ timeout: 10000 });

    // Проверяем, что статистические карточки отображаются
    const statCards = page.locator(".stat-card");
    await expect(statCards.first()).toBeVisible({ timeout: 5000 });
  });
});
