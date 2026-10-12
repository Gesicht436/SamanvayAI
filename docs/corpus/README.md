# Synthetic Document Corpus (`docs/corpus/`)

This directory contains the synthetic document corpus for Stage 0 Document Intake.

---

## 1. Purpose

The files in this directory test the OCR ingestion pipeline and MTC extraction engine:
1. Provide realistic procurement and technical documents without proprietary leaks.
2. Contain exact ground-truth JSON sidecars for automated recall evaluation.
3. Test EN 10204 3.1 and 3.2 material test certificates across multiple steel grades.
4. Test purchase orders, inspection test plans, and bills of quantities.

---

## 2. Theory

Stage 0 processes multi-page PDF documents and images:
- **Optical Character Recognition:** PyMuPDF extracts digital text layers and layout bounding boxes.
- **Scanned Rasterization:** Pages without digital text rasterize at 300 DPI (`SCANNED_RASTER_300DPI`).
- **Confidence Gating:** Any page or line with mean confidence $< 0.85$ triggers Tier 2 review (Invariant S7).
- **MTC Conformance:** Chemical analysis must conform to verified standard limits before Tier 1 matching (Invariant S15).

---

## 3. Corpus Composition (20 Documents)

| Document Category | Count | Specifications & Standards |
|---|---|---|
| Material Test Certificates (`MTC`) | 8 | ASTM A105, A350 LF2, A182 F316L, F51 Duplex, A335 P11, P22, P91, High Alumina Refractory |
| Purchase Orders & GRNs (`PO_GRN`) | 6 | Gate Valves (API 600), ASME B16.5 Flanges, IBR Boiler Tubes, FRAS Belts, API 610 Pumps, OTR Tyres |
| Inspection & Test Plans (`ITP`) | 4 | API 598 Valve Testing, IBR Superheater Headers, Mill Work Rolls, SAE J517 Hydraulic Hoses |
| Bills of Quantities (`BOQ`) | 2 | Thermal Power BOP Piping Package, Mining Coal Handling Overhaul Package |

Each document has two files:
- `{id}.txt`: Raw text representation of the document.
- `{id}.json`: Ground-truth metadata, expected line count, and key chemical or mechanical properties.

---

## 4. Manual Testing Guide

Run the corpus generation and recall evaluation script:
```powershell
uv run python scripts/generate_synthetic_docs.py
# or
make corpus-eval
```

Verify that line recall across all 20 documents is $\ge 95\%$.

---

## 5. Connected Documentation

- [Document Services README](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/services/README.md)
- [MTC Evaluation Script](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/scripts/eval_mtc_docs.py)
- [Verification Register](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/verification.md)
- [Limitations Register](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/docs/limitations.md)
