# System Limitations and Honest Disclosures

This document lists known scope limits, operational assumptions, and features marked as spec-only or roadmap.

---

## 1. Safety and Automation Limits

1. **Identity is Not Substitution:**
   - The platform never automatically upgrades or substitutes materials. A Class 300 valve is never automatically linked to a Class 150 valve.
   - Any substitution recommendation requires human steward and engineering sign-off.
2. **Never Autonomous Merger for Safety-Critical Items:**
   - Items in safety-critical subcategories require human validation by a Checker holding the domain tag.
3. **No Direct ERP Write-Back Execution:**
   - The system exports structured cross-reference feeds and staging tables (CSV, XLSX, JSON). It does not directly write to SAP or Oracle production databases.

---

## 2. Hardware and Performance Limits

1. **OCR and Document Parsing:**
   - High-accuracy OCR on degraded physical scans requires local OCR libraries (PaddleOCR/EasyOCR/Tesseract). In constrained CI environments, a deterministic Fake OCR provider is used for reproducible tests.
2. **Offline Mode:**
   - Full offline operation is supported after one-time downloads of base Docker containers and tokenizer models.
