---
trigger: glob
globs: "api/services/compare.py, api/services/tiering.py, api/services/scoring.py, tests/**"
description: "Safety invariants S1 to S14 for matching and tiering."
---
Never relax, skip or delete an invariant test. Read docs/spec/06.md before editing matching, tiering or scoring code.
A failing invariant means the code is wrong; if the requirement seems wrong, write it to docs/open-questions.md and stop.
