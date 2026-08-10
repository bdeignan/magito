# Research report template

<!-- The fixed structure the /research skill renders every run. The section set never changes; only
     the depth of each section scales with the run's size. Keep this the single source of the
     structure — the skill body points here rather than restating it. -->

Render these sections in this order, top to bottom. Every section appears on every run. At `small`,
Results and Options carry only the decisive evidence, not the full landscape.

---

## Summary

Plain language, no jargon, no source IDs — the answer in brief, one phrase on how solid it is, and
the confidence rating on its own labeled line:

**Confidence: High | Medium | Low** — one clause on why.

A reader who stops here has the answer.

## Results

The findings in plain prose with minimal technical detail. Every claim cross-references the source
IDs it rests on (`A1`, `A3`). Mark a claim inline when it rests on a single web source
(`[single-source]`) or, in exploratory mode only, on unevidenced reasoning (`[reasoning]`).

## Options

_Only when the question has discrete alternatives. Omit the whole section for "how does X work"._

Indexed list (`O1`, `O2`, …). Each option steelmanned: the case for it, its trade-offs, the source
IDs it rests on, and its evidence status.

## Recommendation

The recommended option (reference its `O#`) and an explicit evidence basis — which parts rest on
corroborated evidence, which on a single source, and (exploratory only) which on reasoning. When the
evidence does not settle it, write **"no clear winner"** and name the criteria that would decide,
rather than forcing a pick.

## Validation

Numbered `V#` findings from the adversarial pass: attacks on the evidence, the way the options were
framed, the recommendation, and the integrity of the evidence-gathering. Note any adjustment made to
the recommendation in response, and the remaining risks.

## Sources

One indexed registry, one row per source. **The invariant: every `A#` cited anywhere above resolves
to a row here.**

| ID | Source | Link / location | Retrieved | Trust | Corroboration |
|----|--------|-----------------|-----------|-------|---------------|
| A1 | short title | URL, or `repo/path:line` | date (web only) | codebase / web / provided | corroborated / single-source / anchor |

Render as a compact table by default. Reserve a fuller prose summary for the sources the
recommendation actually rests on.
