# MAGITO — Handoff Prompt

**Project:** MAGITO (Modular Agent Governance & Task Orchestration)
Inspired by the MAGI AI system from Neon Genesis Evangelion — a miniature,
personal approximation of governed multi-agent orchestration.

**Repo:** `~/code/coding-agent-configs/` (also on GitHub, `main` branch)

---

## What exists

```
coding-agent-configs/
├── install.py              # stdlib-only Python install script (PEP 723, requires 3.11+)
├── install.toml.example    # tool config template (copy to install.toml, gitignored)
├── shared/
│   └── SYSTEM-INSTRUCTIONS.md  # shared cross-tool agent persona/standards
├── skills/
│   ├── general/            # cross-tool skills (empty, .gitkeep holds dir)
│   └── claude/
│       └── grilling/SKILL.md   # stress-test a plan with relentless Q&A
└── agents/
    └── haiku-executor.md   # fast/cheap Claude Code subagent for parallel task execution
```

**Installed symlinks (live):**
- `~/.claude/CLAUDE.md` → `shared/SYSTEM-INSTRUCTIONS.md`
- `~/.claude/skills/grilling` → `skills/claude/grilling/`
- `~/.claude/agents/haiku-executor.md` → `agents/haiku-executor.md`
- `~/.codex/AGENTS.md` → `shared/SYSTEM-INSTRUCTIONS.md`

---

## How install.py works

- Reads `install.toml` (gitignored, machine-local copy of `install.toml.example`)
- Per enabled tool: symlinks `shared/SYSTEM-INSTRUCTIONS.md` → tool's instruction path
- For Claude (detected by presence of `agents` key in config): also symlinks `skills/claude/*/` and `agents/*.md`
- For any tool with a `skills` key: symlinks `skills/general/*/` to its skills dir
- Regenerates `skills/INDEX.md` (gitignored, auto-generated) from SKILL.md frontmatter
- Idempotent, supports `--dry-run` and `--force`
- **Key bug fixed:** never call `.resolve()` on `dst` paths — it follows symlinks and breaks idempotency

**Update cycle:** `git pull && python install.py`
Content edits to existing `.md` files are live immediately (symlinks).
New skills/agents require re-running `python install.py`.

---

## Tool config paths (researched)

| Tool       | Instruction file         | Skills dir              | Agents dir          |
|------------|--------------------------|-------------------------|---------------------|
| Claude     | `~/.claude/CLAUDE.md`    | `~/.claude/skills/`     | `~/.claude/agents/` |
| Codex      | `~/.codex/AGENTS.md`     | —                       | —                   |
| Gemini CLI | `~/.gemini/GEMINI.md`    | `~/.gemini/skills/`     | —                   |

- Claude Code and Gemini CLI scan skills dirs **recursively** — whole-dir symlinks work
- Codex auto-discovers `~/.codex/AGENTS.md` as global scope — no config.toml edit needed
- AGENTS.md (project-level format) is adopted by 28+ tools but NOT Claude Code (uses CLAUDE.md)
- `~/.agents/` as a global standard is a draft proposal (dotagents v0.1.0), not widely adopted yet

---

## haiku-executor design

Fast/cheap Claude Code subagent for parallel issue implementation. Key design decisions:
- `permissionMode: acceptEdits` — auto-accepts file edits without prompting (no `permissions.allow` block, which doesn't exist in agent frontmatter)
- `model: haiku` shorthand — tracks latest Haiku automatically
- Tools: `Read, Write, Edit, Bash, Glob, Grep, LS` (Bash for read-only ops + git staging)
- Does NOT manage worktree lifecycle — orchestrator (Sonnet main session) owns create/merge
- Stages explicit files only: `git -C <worktree-path> add <file1> <file2>` — never `git add -A`
- To spawn 3 in parallel, tell the main Sonnet session: "Use haiku-executor to tackle issues 23, 24, 25 in parallel"

---

## Deferred / next steps

1. **Gemini skills install** — `tools.gemini` is `enabled = false` in install.toml.example.
   Raw dir symlinks into `~/.gemini/skills/` may require `gemini skills link --consent` to
   register with Gemini's manifest. Needs a live test before enabling.

2. **INDEX.md auto-loading in Claude Code** — `skills/INDEX.md` is generated but not imported
   into `~/.claude/CLAUDE.md` automatically (shared file avoids tool-specific `@` syntax).
   Fix: add a thin Claude-specific `claude/CLAUDE.md` wrapper that `@`-imports both
   `shared/SYSTEM-INSTRUCTIONS.md` and `~/.claude/skills/INDEX.md`, and update install.py
   to symlink that wrapper instead of the shared file for Claude.

3. **Worktree orchestration skill/template** — a reusable skill or prompt template the
   orchestrator shares with haiku-executor instances: worktree path, issue spec, staging
   instructions. Deferred until first real parallel-issue workflow is needed.

4. **Push to GitHub** — repo is initialized locally. When ready:
   ```bash
   git remote add origin <github-url>
   git push -u origin main
   ```

5. **Grow SYSTEM-INSTRUCTIONS.md** — currently a minimal stub. Refine tone, persona,
   and coding standards over time as you interact with the agents.

---

## Key design decisions (short rationale)

- **One shared instructions file, multi-target symlinks** — single source of truth; `git pull` propagates changes to all tools instantly
- **Tool-specific skills are isolated by directory** — `skills/claude/` only goes to `~/.claude/skills/`; other tools never see Claude-specific skills
- **install.toml is gitignored** — paths differ per machine; `install.toml.example` is the committed template
- **skills/INDEX.md is gitignored** — auto-generated on every install run; committing it would create noisy diffs on every skill addition
- **Skills symlinked as whole directories** — adding `references/` or `scripts/` to a skill is immediately live without reinstalling
