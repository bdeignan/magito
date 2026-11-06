# Pull-request body

A PR body is for the human reviewer and for anyone who reads it later — a reader who did not do the work. Write it for that reader: apply the [readability standard](../../to-issues/references/readability.md) and hold its audience frame while you draft. Do not write for the commit record.

The body is never empty, and never only closing lines (`Closes #N`, `Fixes #N`, and the like), in every mode. Pass the body as one `--body` argument to `gh pr create`.

## Title

The title uses [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, for example `fix(parser): refuse an empty input file`. The type is one of `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `build`, `ci`, `style`, or `revert`. The scope is optional, and a `!` before the colon marks a breaking change. Write the summary as plain words a reader understands without the diff. When the forge squash-merges, the title becomes the commit message on the base branch.

When `git config magito.prTitlePattern` is set, the title follows that pattern, an extended regular expression. When it is unset, the title follows Conventional Commits as above. `off` means no pattern applies.

## Guest repos

In guest mode (`mode = "guest"` in `.magito/config.toml`), the repo belongs to a team, and its house style wins:

- **Body:** when the repo has `.github/pull_request_template.md`, fill in that template instead of the skeleton below. The rules in §What the body never says apply inside the team's template too.
- **Title:** follow `magito.prTitlePattern`. When it is `off`, match the titles of the repo's recent merged pull requests. `setup-magito` sets the pattern in guest mode.

## Right-sized structure

Match the structure to the size of the change. A trivial PR can be one or two sentences of Why and What. Reach for headings only when the change is large enough or crosses enough concerns that a scan needs landmarks. Every body has a **Testing** and a **Risk** field, a Low ticket's included.

Use this light skeleton, and skip any optional section that does not add clarity:

- **Why** — the problem or motivation. Lead with this.
- **What** — the change, in a line or two.
- **Testing** — the commands run and what they showed. Required.
- **Risk** — the ticket's level: Low, Normal, or High. Required.
- **How to revert** — only when reverting the pull request is not enough, such as a data migration or a config change.
- **Follow-ups** — notable side effects or deferred work. Optional.

Example:

> **Why:** Issue #91 asked for one shared PR-body reference because the same guidance lived in two places and the squash-merge framing was repo-dependent.
>
> **What:** Moved the guidance into `skills/general/implement/references/pr-body.md` and pointed both the single-issue path and the parallel fan-out at it.
>
> **Testing:** `grep` found no repo-dependent merge framing in `skills/`; `python install.py --dry-run` completed cleanly.
>
> **Risk:** Low
>
> Closes #91

## What the body never says

These rules hold for every pull request an agent opens. A teammate reads the body to judge the change. How the change was produced is not their concern, and the run's last message to the user carries it.

1. **No reviewer.** The body never says who or what reviewed the change: no reviewer name, no model family, and no note that a subagent reviewed.
2. **No review rounds.** The body never lists review rounds or their results.
3. **No magito vocabulary and no magito bookkeeping, of any kind.** The body never describes how magito produced the change: which skills ran, which steps or stops happened, which files under `.magito/` were written, or which intent doc or ticket draft the work came from. Test every sentence: a teammate who has never heard of magito can read it and loses nothing. These words are examples of what the rule rules out, not the full list: pipeline, roster, worker, verdict, marker, subagent, escalation, intent doc, spec review. One exception: when the change itself is about one of these things, as in the magito repo, the body can name it as the subject of the change.
4. **A test that failed before and passes now goes under "Testing", in ordinary words:** the command, and that it failed before the change and passes after it. When the work had no such test, add nothing for it.
5. **Each choice you made alone stays in the body,** one line each, in the form "Chose X over Y because Z". A code reviewer can overrule a choice only when they can see it.

## Closing issues

The body's last line is `Closes #<ticket>` for the ticket being built. You write it; nothing adds it for you. Each extra issue the same pull request resolves gets its own `Closes #<n>` line.
