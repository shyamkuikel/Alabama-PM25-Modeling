# Verification

Repository preparation checks performed on 27 October 2026:

- Seven current-pipeline unit tests passed.
- A six-model CPU smoke run completed, including checkpoint round-trip checks; its eleven result-audit checks passed. These smoke outputs were kept separate from the supplied full-study results.
- Eleven independent saved-result audit checks passed for three chronological validation folds and 887 common evaluation cases. The checks include input hashes, training-only preprocessing, fold separation, seed averaging and recomputed metrics.
- The repository README reports the supplied full-study results; these have not been replaced by a short verification run.
- Markdown relative links were checked against repository files.

The saved full training experiment is historical. A short CPU smoke run checks execution only and does not independently reproduce the full published result tables. Repeating the full study uses the commands in the main README.

Model-selection uncertainty, previously inspected evaluation months, one-year coverage, shared weather observations and incomplete source provenance remain scientific limitations. Passing software checks does not remove them.
