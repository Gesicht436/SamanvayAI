---
name: ui-screen
description: Builds or changes a screen in the Next.js web app (standardizer, diff inspector, stewardship queue, document review, lots, health card, onboarding wizard). Use when asked to create a page, component, dashboard or UI screen.
---

# UI screens

Screen list and behaviour: `docs/spec/15.md` (or section 15 of `SPEC.md`).

## Steps
1. Read the screen's description and the API it calls. Use only the typed API client; never call endpoints ad hoc.
2. Implement loading, empty and error states for every data view.
3. Use server-side pagination for any list that can grow.
4. Make navigation role-aware. The organisation switcher has no default selection.
5. Show a visible "synthetic data" banner whenever demo data is displayed.
6. Show evidence beside extracted values: the evidence span, the flag, and the tier with its reason.
7. Add a Playwright test for the screen's main flow, then run `make test`.
8. Do not display numbers computed in the browser from hand-typed values; take them from the API.

## Hard rules
- Never hide a flag, a Tier 2 reason, or a safety refusal to make a screen look cleaner.
- Keep text strings in one place so a Hindi translation can be added later.
