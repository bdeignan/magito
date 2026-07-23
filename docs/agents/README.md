<!-- README.md — the docs/agents/ convention manifest. Read it ONCE to learn what belongs
     in this folder and why; you won't need it every session. Not auto-loaded. Tool-neutral:
     this folder stands alone without magito — remove magito and it degrades to a
     well-documented folder, not a broken one. -->

# docs/agents/ — the agent context layer

A version-controlled, tool-neutral home for the project context a coding agent can't cheaply
rederive from the code — plus a discipline that keeps it from rotting into a stale, lying
graveyard that agents trust and act on.

## The two-gate filter
Content earns a place here only if it passes **both** gates:
- **Gate A — non-rederivable:** a codebase-investigator agent can't reconstruct it cheaply
  from the code. Excludes structure (module maps, call graphs, feature→file). Includes
  intent, decisions, conventions, gotchas, domain vocabulary.
- **Gate B — stable:** it survives the next handful of PRs. A pure refactor — moves code,
  same intent — must not invalidate it.

This flips the default from "document the codebase" to "document only what the code can't
tell you and will stay true." Most candidates fail Gate A (that keeps the set small); Gate B
filters the rest (that keeps it honest).

## The auto-load bundle
INDEX + OVERVIEW + a small GLOSSARY load every session via a native `@docs/agents/INDEX.md`
import in `CLAUDE.md` (a prose pointer in `AGENTS.md` for tools without imports). Everything
else is pulled on demand through INDEX's routing table.

## The file set
| File | Job | Auto-loaded? | Created |
|---|---|---|---|
| `INDEX.md` | Routing table: area/task → which file to read. Holds the multi-context routing. | Yes | scaffolded |
| `OVERVIEW.md` | Intent only: purpose + deliberate approach + rejected alternatives. Half-page cap. | Yes | scaffolded (stub) |
| `GLOSSARY.md` | Domain vocabulary → non-obvious meaning; opinionated, with `_Avoid_` lists. | Yes, when small | scaffolded (header) |
| `README.md` | This manifest. | No | scaffolded |
| `CONVENTIONS.md` | Agreed patterns the code doesn't announce. | No (on-demand via INDEX) | lazy |
| `GOTCHAS.md` | Cross-cutting traps only (spanning 2+ areas). | No | lazy |
| `flows/<area>.md` | Per-area notes, only where how-it-works-here is genuinely non-obvious. | No | lazy |

**Scaffold vs grow:** setup creates only the first four. Everything else is pulled into
existence by real content, never pushed by an empty template — that's what stops the folder
rotting into empty files agents learn to distrust. It scales from two files in a personal
repo to dozens of flows in a team monorepo without that rot.

**Rejected** (each fails a gate or duplicates machinery you already have): `ARCHITECTURE.md`
(structure — orient live via a subagent), `MAP.md` (feature→file, a pure Gate-A failure),
`PATTERNS.md` (folds into `CONVENTIONS.md`), `baselines/` (those are your test suite's
pin-and-guard thresholds — they live with the tests), `reports/` (session output; promote a
durable finding to a gotcha or an ADR).

## Maintenance — keep it honest, not comprehensive
When a change touches an area, load that area's INDEX-routed docs and: fix anything the diff
now contradicts (stale), drop anything that fails the two gates (bloat), and remove any dead
reference — a path or symbol the doc names that no longer exists. Detection is diff-scoped
through INDEX, never a whole-folder re-audit. Add a term, gotcha, or convention the moment it
resolves; don't batch. The discipline is detection and visibility, not forced correction: a
review proves the docs were looked at, and fixing a flagged doc is a normal review finding,
discretionary like any other.
