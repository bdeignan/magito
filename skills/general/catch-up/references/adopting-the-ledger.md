# Adopting the ledger in an existing project

This is for a project that already has its own notes or handoff habit —
including one of magito's own old single-file handoffs. It explains what
changes, what doesn't, and the one-time step to bring old history in.

## What the ledger is, and isn't

The session ledger is one file, `~/.magito/ledger.db`, machine-local. It is
never committed to any repo.

It replaces one thing: magito's own old handoff file
(`~/.magito/handoffs/<repo-slug>.md`). It does not touch anything else. Your
project's `README`, its ADRs, `docs/agents/GLOSSARY.md`, and any other notes stay exactly
as they are. The ledger is not a replacement for project documentation — it
is a replacement for the old scratch handoff file magito wrote for itself.

## Nothing to install per project

After `python install.py` places `~/.magito/bin/clock` on a machine, and the
instruction-file floor (`CLAUDE.md` / `AGENTS.md`) is in place, every project
on that machine already has the ledger available. There is no per-project
setup:

- `/catch-up` clocks in on its own, at the start of a session.
- `/handoff` clocks out on its own, at the end of a session.

## The one-time step: importing the old handoff file

If this project has an old handoff file from before the ledger existed,
import it once. Paste the prompt below to an agent, inside the project. It
runs `clock import-handoff`, which reads the old file, saves its text as one
closed "imported" session in the ledger, and leaves the old file in place —
nothing is deleted. After that, forget the old file; the ledger is the
source of history going forward.

## Checking it worked

Two ways to confirm the import landed:

- `clock status` lists the imported session alongside any other sessions
  for this repo.
- `/catch-up` shows it in the recent-sessions list the next time you clock
  in.

## The paste prompt

Run this once, inside the target project, with an agent:

```
You are turning on the magito session ledger in this project. Do these steps in order and report what you find at each one.

1. Run `~/.magito/bin/clock in` once. Confirm it created or opened the ledger and printed an orientation payload.
2. Run `~/.magito/bin/clock import-handoff`. It looks for this repo's old handoff file and, if it finds one, saves its text as a single closed "imported" session. It does not delete the file. Report whether a file was found and imported.
3. Run `~/.magito/bin/clock status` and confirm both the current session and (if there was one) the imported session show up.
4. Tell me if this project has its own notes or handoff habit I should know about. The ledger does not replace the project's own docs — only magito's old handoff file.
```
