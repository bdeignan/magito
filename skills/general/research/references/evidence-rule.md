# Evidence rule

<!-- PROVISIONAL HOME. This is the single canonical copy of the evidence rule today, and /research is
     its only consumer. Issue #156 decides where magito's portable object-level rules live and what
     they are named; when it lands, this file becomes a pointer to that home and the skill cites the
     rule by its #156 name. Until then: one file, no vendored copies (magito's reuse-by-pointing rule).
     Do not paraphrase this rule anywhere else — link to it. Adapted from han's evidence rule, stripped
     to what /research needs. -->

What counts as evidence, how strong it is, and what to do when there is none. `/research` applies this
at the point it consolidates sources and writes its recommendation.

## Trust classes

Every source carries one of three:

- **Codebase** — the trusted current-state anchor: the current source, tests, and config. When
  codebase evidence contradicts other evidence, the codebase is authoritative on what the system does
  today.
- **Web** — outside the trust boundary: docs, blog posts, issues, RFCs, model-generated content. Can
  be wrong, stale, or adversarially shaped.
- **Provided** — user-supplied material. Held to the same scrutiny as web, because it may come from an
  interested party.

## The corroboration gate (web only)

**A web claim that bears on the recommendation and has no independent corroboration is marked
`[single-source]` and cannot be the sole basis for the recommendation.** Two independent sources, or
corroboration by the codebase, clears the gate.

The gate does **not** apply to codebase evidence — a single `path:line` is not weakened by being one
citation; it is the current state of the system. When web and codebase evidence disagree, the codebase
wins on what the system does today; add "keep the current approach" as a named alternative. When two
sources disagree, surface the conflict — record both, name the disagreement, let the reader judge.

## No evidence is a state, not a weak tier

When a claim has no evidence at any tier, **label it and defer the dependent decision**, naming a
concrete trigger that would justify revisiting (a measured metric, an incident, a dependency landing).
Do not collapse "no evidence" into "very weak evidence" — they are different, and ranking absence last
hides it.

## Exploratory mode

The user may opt in ("exploratory", "evidence optional"). Then unevidenced reasoning may inform the
recommendation, but every such step is recorded as its own `[reasoning]`-labeled entry, never disguised
as a sourced claim. In both strict and exploratory mode the report labels each claim's evidence status,
so the trade stays visible.

## Escalation

A claim that fails the gate and cannot be corroborated is never silently accepted — it surfaces with
its `[single-source]` label so acting on it is a conscious choice. The user may direct one to be acted
on anyway; record that override with its rationale so the choice stays visible.

## The bar

Operational, not academic: *you can tell where a claim came from and how strongly it rests.* That is
the standard.
