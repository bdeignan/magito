# Publish once and resume after interruption

Keep one `publication.json` in the intent's private ticket directory. It records what the
tracker confirmed so a resumed run can finish without creating duplicate tickets.
Only one publisher can work on this directory at a time. Claim it by creating a
`publication.lock` directory before reading or changing publication state. An existing lock
stops the run; after an interruption, establish that the previous publisher has stopped
before removing its lock. Remove the lock when the run finishes or stops cleanly.

## Record the reviewed input

Before the first tracker write, compare the original input with the reviewed `input.md`
copy. A change requires fresh review. Save a JSON object with:

- `run_id`: a generated UUID, kept across retries;
- `input_sha256`: SHA-256 of the reviewed `input.md` copy;
- `adapter_path`, `adapter_sha256`, and `main_root`;
- `review`: reviewer name, family, round, complete verdicts, and evidence paths;
- `tickets`: one entry keyed by draft filename, holding `draft_sha256`, `publication_id`,
  `identifier` (initially null), `phase` (initially `ready`), and `edges_done` (initially false).

The publication identity is `<run_id>:<draft-filename>`. Hash the reviewed draft bytes
before adding publication metadata or converting dependency names. Keep those drafts
unchanged. Write each record update to a temporary sibling and replace `publication.json`
atomically. Keep snapshots and captured review output outside the protected worktree until
its content comparison passes.

On resume, validate this record and compare the current input, adapter, and retained draft
hashes. Missing or changed evidence stops publication. Re-review changed drafts as a complete
set before accepting new hashes. If any ticket was already published, reconcile its content
with the changed plan before proceeding; a new UUID is not a way to bypass that reconciliation.
Do not recreate missing reviewed drafts by guessing.

## Publish in dependency order

For each draft:

1. If it has an identifier, fetch that ticket and verify its publication identity and body.
   Compare against the expected reviewed body after dependency conversion and metadata.
   Tracker-managed dates, status, and comments can differ. Other changes require reconciliation.
2. If phase is `publishing` and the identifier is absent, use **find a published ticket**
   with its exact publication identity. One matching ticket recovers the identifier.
   Multiple matches, unavailable lookup, or an uncertain result stop the run. A zero result
   after an uncertain write also stops: delayed visibility is not proof the write failed.
   Retry only after establishing that the original operation did not create a ticket.
3. For a `ready` draft, build the outgoing body from the retained draft. Its first `# ` line
   supplies the title; remove that line from the body. Convert dependency filenames to the
   confirmed tracker identifiers. Add the review line and
   `Publication-ID: <publication_id>` to the body.
4. Persist phase `publishing` before **publish a ticket**. When it succeeds, persist the
   returned identifier and phase `published` immediately. If the call fails or its result
   is uncertain, keep phase `publishing`; resolve it through step 2 before another attempt.
5. Fetch the ticket and verify its identity and expected body. Read its existing blockers,
   add only missing edges with **blocking edges**, and read them back. Mark `edges_done`
   true only after confirmation. A resumed run repeats this readback even for a true flag.

Once every ticket and edge is confirmed, mark the record `complete: true` and hand off the
identifiers with the selected adapter and main root. Retain the record, reviewed drafts,
and review evidence for resume and audit. A later explicit cleanup can remove them after
implementation is complete. The local tracker's open-ticket glob excludes `drafts/`.
