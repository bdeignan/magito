# The issue tracker is an adapter written in prose

Status: settles how skills reach a tracker. Leaves ADR 0012's enforcement tiers intact —
tracker access was never a gated rule — but relies on them to explain the one carve-out
below. `issues.sh` stays the deterministic path for GitHub; it is simply no longer the thing
skills know about.

Skills used to name their backend. `catch-up` ran `issues.sh list`; `implement` branched in
prose between "GitHub mode" and "local mode"; `to-issues` did both. That has two costs, and
the second is the one that mattered.

The visible cost is that adding a backend means editing every skill. The real cost is that
some backends never get added at all. At work the realistic mix is GitHub, Jira sometimes,
and markdown files for ad-hoc work. Under the old design Jira needed new code in `issues.sh`
before any skill could touch it, so it stayed unsupported indefinitely — not because it was
hard, but because the price of the first step was a script change.

So the tracker becomes an adapter, and the adapter is prose. Skills name an **operation** —
list open tickets, fetch a ticket, publish a ticket, and the rest. A single per-repo file,
`docs/agents/issue-tracker.md`, says how each operation is performed here. The operation names
themselves have one home — `setup-magito/references/issue-tracker-other.md.template`, whose
headings every tracker doc must carry — so this record deliberately does not list them. `/setup-magito` writes that file from one of three templates:
GitHub, local markdown, or a skeleton the user fills from a paragraph describing whatever
they actually use.

The third template is the whole point. An unknown backend costs no code at all: the user
describes it and the description *is* the adapter. Someone who writes a paragraph about their
Jira workflow gets a config doc a skill can follow that afternoon.

`issues.sh` is untouched. It is still the deterministic wrapper for GitHub, and the GitHub
template points at it — the script did not stop being the right way to talk to `gh`, it
stopped being the thing skills know about. Every operation in that template also lists the
plain `gh` command beside the wrapper, so the file still reads correctly on a machine with no
magito installed. That matters because `docs/agents/` is meant to degrade into a
well-documented folder, not a broken one.

**Pull request creation is carved out, and this is its canonical reason.** It stays on
`gitflow.sh pr`, and the adapter never mentions a PR command.

The reason is ADR 0012's tiers, not the hook. `gitflow.sh pr` calls `require_review_decision`
before it does anything — a tier-2 check, in a script, running in every tool on every machine
with nothing to opt into. `review-gate.py` does also recognize a raw `gh pr create`, so the
hole is not total; but that is tier-3 insurance, present only in Claude Code and only where
`magito.reviewGate` is set. An adapter that told an agent to run `gh pr create` would trade
the check that always runs for the one that usually doesn't, and would do it silently, in a
config file nobody re-reads.

The carve-out is therefore written into every tracker template, pointing here, because "why
is `gh pr create` missing from this file?" is exactly the tidy-up a later session performs
helpfully.

Fixing this exposed a second thing the old binary got wrong. `implement`'s final step branched
on the tracker to decide whether to open a PR — but that is a question about the repo's host,
not its tracker. A team can keep tickets in Jira and still land every change through a GitHub
pull request. The step now branches on whether there is a remote to open a PR against.

## Accepted costs

**Prose adapters are not verified.** `issues.sh` fails loudly on a missing argument. A
paragraph describing Jira can be wrong, or go stale when the workflow changes, and nothing
catches it — the agent just does the wrong thing confidently. This is the same trade the
`docs/agents/` folder already makes everywhere else, and the same maintenance discipline
applies: fix it when a diff contradicts it.

**Three templates share one set of headings, with nothing enforcing it.** The headings are a
schema: a skill asking for "fetch a ticket" finds nothing if a template renamed it.
`issue-tracker-other.md.template` is declared canonical and the other two must follow it, but
that is a comment in a file, not a check. It is tier 1 in ADR 0012's terms — the tier that
fails.

**Every tracker touch now costs a file read.** A skill that used to run one command reads a
config doc first. Small, paid every session, and the honest price of not hardcoding.

**An operation nobody can perform must say so.** The skeleton tells the user to write **not
supported here** rather than delete the heading. A missing section reads as an oversight and
invites an agent to improvise; an explicit refusal tells it to stop. Whether people actually
fill it in that way is untested.
