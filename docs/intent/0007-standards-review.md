# Where the Standards review belongs

Status: accepted · Opened: 2026-10-04 · Accepted: 2026-10-05

## Problem

`reviewing-changes` reviews a diff along two separate axes. Spec asks whether the change does
what its ticket asked. Standards asks whether it follows the repo's documented rules: the
ADRs, `docs/agents/CONVENTIONS.md`, the glossary, and docs the diff makes stale.

Since intent 0005, `implement` no longer runs `reviewing-changes`. Each branch it builds gets
one review from another model family, and the rules in `worker-contract.md` aim that review
at the ticket's goal. So the pipeline checks Spec, and nothing in it checks Standards. The
Standards axis survives only in a skill run by hand.

Evidence so far:

- **Caught:** the hand review of PR #187 flagged backend selection inside a skill and the
  generic use of "issues", both against the glossary. Neither was a Spec defect.
- **Missed by the pipeline:** PR #224 (intent 0005) took `reviewing-changes` out of
  `implement`, but `CONVENTIONS.md` kept saying the skill "fires inside build" until PR #240.
  A stale-doc check is the Standards axis's job, and no pipeline review had it.
- **Missed by the Standards axis:** dense jargon copied into `writing-for-agents` passed both
  axes, because it broke no written rule. A human caught it.
- **Mechanical rules are already enforced:** `scripts/check.sh` runs `anti-slop.py` on every
  tracked Markdown file, plus the install, hook, and invocation checks. A review never needs
  to repeat those.

## Proposed outcome

Every review `implement` runs checks two things in one reply: whether the change does what
its ticket asked, and whether it follows the repo's written rules. A script picks the
standards docs and finds the doc lines a change may have made untrue, so every reviewer, strong
or weak, gets the same closed inputs and follows the same numbered steps. `reviewing-changes`
runs the same procedure by hand on work done outside `implement`.

## Decisions so far

1. **The Standards check joins `implement`'s review.** It is one more part of the brief the
   same reviewer already gets: no second reviewer and no extra round. It carries a
   materiality bar like Spec's: a finding blocks only when the diff breaks a written rule,
   or leaves a doc saying something the diff made untrue. Everything else is a NOTE.
   `reviewing-changes` stays as the tool run by hand on work done outside `implement`.
2. **The procedure is written for the weakest reviewer.** Any roster worker, or a subagent
   of a cheap model, follows the same plain, numbered steps and reaches the same findings a
   strong model would. Nothing in it says "use judgment" or "consult what you need".
3. **The driver prepares the reviewer's inputs; the reviewer never searches.** Before the
   review, the driver puts two closed lists in the brief: the standards docs to check against,
   by exact path, and the doc lines that mention a name the diff renamed or removed. The docs
   are always `docs/agents/GLOSSARY.md` and `docs/agents/CONVENTIONS.md` when they exist,
   plus those the routing table in `docs/agents/INDEX.md` names for the areas the diff
   touches. This follows the driver-picks rule `worker-contract.md` sets for builders, and
   ADR 0012's lowest-tier rule.

   The reviewer then follows fixed steps: read only the listed docs; check each added or
   changed line against every rule in them (a sentence with "must", "never", or "always", a
   required form, or a glossary term marked _Avoid_); decide for each listed doc line whether
   it is still true; report a blocking finding only as
   `VERDICT FIX: Standards — <doc>:<line> says "<rule>"; <file>:<line> breaks it by <what>.`
   or `VERDICT FIX: Stale — <doc>:<line> says "<quote>", which is untrue now because <why>.`;
   and make everything else a NOTE, never repeating what `check.sh` enforces, wording taste,
   or rules from unlisted docs.
4. **Which names the driver searches for, and where.**
   - Names: every path the diff deletes or renames, by its full path and by its file name
     without the extension; and every backticked term that a changed Markdown file mentioned
     before the diff and does not mention anywhere after it.
   - Skip a term that is a single plain word: letters and digits only, with no space, `-`,
     `/`, `.`, or `_` (so `git` and `implement` are skipped, `reviewing-changes` and
     `--no-ff` are kept). This keeps a large diff's list short.
   - Docs searched: every tracked `.md` file except those under `docs/adr/` and
     `docs/intent/`, which record past decisions and are history, not stale docs.
   - Tested on PR #224's diff (42 files): the rule finds `reviewing-changes`, which three
     changed files stopped mentioning, and a search for it reaches `CONVENTIONS.md:95`, the
     line that went stale. Without the single-word limit the rule gave 48 terms there.
5. **A script prepares the inputs, not written commands.** It is a stdlib Python command the
   driver runs once before the review, and its output pastes straight into the brief. It
   declares its requirements in a PEP 723 inline metadata block
   (`# /// script` / `# requires-python = ">=3.11"` / `# ///`), as `worker.py`, `install.py`,
   and `bin/journal` do, even with no dependencies. If it is a new `worker.py` command, it
   inherits that file's block. Its behavior, including the PR #224 case, is tested in
   `scripts/check.sh`.
6. **The script builds the whole doc list from three fixed parts; `INDEX.md` routing is not
   used for it.** The routing table names topics, not paths, so no script can match a diff
   to it.
   - The project instruction file: `CLAUDE.md`, or `AGENTS.md` when there is no
     `CLAUDE.md`. It holds most of this repo's rules in force.
   - `docs/agents/GLOSSARY.md` and `docs/agents/CONVENTIONS.md`, when they exist.
   - Every ADR that names a file the diff changes, matched by the file's name (`gitflow.sh`).
     A generic name (`SKILL.md`, `README.md`, `INDEX.md`) matches only with its folder
     (`implement/SKILL.md`).
   Tested here: a change to `gitflow.sh` lists 9 ADRs, one to `review-gate.py` lists 5, and
   one to `worker-contract.md` lists none. The first two parts come to about 4,500 words.
7. **ADRs are history, so the review ranks its sources.**
   - The script follows ADR links both ways, repeating until nothing new turns up: it adds
     every later ADR that cites a listed ADR, and every later ADR a listed ADR points to.
     Both directions are needed: ADR 0020 cites the ADR it replaces, but ADR 0006 alone says
     it is "superseded by ADR-0010", and ADR 0010 never names it. Tested here: 0011 brings in
     0013, 0014, 0018, and 0020; 0006 brings in 0010; 0002 brings in 0008 and 0010.
   - It prints each chain together, newest first, with each ADR's `Status:` line on top.
   - The brief gives the reviewer three rules. The living docs (the instruction file,
     `CONVENTIONS.md`, `GLOSSARY.md`) win over any ADR. Within one chain, the newer ADR wins
     where two disagree. A `VERDICT FIX` can cite an ADR rule only when no newer ADR in its
     chain changes it; when the reviewer cannot tell, it is a NOTE. A disagreement between an
     ADR and a living doc is itself a NOTE, since one of them can be stale.
8. **One written procedure serves both reviews.** It lives in one new reference file, such as
   `skills/general/implement/references/standards-review.md`: the command that prepares the
   inputs, the reviewer's numbered steps, which source wins, and the two fixed forms of a
   blocking finding. `implement`'s review brief pastes it in. `reviewing-changes` points its
   Standards axis at the same file, replacing its open-ended brief that says to consult the
   `INDEX.md` routing table.
9. **Smaller choices, made without a question:**
   - The script is a new `worker.py` command, such as `worker.py standards <base>`, so it
     inherits that file's PEP 723 block and sits beside `review` and `record`.
     `reviewing-changes` calls it by that path.
   - The Standards check runs in every ticket's review round (`pipeline.md` step 6). In an
     integrated run, each ticket's review covers it against that ticket's diff; the final
     review stays a check of coverage against the intent.
   - A Standards finding counts toward the same limit of three review rounds as any other.
   - `worker-contract.md` rule 2, which defines a `VERDICT FIX`, gains the two Standards forms
     as further kinds of FIX.

## Affected users and systems

- `skills/general/implement/references/worker-contract.md`, the review brief rules.
- `skills/general/implement/references/pipeline.md`, step 6, and `integrate.md`, the final
  review.
- `skills/general/reviewing-changes/SKILL.md`, its Standards axis.
- `skills/general/implement/scripts/worker.py`, a new command, and a new test under
  `scripts/` wired into `scripts/check.sh`.
- A new `skills/general/implement/references/standards-review.md`.
- `README.md`, "Which skill when".

## Out of scope

- The `to-issues` spec review, which reviews tickets, not diffs.
- New linters. Rules a script can hold belong in `check.sh` (ADR 0012), not in a review.

## Constraints

- Gates only where supervision is absent (ADR 0013), and each review round costs a paid call
  to another model family.
- A reviewer with no materiality bar never passes (journal, 2026-10-02 and 2026-10-03). Any
  standards check added to the pipeline needs the same goal-based FIX bar as Spec.

## Open questions

None.
