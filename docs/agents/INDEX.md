<!-- INDEX.md — the router for docs/agents/: "working on X → read Y." Auto-loaded every
     session (imported from CLAUDE.md), so keep it a ROUTER, not a knowledge base: one line
     per destination, never content that belongs in the target file. Add a row when you add
     a doc here; delete the row when you delete the doc. New to this folder? Read README.md
     once — it explains what belongs here and why. -->

# magito — agent docs index

What is this folder and what belongs in it? See [README.md](./README.md) — read once.

## Auto-loaded every session
Loaded via the `@docs/agents/INDEX.md` import in `CLAUDE.md`:
- [OVERVIEW.md](./OVERVIEW.md) — why magito exists and the deliberate approach behind it.
- [GLOSSARY.md](./GLOSSARY.md) — project vocabulary (deferred; see the file).

## Routing — working on X → read Y
| Working on / question | Read |
|---|---|
| Why magito is built this way | [OVERVIEW.md](./OVERVIEW.md) |
| Install, symlink layout, where files map to each tool | `CLAUDE.md` — "Installing" and "Repo Layout" |
| Machine-local config (`~/.magito/`: ledger, bench, workers, `bin/`) | `CLAUDE.md` — "Machine-Local Config" |
| The session ledger (clock in/out, checkpoints, schema) | `bin/clock`, `bin/ledger.md` |
| Skill, hook, and agent design conventions | `CLAUDE.md` — "Skill and Agent Design Notes" |
| Delegating a build (shell workers, worktrees) | `skills/general/implement-issue/references/worker-contract.md` |
| The magi tribunal | `skills/claude/magi/SKILL.md` |
| Why a past decision was made | `docs/adr/` |

magito is a single-context repo, so there is no multi-context routing table here.
