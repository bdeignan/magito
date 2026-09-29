<p align="center">
  <img src="assets/magito-banner.svg" alt="MAGITO — Modular Agent Governance &amp; Task Orchestration" width="820">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/claude_code-MELCHIOR-ff9d3c?style=flat-square&labelColor=0a0e16" alt="Claude Code">
  <img src="https://img.shields.io/badge/codex-BALTHASAR-ff9d3c?style=flat-square&labelColor=0a0e16" alt="Codex">
  <img src="https://img.shields.io/badge/gemini_cli-CASPER-ff9d3c?style=flat-square&labelColor=0a0e16" alt="Gemini CLI">
  <img src="https://img.shields.io/badge/install-symlink-28c840?style=flat-square&labelColor=0a0e16" alt="Symlink install">
  <img src="https://img.shields.io/badge/deps-stdlib_only-7f8aa3?style=flat-square&labelColor=0a0e16" alt="stdlib only">
</p>

---

## What this is

**MAGITO** (*Modular Agent Governance & Task Orchestration*) is a personal,
version-controlled configuration layer for agentic command-line tools. One repo holds
your shared agent persona, skills, and subagents; an install script symlinks them into
the native config paths each tool expects. Edit once, `git pull` anywhere, and every
tool on every machine stays in sync.

<details>
<summary>Why "MAGITO"?</summary>

It is named after — and lightly modeled on — the **MAGI** supercomputer system from
*Neon Genesis Evangelion*: three semi-independent cores deliberating under one
governance layer. The MAGI decided the fate of humanity. This decides which markdown
file your CLI reads. The ambition here is deliberately *scoped*.

| MAGI core      | …governs       | Role here                                  |
|----------------|----------------|--------------------------------------------|
| **MELCHIOR**   | Claude Code    | Primary orchestrator — subagents, skills, worker delegation |
| **BALTHASAR**  | Codex          | Shares the same persona via `AGENTS.md`    |
| **CASPER**     | Gemini CLI     | Shares the same persona via `GEMINI.md`    |
| —              | Antigravity    | Shares Gemini CLI's persona via the same `GEMINI.md` (enable only one) |
| —              | omp (Oh My Pi) | Shares the same persona via `AGENTS.md`    |

</details>

Every tool reads from a **single source of truth** (`shared/SYSTEM-INSTRUCTIONS.md`), so
your standards stay identical no matter which CLI you reach for.

The governance layer goes further than shared instructions: the primary orchestrator
can delegate implementation work to *other* CLIs as headless workers — a cheap model
builds in an isolated worktree, the orchestrator reviews and lands it. Worker
commands are machine-local (`~/.magito/workers.toml`), so each machine hires from
whatever CLIs it actually has. It also keeps a session journal — one file per
session recording what happened and what is unfinished — so a fresh session can
pick up where the last one left off.

Learning to drive it? Read [Which skill when](#which-skill-when): the main path, one line for
every other skill, and the promises magito keeps.

## How it works

The model is dead simple: **files live in this repo; the tools read them via symlink.**
`install.py` (stdlib-only Python, 3.11+) reads your machine-local `install.toml` and
creates those symlinks for every tool you have enabled. Because they are symlinks:

- **Editing the content of an existing file is live instantly** — no reinstall. The tool
  reads through the link to the repo file.
- **Adding a *new* skill, agent, or hook requires a reinstall** — a new file needs a new link.

The script is idempotent (safe to re-run), and regenerates `skills/INDEX.md` from each
skill's frontmatter on every run. Exactly which repo path maps to which tool's native
config path is listed in [`CLAUDE.md`](CLAUDE.md).

## Quick start (first time on a machine)

```bash
git clone <repo-url> ~/code/magito
cd ~/code/magito

cp install.toml.example install.toml   # your local, gitignored config
$EDITOR install.toml                    # set enabled = true for tools you use

python install.py --dry-run            # preview every symlink it would create
python install.py                      # apply
```

That is it — your CLIs now read this repo.

## Which skill when

Skills are the source of truth. If this section disagrees with a skill, the skill is right and
this section needs a fix.

### The main path

Most work follows one path. You act at three points: accepting the intent, answering an
escalation, and the merge.

1. **`/catch-up`** starts a session. It reads the journal, the tracker, and git, then names the next move.
2. **`/intent`** interviews you one question at a time and produces an intent doc. You act here: you accept the doc.
3. **`to-issues`** runs on its own after you accept. It turns the intent into reviewed tickets and publishes them.
4. **`implement`** runs on its own after that. It builds each ticket, gets it reviewed by a model from a different family when the roster has one, and stops only for an escalation. You act here when it escalates.
5. **The pull request** is the result. You act here: you merge it. In a repo with no remote, the agent stops and asks instead, and merges only after you approve.
6. **`/handoff`** ends the session with one entry in `.magito/journal/`.

Work with no accepted intent can still enter at `/to-issues` (a plan) or `/implement` (one clear
issue). Those tickets keep the older steps: plan approval before code and "ship it" before the pull request.

### Every other skill

- **`/magi`**: a three-seat tribunal for a question no test can settle. Poll is cheap; `deliberate` asks for cost consent first.
- **`/decruft`**: a harsh structural review for the cruft that agents leave behind. It proposes cuts; you approve them.
- **`/challenging-assumptions`**: an adversarial pre-mortem of a plan before you commit, ending in a verdict.
- **`/research`**: an evidence-backed report on an open question, with options and a recommendation.
- **`/finding-lacunae`**: a hunt for the essential element that a topic or design is missing.
- **`/reviewing-changes`**: the two-axis review (Standards and Spec) of any diff, on its own.
- **`/speaking-plainly`**: reset your writing voice, or rewrite dense text plainly.
- **`/teach`**: learn a concept over several sessions, using the current directory as the workspace.
- **`/to-questionnaire`**: turn a decision you cannot make alone into a questionnaire for one person.
- **`/wait-what`**: re-pitch the last message when it did not land.
- **`/domain-modeling`**: sharpen the project vocabulary and record decisions in the glossary and ADRs.
- **`/verifying`**: the testing discipline for Python work: real seams, red-green, and data checks.
- **`/writing-for-agents`**: write skills, `AGENTS.md`, `CLAUDE.md`, issues, and prompts that agents read well.
- **`/setup-magito`**: audit and repair one repo's magito configuration. Run it once per new project; it is safe to re-run.

### What magito promises

1. **You own every merge.** Agents branch, commit, and open pull requests. You merge a pull request yourself. In a repo with no remote, an agent merges only after your explicit approval.
2. **Nothing lands unreviewed by accident.** Work on the pipeline path gets an automatic review, from a different model family when the roster has one. Any other pull request or merge reaches a deliberate choice first: a full review, a lightweight pass, or a knowing skip.
3. **Delegation is explicit.** Reviews on the pipeline path go to a roster worker from a different model family, chosen by `worker.py reviewer`. When no such worker answers, a fresh-context subagent reviews instead, and the pull request says so. Builds delegate only to a worker you name ("via omp"). Thrifty mode limits every step to cheap models.
4. **Worker failures are loud.** A named build worker that is dead or denied stops the run instead of quietly handing the work to your subscription. Your tool's own permission prompts still apply to each worker launch.
5. **Machine-local files are yours.** `~/.magito/` is bootstrapped once with your consent and never overwritten on an agent's own initiative. `bin/` is the exception: `install.py` owns it.
6. **Staging is always explicit.** No agent bulk-stages files. A hook blocks `git add -A` everywhere.
7. **Costs are stated before they are incurred.** A fan-out declares its executor count and workers up front. Magi deliberate mode asks before it convenes.

You stay in the loop at these moments only: accepting an intent, answering an escalation, the
one-time roster bootstrap, magi deliberate cost consent, and every merge. Everything else runs
without you and stops loudly when it cannot continue.

---

## User guide

### 🔄 Syncing a change to another machine

This is the one you will reach for most. You changed something on machine A; pull it down
on machine B:

```bash
cd ~/code/magito
git pull
python install.py        # only strictly needed if NEW skills/agents/tools/bin files were added
```

**Rule of thumb for whether you need `install.py` after a pull:**

| What changed in the pull                                  | Reinstall needed? |
|-----------------------------------------------------------|-------------------|
| Edited `SYSTEM-INSTRUCTIONS.md` or an existing `SKILL.md`  | **No** — symlink already points there, change is live |
| Added a brand-new skill, agent, hook, tool stanza, or `bin/` file (e.g. `journal`) | **Yes** — needs a new symlink |
| Not sure                                                  | Just run it — it is idempotent and harmless |

When in doubt, run `python install.py`. It never does damage on a re-run.

<details>
<summary>➕ Adding a new skill, subagent, hook, or tool</summary>

Full steps for each — which directory a skill goes in, subagent frontmatter fields, the
hook contract, wiring up a new tool stanza — live in [`CLAUDE.md`](CLAUDE.md) under
"Adding a New Skill / Agent / Hook / Tool". That is the file the agents themselves read
before extending this repo, so it stays the one source of truth for these steps.

Short version, every case: create the file with the right frontmatter, then run
`python install.py` to symlink it and regenerate `skills/INDEX.md`.

</details>

<details>
<summary>🩺 Troubleshooting</summary>

```bash
python install.py --dry-run     # show what WOULD happen, change nothing
python install.py --force       # replace symlinks that currently point elsewhere
ls -la ~/.claude/CLAUDE.md       # confirm a link resolves back into this repo
```

- **A tool isn't picking up changes?** Check the symlink actually points here:
  `ls -la <native-path>`. If it points somewhere stale, re-run with `--force`.
- **`install.py` gotcha (for hacking on the script):** never call `.resolve()` on a
  *destination* path before linking — it follows existing symlinks back to the source
  and breaks idempotency.

</details>

---

Full repo layout and the per-tool path table live in [`CLAUDE.md`](CLAUDE.md), kept in
one place so they do not drift out of sync with what the agents actually see.

---

<p align="center"><sub>
  MELCHIOR · BALTHASAR · CASPER — deliberation complete. <b>STATUS: READY.</b>
</sub></p>
