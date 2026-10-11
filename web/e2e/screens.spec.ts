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

  test("Dashboard screen displays catalog health and 14 clusters table", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: /Executive Catalog Health & Inter-CPSE Dashboard/ })
    ).toBeVisible();
    await expect(page.getByText(/Item Completeness/)).toBeVisible();
    await expect(page.getByText(/88.4%/)).toBeVisible();
    await expect(page.getByText(/Audit Chain:/)).toBeVisible();
    await expect(page.getByText(/Motors 55 kW 4P B3 Ex d IIB T4 IE3/)).toBeVisible();
  });

  test("OEM wizard screen displays draft proposals and supersessions", async ({ page }) => {
    await page.goto("/oem");
    await expect(
      page.getByRole("heading", { name: /Bulk OEM Spares Ingestion & Supersession Mapping/ })
    ).toBeVisible();
    await expect(page.getByRole("cell", { name: "OLD-PUMP-01", exact: true })).toBeVisible();
    await expect(page.getByText("NEWPUMP02")).toBeVisible();
  });

  test("Lots screen renders stock lots and FEFO ladder", async ({ page }) => {
    await page.goto("/lots");
    await expect(
      page.getByRole("heading", { name: /Lot-Level Physical Life & FEFO Disposition Ladder/ })
    ).toBeVisible();
    await expect(page.getByText(/FEFO Disposition Ladder Hierarchy/)).toBeVisible();
  });

  test("Docs screen renders MTC evaluation and precheck", async ({ page }) => {
    await page.goto("/docs");
    await expect(
      page.getByRole("heading", { name: /Document Ingestion & Material Test Certificate/ })
    ).toBeVisible();
    await expect(page.getByText(/Calculated CE_IIW:/)).toBeVisible();
  });

  test("Spare Locator screen renders distance matrix and masked holdings", async ({ page }) => {
    await page.goto("/locator");
    await expect(
      page.getByRole("heading", { name: /Geographic Spare Inventory & Surplus Locator/ })
    ).toBeVisible();
    await expect(page.getByText(/Section 9.3 Masked Identity/)).toBeVisible();
    await expect(page.getByRole("button", { name: "All India" })).toBeVisible();
  });

  test("Procurement Hub screen renders Stream A transfers and Stream B pools", async ({ page }) => {
    await page.goto("/procurement");
    await expect(
      page.getByRole("heading", { name: /Inter-CPSE Surplus Transfer & Joint Demand Pooling Hub/ })
    ).toBeVisible();
    await expect(page.getByText(/Stream A: Surplus Redeployment Transfers/)).toBeVisible();
    await expect(page.getByText(/Stream B: Forward Demand Pooling & Tender Packs/)).toBeVisible();
  });
});

