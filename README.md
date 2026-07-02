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

It's named after — and lightly modeled on — the **MAGI** supercomputer system from
*Neon Genesis Evangelion*: three semi-independent cores deliberating under one
governance layer. The MAGI decided the fate of humanity. This decides which markdown
file your CLI reads. The ambition is, let's say, *scoped*.

| MAGI core      | …governs       | Role here                                  |
|----------------|----------------|--------------------------------------------|
| **MELCHIOR**   | Claude Code    | Primary orchestrator + subagents + skills  |
| **BALTHASAR**  | Codex          | Shares the same persona via `AGENTS.md`    |
| **CASPER**     | Gemini CLI     | Shares the same persona via `GEMINI.md`    |

All three read from a **single source of truth** (`shared/SYSTEM-INSTRUCTIONS.md`), so
your standards stay identical no matter which CLI you reach for.

## How it works

The model is dead simple: **files live in this repo; the tools read them via symlink.**

```
   this repo (source of truth)            tool's native path (symlink)
   ─────────────────────────────          ────────────────────────────
   shared/SYSTEM-INSTRUCTIONS.md   ──▶     ~/.claude/CLAUDE.md
                                   ──▶     ~/.codex/AGENTS.md
                                   ──▶     ~/.gemini/GEMINI.md
   skills/general/<name>/          ──▶     ~/.agents/skills/<name>/  (Codex, Antigravity, Gemini…)
                                   ──▶     ~/.claude/skills/<name>/  (Claude)
   skills/claude/<name>/           ──▶     ~/.claude/skills/<name>/  (Claude only)
   agents/<name>.md                ──▶     ~/.claude/agents/<name>.md
   hooks/<name>.py                 ──▶     ~/.claude/hooks/<name>.py  (+ registered in settings.json)
```

`install.py` (stdlib-only Python, 3.11+) reads your machine-local **`install.toml`**,
then creates those symlinks for every tool you've enabled. Because they're symlinks:

- **Editing the content of an existing file is live instantly** — no reinstall. The tool
  reads through the link to the repo file.
- **Adding a *new* skill, agent, or hook requires a reinstall** — a new file needs a new link.

The script is idempotent (safe to re-run), and regenerates `skills/INDEX.md` from each
skill's frontmatter on every run.

## Quick start (first time on a machine)

```bash
git clone <repo-url> ~/code/magito
cd ~/code/magito

cp install.toml.example install.toml   # your local, gitignored config
$EDITOR install.toml                    # set enabled = true for tools you use

python install.py --dry-run            # preview every symlink it would create
python install.py                      # apply
```

That's it — your CLIs now read this repo.

---

## User guide

### 🔄 Syncing a change to another machine

This is the one you'll reach for most. You changed something on machine A; pull it down
on machine B:

```bash
cd ~/code/magito
git pull
python install.py        # only strictly needed if NEW skills/agents/tools were added
```

**Rule of thumb for whether you need `install.py` after a pull:**

| What changed in the pull                                  | Reinstall needed? |
|-----------------------------------------------------------|-------------------|
| Edited `SYSTEM-INSTRUCTIONS.md` or an existing `SKILL.md`  | **No** — symlink already points there, change is live |
| Added a brand-new skill, agent, hook, or tool stanza      | **Yes** — needs a new symlink |
| Not sure                                                  | Just run it — it's idempotent and harmless |

When in doubt, run `python install.py`. It never does damage on a re-run.

### ➕ Adding a new skill

```bash
mkdir -p skills/general/<name>          # cross-tool…
# …or:  skills/claude/<name>            # …Claude Code-only
$EDITOR skills/general/<name>/SKILL.md  # needs `name:` + `description:` frontmatter
python install.py                       # symlink it + regenerate INDEX.md
```

- `skills/general/` → installed to the cross-tool `~/.agents/skills` standard (Codex, Antigravity, Gemini, and 30+ tools) and to `~/.claude/skills` (Claude Code does not yet read `~/.agents/skills`).
- `skills/claude/` → installed to `~/.claude/skills` (Claude Code only).
- A skill is a directory; `references/` and `scripts/` subdirs come along for free
  (the whole dir is symlinked).

### ➕ Adding a new subagent (Claude Code)

```bash
$EDITOR agents/<name>.md   # frontmatter: `name`, `description` (+ optional model/tools/effort)
python install.py
```

### ➕ Adding a new hook (Claude Code)

```bash
$EDITOR hooks/<name>.py    # PreToolUse hook: tool-call JSON on stdin; deny via JSON, allow via silent exit 0
python install.py          # symlink to ~/.claude/hooks/ + register in ~/.claude/settings.json
```

Hooks are the deterministic backstop for rules prose can't guarantee (the staging guard,
the merge/PR review gate). They must **fail open** — any internal error allows the call.
`install.py` merges registrations into `settings.json` idempotently and backs the file
up before writing.

### ➕ Adding a new tool

1. Add a stanza to **both** `install.toml` and `install.toml.example` with an
   `instructions` path (and optional `skills` / `agents` paths).
2. Run `python install.py`.

> A stanza with an `agents` key is treated as Claude Code (gets skills **and** agents).

### 🩺 Troubleshooting

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

---

## Repo layout

```
magito/
├── README.md               # you are here
├── install.py              # symlink installer (stdlib-only, 3.11+; idempotent)
├── install.toml            # your machine-local config (gitignored)
├── install.toml.example    # committed template — copy to install.toml
├── assets/
│   └── magito-banner.svg   # the banner above (dark/light aware)
├── shared/
│   └── SYSTEM-INSTRUCTIONS.md   # single source of truth → all tools
├── skills/
│   ├── INDEX.md            # auto-generated (gitignored)
│   ├── general/            # cross-tool skills
│   └── claude/             # Claude Code-only skills (e.g. dispatch/)
├── hooks/                  # Claude Code PreToolUse hooks (staging guard, review gate)
└── agents/
    └── haiku-executor.md   # fast/cheap Claude Code subagent for parallel tasks
```

### Tool config paths

| Tool       | Instruction file       | Skills dir          | Agents dir          | Hooks dir          |
|------------|------------------------|---------------------|---------------------|--------------------|
| Claude     | `~/.claude/CLAUDE.md`  | `~/.claude/skills/` | `~/.claude/agents/` | `~/.claude/hooks/` |
| Codex      | `~/.codex/AGENTS.md`   | `~/.agents/skills/` | —                   | —                  |
| Gemini CLI | `~/.gemini/GEMINI.md`  | `~/.agents/skills/` | —                   | —                  |

---

<p align="center"><sub>
  MELCHIOR · BALTHASAR · CASPER — deliberation complete. <b>STATUS: READY.</b>
</sub></p>
