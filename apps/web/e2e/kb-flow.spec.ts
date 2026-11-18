import { test, expect } from "@playwright/test";

test("upload → ready → ask with citation", async ({ page }) => {
  await page.goto("/kb");
  await page.setInputFiles("input[type=file]", "e2e/fixtures/sample.md");
  const row = page
    .getByTestId("doc-row")
    .filter({ hasText: "sample.md" })
    .first();
  await expect(row.getByText("ready")).toBeVisible({ timeout: 90_000 });

  await page.goto("/");
  await page.getByPlaceholder("输入问题").fill("WorkPilot 的吉祥物叫什么？");
  await page.getByRole("button", { name: "发送" }).click();
  await expect(page.getByTestId("citation-chip").first()).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("Pilo").first()).toBeVisible();
});
