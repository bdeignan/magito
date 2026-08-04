# The issue tracker is an adapter written in prose

Status: settles how skills reach a tracker. Narrows ADR 0012's "scripts are the enforcement
floor" — `issues.sh` stays the deterministic path for GitHub, but it is no longer what a
skill calls.

Skills used to name their backend. `catch-up` ran `issues.sh list`; `implement` branched in
prose between "GitHub mode" and "local mode"; `to-issues` did both. That has two costs, and
the second is the one that mattered.

The visible cost is that adding a backend means editing every skill. The real cost is that
some backends never get added at all. At work the realistic mix is GitHub, Jira sometimes,
and markdown files for ad-hoc work. Under the old design Jira needed new code in `issues.sh`
before any skill could touch it, so it stayed unsupported indefinitely — not because it was
hard, but because the price of the first step was a script change.

So the tracker becomes an adapter, and the adapter is prose. Skills name an **operation** —
list open tickets, fetch a ticket, publish a ticket, close a ticket, link a sub-ticket,
record a blocking edge. A single per-repo file, `docs/agents/issue-tracker.md`, says how each
operation is performed here. `/setup-project` writes that file from one of three templates:
GitHub, local markdown, or a skeleton the user fills from a paragraph describing whatever
they actually use.

The third template is the whole point. An unknown backend costs nothing — no new code, no new
script branch, no new case in a `case` statement. A user who describes their Jira workflow in
a paragraph gets a config doc a skill can follow that afternoon.

`issues.sh` is untouched. It is still the deterministic wrapper for GitHub, and the GitHub
template points at it — the script did not stop being the right way to talk to `gh`, it
stopped being the thing skills know about. Every operation in that template also lists the
plain `gh` command beside the wrapper, so the file still reads correctly on a machine with no
magito installed. That matters because `docs/agents/` is meant to degrade into a
well-documented folder, not a broken one.

**Pull request creation is carved out, and the carve-out is load-bearing.** It stays on
`gitflow.sh pr`, which `review-gate.py` recognizes by pattern-matching that literal command
string. Route PR creation through the adapter and every fan-out branch would open a pull
request without meeting the gate — a silent hole, discovered late if ever. The carve-out is
written into the GitHub template with that reason attached, because "why is `gh pr create`
missing from this file?" is exactly the tidy-up a later session performs helpfully.

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
