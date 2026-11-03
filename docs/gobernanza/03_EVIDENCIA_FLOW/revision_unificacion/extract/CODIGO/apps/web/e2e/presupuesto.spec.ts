import { expect, test } from "@playwright/test";

test("el lote muestra su presupuesto y permite fijar el techo", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await page.getByRole("navigation").getByRole("link", { name: /^Lotes/ }).click();
  await expect(page).toHaveURL(/\/lotes/);

  // Se crea un lote de prueba para tener un detalle con presupuesto.
  await page.getByRole("button", { name: "5", exact: true }).first().click();
  const botones = page.getByRole("button", { name: "Añadir" });
  for (let i = 0; i < 5; i++) {
    await botones.first().click();
    await page.waitForTimeout(150);
  }
  await page.getByRole("button", { name: /Crear lote/ }).click();
  await expect(page.getByText(/Presupuesto del lote/)).toBeVisible({ timeout: 20_000 });

  // Fijar un techo y comprobar que se refleja.
  await page.getByLabel("Techo de presupuesto del lote en euros").fill("1.50");
  await page.getByRole("button", { name: "Fijar techo" }).click();
  await expect(page.getByText(/1\.50 €/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/disponibles de/)).toBeVisible();
});
