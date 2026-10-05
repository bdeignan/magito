---
name: workers
description: Show which roster workers and reviewers this machine can use — for each one, whether its tool is installed, the variables it needs are set, and it answers — and create the roster from the example when the machine has none. Use it to see which other tools magito can call here, or after a run reported no reviewer from another family. Do not use it at the start of a session or before every build — implement checks the roster itself at the start of each run, and running this first only repeats that work.
---

# Workers

Report which workers on this machine are ready, and why the others are not. The roster is
`~/.magito/workers.toml`: one entry per command-line coding tool that magito can launch to
build or review. Its format lives in the
[worker contract](../implement/references/worker-contract.md); this skill does not repeat it.
`<skills>` is the folder that holds this skill's own folder: the parent of the directory its `SKILL.md` is in.

This skill reports. It writes one thing only, the copy in step 3. It never edits, overwrites,
or deletes an existing `~/.magito/workers.toml`: that file is the user's. A second run
changes nothing.

1. **Run the report and show its output to the user, unchanged.**

   ```
   python3 <skills>/implement/scripts/worker.py ready --family <your-family>
   ```

   Your family is the family of the model you run as: `anthropic` for Claude, `google` for
   Gemini, `openai` for GPT and Codex models. The output has one line per worker, a
   `launcher allow rule:` line, and a `reviewer for <family>:` line that names the worker a
   run would pick as reviewer.

2. **For each worker that is not fully ready, name the line to change and what to do.**
   Change nothing. Read `~/.magito/workers.toml` with your file-reading tool to find the line
   number, and give it as `~/.magito/workers.toml:<line>`: the line of the field at fault, or
   the line of the entry's `[workers.<name>]` header when the field is absent.
   - `invalid entry (<reason>)`: the entry's `cmd` line, or its header line when it has no
     `cmd`. An entry that is not a table, such as `x = "text"` under `[workers]`, has neither:
     point at the line of that assignment. For a reason about the name, point at the header
     line and say the entry needs another name. Say what the reason means.
   - `installed=no`: the entry's `cmd` line. Install the tool, or correct the program name.
   - `env=missing <VAR>`: no roster line changes. Set the variable in the environment the worker starts from (for zsh, `~/.zshenv`). Name
     the entry's `requires_env` line so the user sees where the requirement comes from.
   - `env=invalid`: the entry's `requires_env` line. It must be a list of strings, such as
     `requires_env = ["GOOGLE_CLOUD_PROJECT"]`.
   - `family=none`: the entry's header line. Add a `family = "<family>"` line under it, or
     the worker can never review.
   - `family=invalid`: the entry's `family` line. It must be a string.
   - `probe=failed`: no roster line is known to be wrong. Tell the user to run
     `python3 <skills>/implement/scripts/worker.py probe <name>` to see the tool's own error,
     which is most often a login that has expired.

   When stderr reported a fault in a top-level setting (`reviewers`, `spec_reviewer`,
   `thrifty`, or `workers`), name that setting's line the same way.

3. **No roster file.** The command exits 2 and says the file was not found. Say so, and
   offer to copy `<skills>/implement/references/workers.toml.example` to
   `~/.magito/workers.toml`. Copy only after the user says yes, and check again right before
   the copy that the destination does not exist. Then tell the user that every entry in the
   file is commented out, that they must uncomment the entries for the tools they have, and
   to run this skill again.

4. **A roster that cannot be read.** The command exits 2 and says why: it is not valid TOML,
   or the file cannot be opened. Show the error it printed and stop. Change nothing.
