<!-- issue-tracker.md — where work is tracked for this repo and how to reach it. Generated
     from skills/general/setup-magito/references/issue-tracker-github.md.template. Not
     auto-loaded; routed from INDEX.md and read by any skill that names a tracker
     operation. -->

# Issue tracker: GitHub

Work for magito is tracked as GitHub issues on `bdeignan/magito`, reached through the `gh`
CLI. [`issues.sh`](../../skills/general/implement/scripts/issues.sh) is the deterministic
wrapper around the verbs agents otherwise retype freehand — it fails loudly on a missing
argument or missing auth instead of opening an editor or retrying. Each operation below gives
the wrapper first and the plain `gh` command after it, so this file still reads correctly on
a machine without magito installed.

Skills never name a backend. They name one of the operations below and read this file to find
out how to perform it here.

`<skills>` below is your tool's installed skills directory — `~/.claude/skills` for Claude
Code, `~/.agents/skills` for most others.

## Ticket identifiers

`#<number>`, unique within the repo. `gh` infers the repo from the clone's `git remote`, so
no `--repo` flag is needed inside a working copy. GitHub shares one number space between
issues and pull requests, so a bare `#42` may be either — try `gh issue view 42` and fall
back to `gh pr view 42`.

## List open tickets

```
bash <skills>/implement/scripts/issues.sh list          # gh issue list
```

Extra flags pass straight through to `gh issue list`, e.g. `list --label enhancement --state all`.

## Fetch a ticket

```
bash <skills>/implement/scripts/issues.sh view <number>     # gh issue view <number>
```

The wrapper takes the number and nothing else. For the conversation and the relationship
fields, call `gh` directly:

```
gh issue view <number> --comments
gh issue view <number> --json number,title,body,labels,parent,subIssues,blockedBy,blocking
```

## Publish a ticket

```
bash <skills>/implement/scripts/issues.sh create "<title>" "<body>"
# gh issue create --title "<title>" --body "<body>"
```

Both arguments are mandatory. Use a heredoc or a `$(cat file)` for a multi-line body.

## Comment on a ticket

```
bash <skills>/implement/scripts/issues.sh comment <number> "<body>"
# gh issue comment <number> --body "<body>"
```

## Close a ticket

```
bash <skills>/implement/scripts/issues.sh close <number>    # gh issue close <number>
```

Merging a PR whose body says `Closes #<n>` closes the issue on its own — don't close it a
second time by hand.

## Link a sub-ticket

```
bash <skills>/implement/scripts/issues.sh sub-add <parent> <child>
# gh issue edit <parent> --add-sub-issue <child>
```

Read the relationship back with `gh issue view <n> --json parent,subIssues,subIssuesCompleted`.

## Blocking edges

GitHub has native issue dependencies, and `gh` exposes them as ordinary flags. Nothing here
needs GraphQL or a convention buried in a ticket body:

```
gh issue edit <n> --add-blocked-by <blocker>     --remove-blocked-by <blocker>
gh issue edit <n> --add-blocking <blocked>       --remove-blocking <blocked>
```

Read them back with `gh issue view <n> --json blockedBy,blocking`. A ticket is ready to start
when every entry in `blockedBy` is closed.

## Pull requests

**PR creation does not route through this file.** It stays on
`bash <skills>/implement/scripts/gitflow.sh pr <issue> <title>`, which checks for a review
decision before it opens anything. Whoever later notices that `gh pr create` is missing here
and decides to "unify" it weakens the review gate on fan-out branches. Leave it where it is;
[`docs/adr/0015`](../adr/0015-the-tracker-is-an-adapter-in-prose.md) is the canonical reason
and the place to argue with it.

Reading PRs is unrestricted: `gh pr list`, `gh pr view <n>`, `gh pr diff <n>`.
