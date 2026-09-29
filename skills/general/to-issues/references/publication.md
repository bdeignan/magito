# Publish once, and rerun safely

Every published ticket body carries one line that names the draft it came from:

```
Publication-ID: <NNNN>-<slug>/<draft-filename>
```

For example, `Publication-ID: 0003-to-issues/01-local-dates.md`. The line is the same on
every run of the same intent, so a rerun can find what an earlier run already published.
There is no other record to keep.

## Publish in dependency order

For each draft, blockers first:

1. **Look first.** Run the tracker's **find a published ticket** operation with the draft's
   `Publication-ID`.
   - One match: that ticket is already published. Use its identifier and go to step 3.
   - No match: go to step 2.
   - Several matches, or the lookup itself fails: stop and escalate. Never publish when you
     cannot tell whether the ticket exists.
2. **Publish.** Build the body from the draft. The text after `# ` on the first line is the
   title; remove that line from the body. Replace each draft file name under "Depends on"
   with the identifier of the published blocker. Add the `Spec review:` line and the
   `Publication-ID:` line at the end. Run **publish a ticket**. If the call fails, or you
   cannot tell whether it succeeded, return to step 1 for this draft before trying again.
3. **Link blockers.** Read the ticket's existing blockers, add only the missing ones with
   **blocking edges**, and read them back.

Once every ticket and blocker is confirmed, delete the drafts, `review-brief.md`, and the
empty `drafts/` folder.

## After an interruption

Run `to-issues` on the same intent again. If `drafts/` still holds numbered drafts, an
earlier run stopped partway: keep those drafts, skip drafting, and resume at the spec review.
Step 1 above then skips every ticket that already exists, so nothing is published twice.
