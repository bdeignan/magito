# Antigravity installs to GEMINI.md and ~/.gemini/config/skills, not the ~/.agents/skills standard

Antigravity does not follow the `~/.agents/skills` cross-tool standard at the home level — it
reads that path only at workspace scope (`<project>/.agents/skills/`) — and it does not auto-read
`AGENTS.md`/`CLAUDE.md`. Its global instruction file is `~/.gemini/GEMINI.md` (a hardcoded path it
shares with Gemini CLI) and its global skills directory is `~/.gemini/config/skills`, so magito's
`antigravity` stanza points there rather than at `~/.agents/skills`. Because the `GEMINI.md` path
collides with Gemini CLI, only one of the two tools should be enabled at a time. This corrects an
earlier README/CLAUDE.md assumption that Antigravity read `~/.agents/skills`.
