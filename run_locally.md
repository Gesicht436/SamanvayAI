# How to Run and Verify Samanvay Locally

This document describes how to start and test the Samanvay Material Master Harmonization Platform on your local machine.

---

## 1. Prerequisites

Verify that the following tools are available on your system:

| Tool | Minimum Version | Verification Command | Notes |
|---|---|---|---|
| **Python** | 3.12+ | `uv run python --version` | Managed via Astral `uv` |
| **Astral uv** | 0.4+ | `uv --version` | High-speed package manager |
| **Node.js** | 18+ (20+ recommended) | `node -v` | Required for Next.js web application |
| **Docker & Docker Compose** | 24+ | `docker --version` | Runs PostgreSQL 18 with `pgvector` |
| **Git** | 2.40+ | `git --version` | Version control |

---

## 2. One-Click Launch (Windows)

For Windows systems, use the configured batch script:

1. Double-click `run_locally.bat` or run it from a command prompt:
   ```cmd
   .\run_locally.bat
   ```
2. The script executes the following sequence:
   - Verifies system prerequisites (`uv`, `node`, `docker`).
   - Starts the `samanvay_db` container on port `5432`.
   - Runs database migrations (`uv run alembic upgrade head`).
   - Seeds reference material clusters and savings baselines (`uv run python -m scripts.seed_clusters`).
   - Opens the FastAPI server in a dedicated window on port `8000`.
   - Opens the Next.js frontend in a dedicated window on port `3000`.
   - Opens `http://localhost:3000` in your default browser.
3. To stop all running servers, run `stop_locally.bat` or close the opened terminal windows.

---

## 3. Manual Startup (Multi-Terminal / Linux / macOS)

If you prefer to start each service manually, open two terminal windows.

### Terminal 1: Database & Backend API

1. Start the PostgreSQL container:
   ```bash
   docker compose up -d db
   ```
2. Apply database migrations:
   ```bash
   uv run alembic upgrade head
   ```
3. Seed the reference clusters:
   ```bash
   uv run python -m scripts.seed_clusters
   ```
4. Start the FastAPI backend server:
   ```bash
   uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Terminal 2: Frontend Web UI

1. Navigate to the web directory and install dependencies if not already done:
   ```bash
   cd web
   npm install
   ```
2. Start the Next.js development server:
   ```bash
   npm run dev
   ```
3. Open your browser to [http://localhost:3000](http://localhost:3000).

---

## 4. Port and URL Reference

| Service | Address | Description |
|---|---|---|
| **Web Frontend** | `http://localhost:3000` | Full 14-screen Next.js user interface |
| **Backend REST API** | `http://localhost:8000` | FastAPI root |
| **Interactive API Docs** | `http://localhost:8000/docs` | Swagger UI with direct endpoint testing |
| **Alternative API Docs** | `http://localhost:8000/redoc` | OpenAPI ReDoc specification |
| **System Health** | `http://localhost:8000/health` | Service status, clock mode, and ML toggle |
| **System Metrics** | `http://localhost:8000/metrics` | In-memory latency and counter metrics |
| **PostgreSQL Database** | `localhost:5432` | `samanvay` database with `pgvector` |

---

## 5. Feature Checkout Guide

Inspect each module using the steps below to confirm that every system operates correctly.

### Feature 1: Interactive Web Portal
- Open [http://localhost:3000](http://localhost:3000).
- Check the navigation bar for all key views:
  - **Standardizer** (`/standardizer`): Enter raw messy material strings to see instant canonicalization and check digit generation.
  - **Stewardship Queue** (`/queue`): View Tier 2 materials requiring human steward sign-off.
  - **Cross-CPSE Locator** (`/locator`): Search inventory across ONGC, BHEL, and IOCL.
  - **MTC Inspector** (`/docs`): Review scanned Mill Test Certificates with side-by-side OCR highlight bounding boxes.
  - **Lots & Life Monitor** (`/lots`): Inspect shelf-life countdowns, storage degradation alerts, and quarantine actions.
  - **Procurement Pools** (`/procurement`): Examine demand aggregation across CPSEs and projected bulk discounts.
  - **OEM Onboarding** (`/oem`): Inspect vendor catalog ingestion and part number cross-references.
  - **Diff Inspector** (`/diff`): View character-level attribute comparison between candidate items.
  - **Catalog Health** (`/eval`): View live binomial confidence intervals and release gate scores.

### Feature 2: High-Speed Deduplication Engine (Cold Start)
- Run the cold-start deduplication script on 5,000 synthetic material descriptions:
  ```bash
  uv run python scripts/cold_start_dedup.py --count 5000
  ```
- **Expected Result:** Processes 5,000 items in less than 1 second with 99%+ deduplication accuracy.

### Feature 3: Subvector Embedding Precision (Hard Negative Rejection)
- Demonstrate why naive single-cosine embeddings fail on critical engineering parameters while domain subvectors succeed:
  ```bash
  uv run python scripts/demo_embedding_limitation.py
  ```
- **Expected Result:**
  - Standard single cosine score gives high false similarity on mismatched pressure ratings (e.g., Class 150 vs Class 600).
  - Samanvay PT subvector detects rating divergence and blocks unsafe merge ($S1$ invariant).

### Feature 4: Tamper-Evident Hash Chain Audit Trail
- Verify the mathematical cryptographic integrity of all audit records in PostgreSQL:
  ```bash
  uv run python -m api.core.hashchain_verify
  ```
- **Expected Result:** Reports all log records verified with `0 errors`. Every row is linked by SHA-256 hash chains ($S12$ invariant).

### Feature 5: Safety Invariants Release Gate
- Run the formal release gate evaluation:
  ```bash
  uv run python scripts/eval_harness.py
  ```
- **Expected Result:**
  - Evaluates 170 hard negative test pairs across 14 equipment categories.
  - Confirms `0 false merges` (Safety Invariant $S1$).
  - Clopper-Pearson exact binomial confidence interval reported.
  - `Release Gate: PASS`.

---

## 6. Automated Test Suites

Execute the comprehensive test suites to verify backend safety and frontend rendering:

### Backend Unit & Invariant Tests
```bash
uv run pytest
```
- **Result:** 216 tests passing across 34 test suites in ~10 seconds.
- Covers invariants $S1$ to $S15$, OCR fallbacks, ERP dual commits, Verhoeff check digits, and life monitors.

### Code Style and Formatting
```bash
uv run ruff check .
```
- **Result:** All checks pass with 0 lint errors.

### Frontend Component Tests (Vitest)
```bash
cd web && npm test -- --run
```
- **Result:** 22 unit tests passing across 7 component suites.

### Frontend End-to-End Tests (Playwright)
```bash
cd web && npm run test:e2e
```
- **Result:** 10 browser tests passing.

---

## 7. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `FATAL: password authentication failed for user "postgres"` | Database credentials mismatch in `.env`. | Verify `.env` contains `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/samanvay`. |
| `docker compose up -d db` fails | Docker daemon is not running. | Start Docker Desktop or execute `sudo systemctl start docker`. |
| `alembic upgrade head` reports connection refused | PostgreSQL container is still starting. | Wait 5 seconds for health check to complete, then retry. |
| `port 8000 is already in use` | A previous uvicorn instance is active. | Run `stop_locally.bat` or terminate the process listening on port 8000: `netstat -ano \| findstr 8000`. |
| `port 3000 is already in use` | Another Next.js or React dev server is active. | Terminate existing Node process or start Next.js on port 3001: `npm run dev -- -p 3001`. |
| `ModuleNotFoundError: No module named 'uvicorn'` | Uvicorn dependency missing from environment. | Run `uv sync` to update the virtual environment. |

---

## 8. Summary of Core Safety Invariants

- **S1 (No False Merges):** Candidate items with mismatched sizes, pressure ratings, or metallurgy can never merge automatically into Tier 1.
- **S2 (Fail Closed):** Ambiguous or unparsed attributes automatically route to Tier 2 human review.
- **S5 (Low-Confidence OCR):** Scanned certificates with OCR confidence below 70% are blocked from Tier 1.
- **S12 (Tamper-Evident Audit):** All catalog changes are committed with cryptographically chained SHA-256 hashes in the same database transaction.
