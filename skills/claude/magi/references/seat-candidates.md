# Seat candidates

Vetted headless-capable agent CLIs for tribunal seats, as of July 2026. A seat
candidate needs one thing: a shell command that takes a brief and prints a verdict on
stdout. Configure the chosen seats per machine in `~/.magito/bench.toml` (see
[SKILL.md](../SKILL.md)); this file is the menu, not the config.

`family` is the model that answers, not the CLI vendor (see [SKILL.md](../SKILL.md)) —
beware seating a second anthropic-family judge next to Melchior.

| CLI | Family | Headless command | Auth |
|-----|--------|------------------|------|
| codex | openai | `codex exec --sandbox read-only "<brief>"` | ChatGPT login or `OPENAI_API_KEY` |
| gemini | google | `gemini --skip-trust -p "<brief>"` | enterprise Code Assist, or paid `GEMINI_API_KEY` |
| agy (Antigravity) | google by default; can run anthropic and others via `--model` | `script -q /dev/null agy --sandbox -p "<brief>"` | Google account or `ANTIGRAVITY_API_KEY` (key env unconfirmed) |
| pi | any (BYOK) | `pi -p "<brief>" --provider <name> --model <id> --mode json` | provider API keys |
| omp | any (BYOK, 40+ providers) | `omp -p "<brief>"` | provider API keys |
| opencode | any (BYOK); the documented DeepSeek path | `opencode run -m deepseek/deepseek-v4-pro --format json "<brief>"` | `DEEPSEEK_API_KEY` (or other provider keys) |
| qwen | qwen | `qwen -p "<brief>"` | free-tier OAuth or OpenAI-compatible key |

## Quirks that will bite

- **gemini**: consumer tiers lost access in June 2026 ("Project ID required" errors
  mean an ineligible account, not a missing project). Works with enterprise Code
  Assist or a paid, restricted `GEMINI_API_KEY` — and Google's key-format migration
  (~September 2026) may break standard keys.
- **agy**: emits nothing when stdout is not a TTY — a known bug. Shelling out pipes
  stdout, so always wrap in a pseudo-terminal: `script -q /dev/null agy ...`. Consumer
  quotas are low; an exhausted quota errors out and counts as an empty seat.
- **opencode**: headless one-shot needs `--dangerously-skip-permissions` in some
  versions and OpenCode >= v1.14.24 (earlier versions had a headless session bug).
- **pi**: `--mode json` emits JSON-lines events — the easiest seat to parse verdicts
  from.

## Unconfirmed — verify before configuring

- `agy --output-format` (contested) and the `ANTIGRAVITY_API_KEY` env var.
- omp's JSON output flag (only `-p` is confirmed).

When a candidate is unverified, run SKILL.md's probe against it before configuring.
