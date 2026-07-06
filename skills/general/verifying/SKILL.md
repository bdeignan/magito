---
name: verifying
description: Disciplined testing for Python work — find the real seam, default to red-green for behavior you can specify up front and pin-and-guard (characterization, eval thresholds, smoke) for exploratory analysis, and always add invariant and schema checks at data boundaries. Use when adding tests, implementing a feature or fix that needs verification, working with dataframes, pipelines, or models, or when asked to test, verify, or harden code.
---

# Verifying

Close the loop with a *real* test at a *real* seam. A test earns its place by failing when the behavior breaks — not by turning green. The dominant failure mode is a test that passes but doesn't catch: the seam under test is mocked away, or the assertion is on implementation details. Mock only at process boundaries (network, clock, filesystem); never mock the thing you're verifying.

## 1. Find the seam

Test at the highest, fewest seams possible — ideally one pure function over data. Prefer an existing seam to a new one. A function that takes data and returns data is the easiest thing to verify; reach for that shape before reaching for mocks.

## 2. Pick the mode

Ask one question: **is the correct behavior specifiable in advance?**

- **Yes → red-green** (most work). Write the test first and watch it go *red* for the right reason. Implement the minimum to make it *green*. Refactor under green. The red step is the proof the test can fail — never skip it.
- **No → pin-and-guard** (exploratory analysis, modeling, EDA). You can't assert an answer you don't yet know, so guard the behavior instead:
  - **Characterization** — pin current output (a golden file / saved fixture) so a refactor can't silently drift it.
  - **Eval harness** — assert a metric stays within a threshold (`accuracy >= 0.8`, `rmse <= x`), not an exact value.
  - **Smoke** — the pipeline runs end-to-end on a tiny fixture and produces output of the right shape.

## 3. Always: invariants and schema at the data seam

Independent of mode, guard the data boundaries — this is the default layer, not an afterthought:

- **Schema** — columns, dtypes, nullability at every dataframe / IO boundary.
- **No silent corruption** — no NaN/inf where forbidden; values in range; categories in the allowed set.
- **Structural truths** — shape, row counts, keys unique, group probabilities sum to 1, monotonic where required.
- **No leakage** — the train/test split is clean; no target or future information in features.

Plain `pytest` asserts are the zero-dependency floor and always available. Reach for `pandera`/`pydantic` (schema) or `hypothesis` (properties) on heavier cases — but read the project's declared stack first, and don't add a dependency without asking.

## 4. Handle nondeterminism

Seed everything (`random`, `numpy`, the framework). Assert with tolerance (`np.allclose`, `pytest.approx`), not equality, on floats. Use saved golden files for large structured outputs.

## Done when

Every new seam has a test that fails for the right reason, the invariant layer guards the data boundaries it crosses, and the full suite passes once at the end. A green suite with no red step ever proven is not done.
