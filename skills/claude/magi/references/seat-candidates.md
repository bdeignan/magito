# Seat candidates

Vetted headless-capable agent CLIs for tribunal seats, as of July 2026. A seat
candidate needs one thing: a shell command that takes a brief and prints a verdict on
stdout. Configure the chosen seats per machine in `~/.magito/bench.toml` (see
[SKILL.md](../SKILL.md)); this file is the menu, not the config.

`family` is the model that answers, not the CLI vendor (see [SKILL.md](../SKILL.md)) —
beware seating a second anthropic-family judge next to Melchior.

Any candidate whose command takes a `--model`-style flag (agy, pi, opencode) can use
the `{model}` placeholder convention documented in [SKILL.md](../SKILL.md)'s Seat
resolution section, so the model choice survives a vendor renaming its flags. codex
and gemini are close enough to single-family defaults that this usually isn't needed;
qwen's documented headless command below takes no model flag at all. omp's docs prefer
`--model` (`--provider` is legacy), so it can use the placeholder too.

| CLI | Family | Headless command | Auth |
|-----|--------|------------------|------|
| codex | openai | `codex exec --sandbox read-only "<brief>"` | ChatGPT login or `OPENAI_API_KEY` |
| gemini | google | `gemini --skip-trust -p "<brief>"` | enterprise Code Assist, or paid `GEMINI_API_KEY` |
| agy (Antigravity) | google by default; can run anthropic and others via `--model` | `script -q /dev/null agy --sandbox -p "<brief>"` | Google account or `ANTIGRAVITY_API_KEY` (key env unconfirmed) |
| pi | any (BYOK) | `pi -p "<brief>" --provider <name> --model <id> --mode json` | provider API keys |
| omp | any (BYOK, 40+ providers; native OpenRouter support) | `omp -p --no-session "<brief>" --model {model}` | provider API keys (e.g. `OPENROUTER_API_KEY`) |
| opencode | any (BYOK); the documented DeepSeek path | `opencode run -m deepseek/deepseek-v4-pro --format json "<brief>"` | `DEEPSEEK_API_KEY` (or other provider keys) |
| qwen | qwen | `qwen -p "<brief>"` | free-tier OAuth or OpenAI-compatible key |

## Quirks that will bite

- **gemini**: consumer tiers (free, Pro, Ultra) lost access on 2026-06-18, replaced by
  Antigravity CLI ("Project ID required" errors mean an ineligible account, not a
  missing project). Works with enterprise Code Assist or a paid, restricted
  `GEMINI_API_KEY` — and Google's key-format migration (~September 2026) may break
  standard keys.
- **agy**: emits nothing when stdout is not a TTY — a known bug, tracked upstream as
  google-antigravity/antigravity-cli#76 (open, no maintainer response as of July 2026).
  Shelling out pipes stdout, so always wrap in a pseudo-terminal:
  `script -q /dev/null agy ...`. There is no JSON or structured-output flag — `agy -p`
  prints plain text only. Consumer quotas are low; an exhausted quota errors out and
  counts as an empty seat.
- **opencode**: headless one-shot needs `--dangerously-skip-permissions` in some
  versions and OpenCode >= v1.14.24 (earlier versions had a headless session bug).
- **pi**: `--mode json` emits JSON-lines events — the easiest seat to parse verdicts
  from.
- **omp**: probe-verified 2026-07-14 (ping and the `-p ... --model` pairing both
  answered on a live bench). Give `--model` the full `provider/model` path (e.g.
  `openrouter/deepseek/deepseek-v4-flash`) — a bare fuzzy name can resolve to a
  different provider and fail on missing auth (reconfirmed 2026-07-22: bare `gemini`
  and `kimi` misrouted to their *direct* providers and failed on the missing key,
  while bare `deepseek` happened to route through OpenRouter). Add `--no-session` so
  seat calls stay stateless. `--mode json` works but emits a verbose NDJSON event
  stream (every thinking delta included); plain text output is easier to read verdicts
  from.
- **omp roles vs. the responder** (verified 2026-07-22): `--model` also accepts a
  **role alias** — `@default`, `@slow`, `@plan`, `@smol` — which resolves to whatever
  model backs that role in the user's omp config *and* makes it the print-mode
  responder. This is how you bind a seat to a role (it follows the user repointing the
  role) rather than to a fixed model id — e.g. `--model @slow` seats the deep-reasoning
  role, the natural fit for a tribunal vote. Do NOT confuse this with the bare
  `--slow`/`--plan`/`--smol` flags: those *set the model backing a role*, they do not
  route the one-shot responder. In `-p` print mode the responder is the `default` role
  (i.e. `--model`); omp only reaches `slow` on its own intent judgment, which is
  non-deterministic — useless for a stateless seat. So pin the responder with
  `--model <id>` or `--model @slow`, never `--slow` alone. Two caveats: an
  *unconfigured* role silently resolves to some cloud model instead of erroring (issue
  can1357/oh-my-pi#2336), and a role-alias seat's declared `family` is a snapshot —
  repointing the role can silently make the tag (and magi's diversity count) stale.
- **OpenRouter as the key behind BYOK seats**: one pay-as-you-go key fronts DeepSeek,
  Kimi, GLM, Qwen, and frontier models, so pi/omp/opencode seats can each run a
  different family off the same credential. Declare `family` from the model that
  answers, never "openrouter". Account quirk: a one-time $10 credit purchase
  permanently raises the `:free`-model daily cap from 50 to 1,000 requests
  (20 req/min regardless).

## Unconfirmed — verify before configuring

- The `ANTIGRAVITY_API_KEY` env var. (`agy --output-format` is resolved: no such flag
  exists — see the agy quirk above. omp's flags are resolved: probed 2026-07-14 — see
  the omp quirk above.)

When a candidate is unverified, run SKILL.md's probe against it before configuring.
