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

Every published ticket carries a `Publication-ID:` line naming its intent and draft file,
and adapters expose **find a published ticket** by that line across all ticket states.
`to-issues` looks before it publishes, so a rerun after an interruption skips tickets that
already exist. A failed or ambiguous lookup stops the run rather than risk a duplicate. No
other publication record is kept: a lock, run IDs, and hashes were tried during review of
PR #187 and dropped, since they only recorded state that the lookup already recovers.

The user approved these repairs to intent 0003 during review of PR #187. That approval also
replaces exact-text implementation criteria with behavioral criteria, adds review of coverage
across the complete ticket set, and keeps reviewed drafts until every ticket is published,
so a rerun can resume. The accepted intent remains the historical record; these changes
supersede its instruction to delete remote tracker drafts immediately after publishing. PR creation remains on `gitflow.sh`.
