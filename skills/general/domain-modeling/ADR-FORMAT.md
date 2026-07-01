# ADR Format

ADRs live in `docs/adr/`, numbered `0001-slug.md`, `0002-slug.md`. Create the directory lazily, and scan it for the highest existing number before adding one.

## Template

```md
# {Short title of the decision}

{1–3 sentences: the context, what we decided, and why.}
```

An ADR can be a single paragraph. The value is recording *that* a decision was made and *why* — not filling out sections.

## Optional sections

Add only when they earn it: **Status** frontmatter (`proposed | accepted | superseded by ADR-NNNN`); **Considered options** when the rejected alternatives are worth remembering; **Consequences** when non-obvious downstream effects need calling out.

## When to offer one

All three must hold:

1. **Hard to reverse** — changing your mind later is costly.
2. **Surprising without context** — a future reader will wonder "why on earth this way?"
3. **A real trade-off** — genuine alternatives existed and you picked one for reasons.

Qualifying examples: architectural shape ("the feature store is the single source of truth"); a technology choice with lock-in (warehouse, orchestrator, experiment tracker); boundary/scope decisions; deliberate deviations from the obvious path ("manual SQL, not the ORM, because X"); and constraints invisible in the code ("must run fully offline for compliance").
