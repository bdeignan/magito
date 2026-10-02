# Pull-request body

A PR body is for the human reviewer and for anyone who reads it later — a reader who did not do the work. Write it for that reader: apply the [readability standard](../../to-issues/references/readability.md) and hold its audience frame while you draft. Do not write for the commit record.

`gitflow.sh pr` refuses a body that is empty or holds only closing lines (`Closes #N`, `Fixes #N`, and the like), in every mode. Write the body to a file with your file-writing tool, then pass it as `"$(cat <file>)"`. If you must redirect in the shell, use `>|`: under zsh `noclobber`, a plain `>` onto an existing file fails and leaves the file empty.

## Title

The title uses [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, for example `fix(gitflow): refuse an empty pull request body`. The type is one of `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `build`, `ci`, `style`, or `revert`. The scope is optional, and a `!` before the colon marks a breaking change. Write the summary as plain words a reader understands without the diff. When the forge squash-merges, the title becomes the commit message on the base branch.

`gitflow.sh pr` checks the title against `git config magito.prTitlePattern`, an extended regular expression. Unset means the Conventional Commits pattern above. `off` turns the check off.

## Guest repos

In guest mode (`mode = "guest"` in `.magito/config.toml`), the repo belongs to a team, and its house style wins:

- **Body:** when the repo has `.github/pull_request_template.md`, fill in that template instead of the skeleton below. The rules in §What the body never says apply inside the team's template too.
- **Title:** follow `magito.prTitlePattern`. When it is `off`, match the titles of the repo's recent merged pull requests. `setup-magito` sets the pattern in guest mode.

## Right-sized structure

Match the structure to the size of the change. A trivial PR can be one or two sentences. Reach for headings only when the change is large enough or crosses enough concerns that a scan needs landmarks.

When headings help, use this light skeleton and skip any section that does not add clarity:

- **Why** — the problem or motivation. Lead with this.
- **What** — the change, in a line or two.
- **How it was verified** — tests run, throwaway checks, commands exercised.
- **Risks / follow-ups** — notable side effects or deferred work. Optional.

Example:

> **Why:** Issue #91 asked for one shared PR-body reference because the same guidance lived in two places and the squash-merge framing was repo-dependent.
>
> **What:** Moved the guidance into `skills/general/implement/references/pr-body.md` and pointed both the single-issue path and the parallel fan-out at it.
>
> **How it was verified:** `grep` found no repo-dependent merge framing in `skills/`; `python install.py --dry-run` completed cleanly.

## What the body never says

These rules hold for every pull request an agent opens. A teammate reads the body to judge the change. How the change was produced is not their concern, and the run's last message to the user carries it.

1. **No reviewer.** The body never says who or what reviewed the change: no reviewer name, no model family, and no note that a subagent reviewed.
2. **No review rounds.** The body never lists review rounds or their results.
3. **No magito vocabulary and no magito bookkeeping, of any kind.** The body never describes how magito produced the change: which skills ran, which steps or stops happened, which files under `.magito/` were written, or which intent doc or ticket draft the work came from. Test every sentence: a teammate who has never heard of magito can read it and loses nothing. These words are examples of what the rule rules out, not the full list: pipeline, roster, worker, verdict, marker, subagent, escalation, intent doc, spec review. One exception: when the change itself is about one of these things, as in the magito repo, the body can name it as the subject of the change.
4. **A test that failed before and passes now goes under "How it was verified", in ordinary words:** the command, and that it failed before the change and passes after it. When the work had no such test, add nothing for it.
5. **Each choice you made alone stays in the body,** one line each, in the form "Chose X over Y because Z". A code reviewer can overrule a choice only when they can see it.

## Closing issues

`gitflow.sh pr <issue>` appends `Closes #<issue>` automatically. Do not add that line to the body for the primary issue. Add `Closes #M` lines only for extra issues the same PR resolves.

For an integrated run (see [integrate.md](./integrate.md)), the script still appends `Closes #<first-ticket>` for the ticket you pass it. Put a `Closes #<n>` line in the body for every other ticket in the run, each on its own line. Never write the first ticket's line yourself: the body would name it twice.
