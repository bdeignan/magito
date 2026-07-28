# Pull-request body

A PR body is for the human reviewer and for anyone who reads it later. Write in Simple English, per the repo's voice standards. Do not write for the commit record.

## Right-sized structure

Match the structure to the size of the change. A trivial PR can be one or two sentences. Reach for headings only when the change is large enough or crosses enough concerns that a scan needs landmarks.

When headings help, use this light skeleton and skip any section that does not add clarity:

- **Why** — the problem or motivation. Lead with this.
- **What** — the change, in a line or two.
- **How it was verified** — tests run, throwaway checks, commands exercised.
- **Risks / follow-ups** — notable side effects or deferred work. Optional.

Example:

> **Why:** Issue #91 asked for one shared PR-body reference because the same guidance lived in two skills and the squash-merge framing was repo-dependent.
>
> **What:** Moved the guidance into `skills/general/implement-issue/references/pr-body.md` and pointed `implement-issue` and `dispatch` at it.
>
> **How it was verified:** `grep` found no repo-dependent merge framing in `skills/`; `python install.py --dry-run` completed cleanly.

## Closing issues

`gitflow.sh pr <issue>` appends `Closes #<issue>` automatically. Do not add that line to the body for the primary issue. Add `Closes #M` lines only for extra issues the same PR resolves.
