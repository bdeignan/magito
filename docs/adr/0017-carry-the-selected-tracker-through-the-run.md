# Carry the selected tracker through the run

Status: accepted, 2026-09-29. Amends ADR 0015 for intent-specific tracker overrides.

An intent can use a tracker different from the repo default. Passing only ticket identifiers
to the next skill loses that choice: the consumer reopens the default adapter and looks in
the wrong tracker. The run must carry the selected adapter and main worktree root together
with its ticket identifiers.

ADR 0015's operation boundary stays: adapters own backend commands. The default adapter is
still `docs/agents/issue-tracker.md`. Selection now has one canonical home in
`skills/general/setup-magito/references/tracker-selection.md`; workflow skills point there.
A different custom tracker requires a concrete adapter supplied by the user.

Publication keeps a private record with input hashes, review evidence, stable ticket
identities, returned identifiers, and dependency completion. Adapters expose lookup by
publication identity across all ticket states. An uncertain write stops until reconciled;
repeating a publish after a missing response is not safe. This provides recovery instructions,
not transactional guarantees across a tracker and local files.

The user approved these repairs to intent 0003 during review of PR #187. That approval also
replaces exact-text implementation criteria with behavioral criteria, adds review of coverage
across the complete ticket set, and retains reviewed drafts for recovery. The accepted intent
remains the historical record; these changes supersede its instruction to delete remote
tracker drafts immediately after publishing. PR creation remains on `gitflow.sh`.
