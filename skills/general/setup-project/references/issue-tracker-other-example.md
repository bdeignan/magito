<!-- issue-tracker-other-example.md — a worked example of issue-tracker-other.md.template:
     one paragraph of user description in, one usable docs/agents/issue-tracker.md out. Read
     it when you are filling that template and want to see what "good" looks like, especially
     for the two operations this fictional team cannot perform.

     The tracker is invented and the `jira` CLI flags are NOT verified against the real tool.
     This example shows the shape of a filled-in adapter, never a command to copy. -->

# Worked example: a fictional Jira setup

## The paragraph the user gave (input)

> We track everything in Jira, project key `PLAT`, on the company cloud instance at
> `acme.atlassian.net`. I have the `jira` CLI installed and logged in. Tickets are Story,
> Task, or Bug; the states are To Do / In Progress / In Review / Done. Nobody uses Jira
> epics here — we just put `PLAT-123` in the branch name and the commit message. Jira has
> "blocks" links but half the team forgets them, so the real blocker list is a line in the
> description. Code review is GitHub PRs; Jira never sees the PR.

## The file produced (output → docs/agents/issue-tracker.md)

---

# Issue tracker: Jira (`PLAT` on acme.atlassian.net)

Work is tracked in Jira, project key `PLAT`, reached with the `jira` CLI (already
authenticated on this machine). Ticket types are Story, Task, and Bug; states are
`To Do`, `In Progress`, `In Review`, `Done`. Epics are not used here — don't create one.
Code review happens on GitHub pull requests, which Jira never sees.

Skills never name a backend. They name one of the operations below and read this file to
find out how to perform it here.

## Ticket identifiers

`PLAT-<number>`, e.g. `PLAT-123`. It appears in the branch name and in every commit
message, which is how `reviewing-changes` finds the spec behind a diff.

## List open tickets

```
jira issue list -p PLAT -s~Done --plain
```

## Fetch a ticket

```
jira issue view PLAT-<n> --comments 20
```

## Publish a ticket

```
jira issue create -p PLAT -t Task -s "<title>" -b "<body>"
```

Type is `Task` unless the user says Story or Bug.

## Comment on a ticket

```
jira issue comment add PLAT-<n> "<body>"
```

## Close a ticket

```
jira issue move PLAT-<n> Done
```

Jira has no auto-close from a merge — this is always a deliberate step.

## Link a sub-ticket

**Not supported here.** This team does not use epics or sub-tasks. When a breakdown needs a
parent spec, publish the spec as an ordinary ticket and put `Part of PLAT-<n>` on the first
line of each child's description.

## Blocking edges

Jira's "blocks" link type exists (`jira issue link PLAT-<a> PLAT-<b> Blocks`) but is applied
inconsistently, so **do not trust it as the source of truth**. The authoritative list is a
`Blocked by: PLAT-<n>, PLAT-<n>` line in the ticket description. Read that line; a ticket is
ready when every ticket it names is `Done`. Write both when you record a new edge.

## Pull requests

Jira is not the review surface. Work lands through GitHub pull requests, and PR creation
stays on `bash <skills>/implement/scripts/gitflow.sh pr <issue> <title>` — never through
this file.

---

## What this example is here to show

- **Every canonical heading is answerable from one paragraph.** If you find yourself unable
  to fill one, that is a question to ask the user, not a heading to delete.
- **The two operations this team cannot perform are the interesting part.** *Link a
  sub-ticket* gets **not supported here** plus the convention they use instead; *blocking
  edges* gets a stronger warning, because the Jira link type exists but is unreliable, and an
  adapter that stayed silent about that would send an agent to the wrong source of truth.
  Naming an operation's absence is what stops a skill improvising.
- **The tracker does not decide how work lands.** This team keeps tickets in Jira and still
  reviews on GitHub pull requests, so `implement` takes the PR path — it reads the remote, not
  this file (`docs/adr/0015`).
- **Identifiers travel.** `PLAT-123` in the branch and commit message is what lets
  `reviewing-changes` find the spec behind a diff without a hardcoded `#N`.
