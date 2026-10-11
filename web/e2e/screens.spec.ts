import { test, expect } from "@playwright/test";

test.describe("Samanvay AI Frontend Screens E2E", () => {
  test("Organisation switcher initializes with no default selection", async ({ page }) => {
    await page.goto("/");
    const select = page.getByLabel("Select CPSE Organisation");
    await expect(select).toBeVisible();
    await expect(select).toHaveValue("");

    // Select OIL-1
    await select.selectOption("OIL-1");
    await expect(page.getByText("Active Enterprise:")).toBeVisible();
    await expect(page.getByText("Indian Oil & Gas Corporation")).toBeVisible();
  });

  test("Standardizer screen matches input and inspects diff", async ({ page }) => {
    await page.goto("/standardizer");
    await expect(
      page.getByRole("heading", { name: "Material Standardizer & Match Engine" })
    ).toBeVisible();

    // Trigger match
    await page.getByRole("button", { name: "Standardize & Match" }).click();

    // Verify subcategory and candidate card
    await expect(page.getByText("VALVES.GATE", { exact: true })).toBeVisible();
    await expect(page.getByText("MPNG-0004821937-3")).toBeVisible();
    await expect(page.getByText("Tier 2: Steward Review").first()).toBeVisible();

    // Inspect Diff
    const inspectBtn = page.getByRole("button", { name: "Inspect Diff Matrix" }).first();
    await inspectBtn.click();

    await expect(page.getByRole("heading", { name: /Diff Inspector/ })).toBeVisible();
    await expect(page.getByText("Explains the decision")).toBeVisible();
  });

  test("Diff Inspector screen renders verdict badges and safety refusal banners", async ({ page }) => {
    await page.goto("/diff");
    await expect(
      page.getByRole("heading", { name: /Diff Inspector & Safety Verdict Matrix/ })
    ).toBeVisible();

    // Case 1: Amber banner for missing required attributes
    await expect(page.getByText(/SAFETY ROUTING: Required Attribute Gap/)).toBeVisible();
    await expect(page.getByText("MISSING", { exact: true }).first()).toBeVisible();

    // Switch to Case 2: Hard pressure mismatch
    await page.getByRole("button", { name: /Case 2/ }).click();
    await expect(page.getByText(/SAFETY REFUSAL: Hard Attribute Mismatch Detected/)).toBeVisible();
    await expect(page.getByText("MISMATCH", { exact: true })).toBeVisible();
  });

  test("Stewardship Queue screen displays paginated tasks and filters", async ({ page }) => {
    await page.goto("/queue");
    await expect(
      page.getByRole("heading", { name: "Stewardship Governance Queue" })
    ).toBeVisible();
    await expect(page.getByText(/Total Tasks:/)).toBeVisible();

    // Filter by Approved
    const statusFilter = page.getByLabel("Filter Tasks by Status");
    await statusFilter.selectOption("APPROVED");
    await expect(page.getByText("POWER.TRANSFORMER")).toBeVisible();
  });
});
