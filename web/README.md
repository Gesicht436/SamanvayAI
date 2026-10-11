# Web: Samanvay Core Frontend User Interface

This directory contains the Next.js web application for **Samanvay AI**. It provides human stewards, plant engineers, and CPSE procurement officials with explainable material standardization and governance tools.

---

## 1. Purpose and Theory

The web application exposes the core harmonization engine through transparent, explainable screens:

1. **Standardizer Screen (`/standardizer`):**
   - Ingests noisy, unstructured legacy material descriptions.
   - Normalizes text into clean tokens.
   - Extracts technical attributes with confidence scores and evidence spans.
   - Retrieves candidate golden masters gated by deterministic safety rules.

2. **Diff Inspector Screen (`/diff`):**
   - Explains the harmonization decision through an attribute-by-attribute side-by-side comparison matrix.
   - Uses strict color coding: Green (`EXACT`), Amber (`MISSING` or `UPGRADE`), Red (`MISMATCH`).
   - Prevents catastrophic plant substitutions by displaying clear Safety Refusal banners when HARD attributes mismatch (Invariants S1 and S4).

3. **Stewardship Governance Queue (`/queue`):**
   - Implements a Maker-Checker workflow.
   - Proposers cannot approve their own tasks ($Maker \ne Checker$).
   - Checkers must possess domain tags for safety-critical subcategories.
   - Every approval or rejection appends an immutable record to the SHA-256 audit log.

4. **Evaluation Gate & Parity Dashboard (`/eval`):**
   - Displays 3 baselines side-by-side: Cosine Similarity (67.6% error), Character Trigrams (55.9% error), and Samanvay (0.0% error; 95% Clopper-Pearson bound $\le 2.15\%$).
   - Reports release gate status and sector/organization parity breakdowns.

---

## 2. Invariants and Constraints

- **No Default Organisation:** Per specification Section 15.0, the organisation switcher starts with no default selection (`Select CPSE Organisation...`). The user must explicitly choose an active enterprise context.
- **Synthetic Data Banner:** A clear banner marks demonstration environments running synthetic clusters. No proprietary enterprise data is exposed.
- **Explainable Decisions:** The visual attribute comparison matrix remains the authoritative explanation of all decisions. The UI never hides flags, safety refusals, or reason codes.
- **Keyboard Navigation:** Stewards can triage tasks rapidly using standard shortcuts (`J` next, `K` previous, `A` approve, `R` reject).

---

## 3. Directory File Index

| File / Folder | Purpose |
|---|---|
| [`src/app/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/page.tsx) | Home portal and platform metrics overview. |
| [`src/app/standardizer/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/standardizer/page.tsx) | Material Standardizer and match engine screen. |
| [`src/app/diff/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/diff/page.tsx) | Dedicated Diff Inspector with preset engineering scenarios. |
| [`src/app/queue/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/queue/page.tsx) | Stewardship Governance task queue screen. |
| [`src/app/eval/page.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/eval/page.tsx) | Evaluation harness results, baselines, and parity tables. |
| [`src/app/layout.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/app/layout.tsx) | Root application layout with AuthProvider, Header, and DemoBanner. |
| [`src/components/common/Header.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/Header.tsx) | Navigation header with role switcher and organisation switcher. |
| [`src/components/common/DemoBanner.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/DemoBanner.tsx) | Visible synthetic data notification banner. |
| [`src/components/common/Badge.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/common/Badge.tsx) | Standard badge components for Tiers, Verdicts, Roles, and Statuses. |
| [`src/components/standardizer/ExtractedCard.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/standardizer/ExtractedCard.tsx) | Displays clean tokens and attribute cards with evidence hover highlighting. |
| [`src/components/standardizer/CandidateCard.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/standardizer/CandidateCard.tsx) | Displays ranked candidate masters with Tier badges and diff triggers. |
| [`src/components/diff/DiffInspector.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/diff/DiffInspector.tsx) | Side-by-side attribute comparator table and safety refusal banners. |
| [`src/components/queue/TaskQueue.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/components/queue/TaskQueue.tsx) | Paginated task queue with Maker-Checker validation and modals. |
| [`src/lib/api.ts`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/lib/api.ts) | Typed API client connecting to FastAPI backend with demo fallbacks. |
| [`src/lib/auth-context.tsx`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/lib/auth-context.tsx) | React Context managing user roles, domain tags, and organisation. |
| [`src/types/index.ts`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/src/types/index.ts) | Core TypeScript interfaces and type definitions. |
| [`tests/`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/tests) | Vitest unit and component tests (16 tests across 5 test suites). |
| [`e2e/screens.spec.ts`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/web/e2e/screens.spec.ts) | Playwright end-to-end integration tests for all primary screens. |

---

## 4. Manual Testing Instructions

Execute all commands from the `web` directory:

1. **Run Unit and Component Tests (Vitest):**
   ```bash
   npm test
   ```
   *Expected:* 16 tests pass across 5 test files.

2. **Run End-to-End Integration Tests (Playwright):**
   ```bash
   npx playwright test
   ```
   *Expected:* 4 tests pass across Desktop Chromium.

3. **Verify Type Checking and Production Build:**
   ```bash
   npm run build
   ```
   *Expected:* Build succeeds and prerenders static routes.

4. **Verify ESLint Rules:**
   ```bash
   npm run lint
   ```
   *Expected:* 0 errors, 0 warnings.

5. **Start Development Server:**
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` to interact with the user interface.

---

## 5. Cross-Links

- Master Specification: [specsheet.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md) (Sections 7.0, 15.0, 15.1)
- Implementation Plan: [implementation_plan.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/implementation_plan.md) (Module 8 / Phase 9)
- Match Router: [`api/routers/match.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/routers/match.py)
- Tasks Router: [`api/routers/tasks.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/routers/tasks.py)
- Stewardship Service: [`api/services/stewardship.py`](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/stewardship.py)
