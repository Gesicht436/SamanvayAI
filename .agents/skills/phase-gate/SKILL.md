---
name: phase-gate
description: Runs the acceptance gate for the current build phase, reports pass or fail for each check, and updates docs/PROGRESS.md. Use at the end of every phase, or when asked whether a phase is done, finished or accepted.
---

# Phase gate

Use this at the end of a build phase. Never start the next phase from here.

## Steps
1. Read `docs/PROGRESS.md` to find the current phase number.
2. Find that phase's row in `docs/spec/21.md` (or section 21 of `SPEC.md`). Copy its gate checks into a checklist.
3. Run `make check` first. If `make` is not available, stop and tell the user; do not improvise another command.
4. Run each phase-specific gate command or test listed in the row.
5. Report a table with one row per check: check, pass or fail, last lines of output.
6. If every check passes: update `docs/PROGRESS.md` (phase, what was built, open items, exact gate output) and suggest `git tag phase-<N>`.
7. If any check fails: fix the code and run the gate again. If it fails a second time, write the blocker to `docs/open-questions.md` and stop.

## Hard rules
- Never edit, skip, loosen or delete a test or a gate to make it pass.
- Never mark a phase accepted without the real command output.
- Do not begin the next phase.
