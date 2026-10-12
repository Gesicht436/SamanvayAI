# Web: Samanvay Core Frontend User Interface

This directory contains the Next.js web application for **Samanvay AI**. It provides human stewards, plant engineers, and CPSE procurement officials with explainable material standardization and governance tools.

The interface implements the **Precision Industrial Elegance** design system. It combines Apple typography and micro-interactions, Microsoft Fluent command bars, LinkedIn activity feeds, and Amazon/AWS faceted inspection tables.

---

## 1. Purpose and Theory

The web application exposes the core harmonization engine through transparent, explainable screens:

1. **Standardizer Screen ([`src/app/standardizer/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/standardizer/page.tsx)):**
   - Ingests noisy, unstructured legacy material descriptions.
   - Normalizes text into clean tokens.
   - Extracts technical attributes with confidence scores and evidence spans.
   - Retrieves candidate golden masters gated by deterministic safety rules.

2. **Diff Inspector Screen ([`src/app/diff/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/diff/page.tsx)):**
   - Explains the harmonization decision through an attribute-by-attribute side-by-side comparison matrix.
   - Features SVG lattice connectors between raw character spans and golden master fields.
   - Uses strict color coding: Green (`EXACT`), Amber (`MISSING` or `UPGRADE`), Red (`MISMATCH`).
   - Prevents catastrophic plant substitutions by displaying clear Safety Refusal banners when HARD attributes mismatch (Invariants S1 and S4).
   - Includes optional TreeSHAP local attribution panel with governance safety notices.

3. **Stewardship Governance Queue ([`src/app/queue/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/queue/page.tsx)):**
   - Implements a Maker-Checker workflow.
   - Proposers cannot approve their own tasks ($Maker \ne Checker$).
   - Checkers must possess domain tags for safety-critical subcategories.
   - Every approval or rejection appends an immutable record to the SHA-256 audit log.

4. **Master Golden Catalogue Browser ([`src/app/catalogue/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/catalogue/page.tsx)):**
   - Authoritative browser for national material codes (Verhoeff MPNG-17).
   - Features AWS-style faceted filter drawer by Sector Pack and Lifecycle Status.
   - Supports 3 table row densities: Compact (30px), Standard (38px), and Comfortable (48px).
   - Enables Maker-initiated Merge, Split, and Lifecycle status stewardship modals.

5. **Batch Tabular Ingestion & Column Mapping ([`src/app/upload/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/upload/page.tsx)):**
   - Ingests legacy ERP extracts via drag-and-drop CSV dropzone.
   - Pre-configured mapping profiles for SAP MARA/MAKT, Oracle Cloud ERP, and IBM Maximo.
   - Validates required columns and displays row-by-row error preview table.

6. **Document Intake & OCR Canvas ([`src/app/docs/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/docs/page.tsx)):**
   - Side-by-side 300 DPI page image canvas with bounding box overlays.
   - Color-coded OCR confidence thresholds (green $\ge 0.85$, amber $< 0.85$).
   - Live camera capture interface (`getUserMedia`) with video preview modal.
   - MTC chemistry bounds validation and Section 10.2 statutory pre-check.

7. **Lots and Life Monitor ([`src/app/lots/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/lots/page.tsx)):**
   - Simulated CPSE system clock stepper banner (`clock_mode == "simulated"`).
   - Visual SVG burn-down usage chart projecting consumption velocity and depletion date.
   - Alert acknowledgment action (`POST /alerts/{id}/ack`) and scrap condemnation certificate modal.

8. **Inter-CPSE Spare Locator ([`src/app/locator/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/locator/page.tsx)):**
   - Haversine distance calculator with 1.25x road winding multiplier.
   - Section 9.3 privacy masking: conceals plant identity until formal inter-CPSE transfer request.
   - Direct initiation of Stream A surplus transfer workflows.

9. **Spend Pooling & Procurement Streams ([`src/app/procurement/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/procurement/page.tsx)):**
   - Stream A surplus transfer orders with 6-stage Maker-Checker review gate.
   - Stream B forward demand pooling for joint buyer tender packs.
   - Exports structured tender packs (JSON) and Bill of Quantities (CSV).

10. **Executive Dashboard ([`src/app/dashboard/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/dashboard/page.tsx)):**
    - Executive scorecards for Catalog Completeness, Deduplication, and Audit Chain.
    - Queue depth bar charts grouped by domain.
    - Section 19.2 spend pooling financial scenarios across 14 validated clusters.
    - Section 12.0 ERP cross-reference export preview for SAP, Oracle, and Maximo.

11. **OEM Onboarding Wizard ([`src/app/oem/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/oem/page.tsx)):**
    - Bulk OEM catalogue onboarding with supersession chain detection.
    - Maker proposal reviews and Checker batch authorization gate.

12. **Evaluation Gate & Parity Dashboard ([`src/app/eval/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/eval/page.tsx)):**
    - Displays 3 baselines side-by-side: Cosine Similarity (67.6% error), Character Trigrams (55.9% error), and Samanvay (0.0% error; 95% Clopper-Pearson bound $\le 2.15\%$).
    - Reports exact binomial release gates and sector/organization parity breakdowns.

---

## 2. Invariants and Constraints

- **No Default Organisation:** Per specification Section 15.0, the organisation switcher starts with no default selection (`Select CPSE Organisation...`). The user must explicitly choose an active enterprise context.
- **Dual-Theme Support:** Every screen and component supports both Clean Light Mode and Obsidian Dark Mode via Tailwind CSS v4 `@custom-variant dark (&:where(.dark, .dark *));`. Theme preference persists in `localStorage`.
- **Global Command Palette (`Cmd+K`):** Global spotlight search provides instant keyboard navigation to all 12 routes and sample `MPNG-` codes.
- **Audit Hash Chain Drawer:** Slide-out drawer verifies SHA-256 tamper-evident integrity without page reloads.
- **Explainable Decisions:** The visual attribute comparison matrix remains the authoritative explanation of all decisions. The UI never hides flags, safety refusals, or reason codes.
- **Keyboard Navigation:** Stewards triage tasks rapidly using standard shortcuts (`J` next, `K` previous, `A` approve, `R` reject).

---

## 3. Directory File Index

| File / Folder | Purpose |
|---|---|
| [`src/app/layout.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/layout.tsx) | Root application layout with ThemeProvider, AuthProvider, Header, CommandPalette, and AuditDrawer. |
| [`src/app/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/page.tsx) | Home portal and platform metrics overview. |
| [`src/app/standardizer/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/standardizer/page.tsx) | Material Standardizer and match engine screen. |
| [`src/app/diff/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/diff/page.tsx) | Dedicated Diff Inspector with preset engineering scenarios. |
| [`src/app/queue/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/queue/page.tsx) | Stewardship Governance task queue screen. |
| [`src/app/catalogue/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/catalogue/page.tsx) | Master Golden Catalogue browser with faceted filters and merge/split modals. |
| [`src/app/upload/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/upload/page.tsx) | Batch tabular upload and ERP profile mapping screen. |
| [`src/app/docs/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/docs/page.tsx) | Document intake, 300 DPI canvas, camera capture, and MTC validator. |
| [`src/app/lots/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/lots/page.tsx) | Lots and life monitor with burn-down chart and alert acknowledgments. |
| [`src/app/locator/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/locator/page.tsx) | Surplus spare locator with privacy masking and transfer modal. |
| [`src/app/procurement/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/procurement/page.tsx) | Stream A transfer orders and Stream B joint demand pooling. |
| [`src/app/dashboard/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/dashboard/page.tsx) | Executive health scorecards, clusters spend pooling, and ERP export feeds. |
| [`src/app/oem/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/oem/page.tsx) | OEM onboarding wizard with supersession chain mapping. |
| [`src/app/eval/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/eval/page.tsx) | Evaluation harness results, baselines, and parity tables. |
| [`src/components/common/Header.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/Header.tsx) | Top navigation header with categorized menus, tenant switcher, role selector, and theme toggle. |
| [`src/components/common/CommandPalette.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/CommandPalette.tsx) | Spotlight search modal for quick keyboard route and master navigation. |
| [`src/components/common/AuditDrawer.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/AuditDrawer.tsx) | Slide-out drawer displaying SHA-256 hash chain health. |
| [`src/components/common/FacetedFilterDrawer.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/FacetedFilterDrawer.tsx) | AWS-style collapsible faceted filter drawer with record counts. |
| [`src/components/common/DensityToggle.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/DensityToggle.tsx) | Table row density controller (compact, standard, comfortable). |
| [`src/components/common/SafetyBanner.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/SafetyBanner.tsx) | Standardized safety callouts citing Safety Invariants S1–S15. |
| [`src/components/common/Badge.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/Badge.tsx) | Dual-theme semantic badges for Tiers, Verdicts, Roles, and Statuses. |
| [`src/lib/theme-context.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/lib/theme-context.tsx) | ThemeProvider managing dark, light, and system color modes. |
| [`src/lib/auth-context.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/lib/auth-context.tsx) | React Context managing user roles, domain tags, and CPSE tenants. |
| [`src/lib/api.ts`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/lib/api.ts) | Typed API client connecting to FastAPI backend with mock fallbacks. |
| [`tests/`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/tests) | Vitest unit and component tests (26 tests across 8 test suites). |
| [`e2e/screens.spec.ts`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/e2e/screens.spec.ts) | Playwright end-to-end integration tests for all primary screens. |

---

## 4. Manual Testing Instructions

Execute all commands from the `web` directory:

1. **Run Unit and Component Tests (Vitest):**
   ```bash
   npm test
   ```
   *Expected:* 26 tests pass across 8 test files.

2. **Verify Type Checking and Production Build:**
   ```bash
   npm run build
   ```
   *Expected:* Build succeeds and prerenders all 14 routes.

3. **Verify ESLint Rules:**
   ```bash
   npm run lint
   ```
   *Expected:* 0 errors, 0 warnings.

4. **Start Development Server:**
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` to interact with the user interface.

---

## 5. Cross-Links

- Master Specification: [specsheet.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md) (Sections 7.0, 15.0, 15.1, 15.2, 20.1, 20.2)
- Frontend Overhaul Plan: [frontend_overhaul_plan.md](file:///C:/Users/mayank/.gemini/antigravity-cli/brain/60d4bd18-7da9-4b24-8a94-c4f190c57ade/frontend_overhaul_plan.md)
- Match Router: [`api/routers/match.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/routers/match.py)
- Tasks Router: [`api/routers/tasks.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/routers/tasks.py)
- Ingest Router: [`api/routers/ingest.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/routers/ingest.py)
- Stewardship Service: [`api/services/stewardship.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/stewardship.py)
