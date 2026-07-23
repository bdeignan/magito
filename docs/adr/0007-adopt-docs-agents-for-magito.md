# Adopt `docs/agents/` for magito itself; the glossary stays deferred

magito ships the `docs/agents/` convention (issue #56) — a small, routed, self-describing
context layer gated by the two-gate filter: content belongs only if it is non-rederivable
from the code and stable across refactors. We now dogfood it here. magito's own
`docs/agents/` carries an `INDEX.md` router, an intent-only `OVERVIEW.md`, and the `README.md`
manifest, wired into `CLAUDE.md` through a native `@docs/agents/INDEX.md` import so the bundle
auto-loads every session. This revisits ADR 0001, which kept magito on a bare `CLAUDE.md`:
the OVERVIEW and INDEX add non-rederivable intent and routing that `CLAUDE.md`'s operational
detail doesn't carry, while `GLOSSARY.md` stays an empty header — 0001's deferral of the
vocabulary file still holds until a term is genuinely contested. The trade-off is one thin
extra layer to keep honest, governed by the same review-gate maintenance the convention
ships, in exchange for magito living under the convention it asks other repos to adopt.
