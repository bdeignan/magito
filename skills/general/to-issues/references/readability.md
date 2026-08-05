# Readability standard

The human-facing parts of an issue, spec, or pull request must be understandable by a reader
who did not do the work and lacks the author's context. That is the whole aim. A teammate who
opens the issue a week later, or a reviewer who never saw the conversation, should learn what
it is for and why it matters from the prose alone.

This file is the one home for the summary-and-self-check standard. `to-issues` and
`implement`'s `pr-body.md` both apply it. The word-level rules it leans on — plain words over
technical ones, no stacked compound nouns, the AI-marker blocklist — have their canonical home
in `shared/SYSTEM-INSTRUCTIONS.md`. The self-check below names a few of them as checkpoints, but
that file stays authoritative: change a word-level rule there, not here.

## Apply it in stages, never as one block

Dumping every rule into a single instruction is what produces dense prose in the first place:
the writer tries to satisfy ten constraints at once and satisfies none. Apply it at three
separate moments instead.

1. **Template.** The output template already puts the summary first and the detail below.
   Draft into it, so the shape is built in rather than bolted on.
2. **Audience frame.** Hold one instruction while drafting the human-facing prose: *write for
   a capable reader who did not do this work and lacks your context.* This is the single
   strongest lever. It steers you off insider shorthand and off your own mental model.
3. **Self-check.** After the draft exists, run the six checks below over the prose. Fix every
   miss before publishing.

## Two audiences, scoped by section

An issue serves two readers, so scope the frame to the section:

- **Summary, problem, why** — full reader frame. Main point first, plain words, no file paths
  or symbols unless the point genuinely needs one.
- **What to build, acceptance criteria** — written for the weaker implementing agent: precise
  and complete, but still in plain words. Keep identifiers exact (`clock_in`,
  `PRAGMA foreign_keys`) and define them; never rename them to sound simpler.

## Fidelity wins

Simplifying may never drop a fact. Every number, name, condition, and qualifier survives with
its precision intact. "Exceeded 340ms in three of ten windows" must not soften to "sometimes
slow." "Only when X and Y both hold" must not flatten to "generally." The standard governs how
a fact is said, never whether it appears.

## The self-check

Six yes/no checks over the prose regions — never "is this clear?" Each is concrete.

1. **Main point first** — the summary's opening sentence says what this is and why it matters.
2. **One idea per paragraph** — each paragraph carries one idea and leads with it.
3. **Plain words** — no stacked compound nouns, no AI-marker word (see
   `shared/SYSTEM-INSTRUCTIONS.md`), the common word chosen over the technical synonym.
4. **Sentence length** — no sentence runs past about thirty words without a reason.
5. **Technical detail follows the prose** — symbols, paths, and code sit below the sentence
   that explains them, never inside the human summary.
6. **Every fact preserved** — every number, name, condition, and qualifier from the source
   survives intact.

## One example

The same issue summary, before and after. Both describe a real change: a cleanup step for
`install.py`, which leaves dead symlinks behind when a skill is renamed.

**Before** — fluent-looking, but a reader has to decode it, and it never says why it matters:

> Implement an idempotent managed-symlink reconciliation pass that performs orphan detection
> and removal for links whose source-of-truth targets no longer resolve.

**After** — main point first, plain words, the technical name kept but explained:

> When you rename a skill, `install.py` adds the new symlinks but leaves the old ones behind,
> pointing at files that no longer exist. The last two renames each left dead links that we
> cleared by hand. This adds a cleanup step so a reinstall clears them on its own. It matters
> because the next rename will repeat the mess unless this lands first.

The before fails checks 1, 3, and 5. The after passes all six, keeps every fact, and reads at
a grade-6 level (`readability.py`).
