# The Standards review

A review asks two questions of a change. Does it do what its ticket asked? Does it follow
the repo's written rules? This file is the procedure for the second question. Every
reviewer follows the same steps, so a weak reviewer and a strong one reach the same
findings. `implement` pastes this procedure into every review brief. `reviewing-changes`
uses it for its Standards axis.

The driver prepares the inputs. The reviewer never searches for docs.

## Prepare (the driver)

Run this command in the worktree, before every review round:

```
python3 <skills>/implement/scripts/worker.py standards <base>
```

`<base>` is the base the review diff starts from. In an integrated run, it is the
integration branch. Paste the whole output into the brief, unchanged.

Run the command again before each round. A fix round changes the diff, so it can change
the lists.

The output has three sections:

1. **Standards docs:** the project instruction file, `GLOSSARY.md`, and `CONVENTIONS.md`.
   These are the living docs. They state the rules in force.
2. **ADRs:** the decision records that name a file the diff changes, and the later ADRs
   linked to them. Each chain is listed newest first, with each ADR's status.
3. **Doc lines:** each line in the docs that names something the diff removed or renamed.

A section with nothing in it says `None.`

## The reviewer's steps

1. Read every doc and ADR the output lists. Read no other doc.
2. Take each line the diff adds or changes. Check it against every rule in those docs. A
   rule is one of these:
   - a sentence that says "must", "never", or "always";
   - a sentence that names a required form, such as a command, a heading, or a format;
   - a glossary term marked _Avoid_.
3. Take each doc line listed under the third heading. Decide one thing: is that line still
   true after the diff?
4. Report a blocking finding only in one of these two forms, exactly:

   ```
   VERDICT FIX: Standards — <doc>:<line> says "<rule>"; <file>:<line> breaks it by <what>.
   VERDICT FIX: Stale — <doc>:<line> says "<quote>", which is untrue now because <why>.
   ```

5. Write everything else as a `NOTE:` line. A NOTE never blocks. Never report any of these:
   - a rule that `scripts/check.sh` or the repo's check command already enforces;
   - wording taste;
   - a rule from a doc the output did not list.

## Which source wins

ADRs are records of past decisions, and they are never edited. A later ADR can replace an
earlier one. So the sources rank like this:

1. The living docs win over any ADR. Those are the instruction file, `CONVENTIONS.md`, and
   `GLOSSARY.md`.
2. Within one ADR chain, the newer ADR wins where two ADRs disagree.
3. A `VERDICT FIX` can cite an ADR rule only when no newer ADR in its chain changes that
   rule. When you cannot tell whether a newer ADR changed it, write a NOTE instead.

When an ADR and a living doc disagree, report that disagreement as a NOTE. One of them can
be stale, and a person decides which.
