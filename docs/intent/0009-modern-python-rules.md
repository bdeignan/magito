# Modern Python project rules

Status: accepted · Opened: 2026-10-06 · Accepted: 2026-10-06

## Problem

Agents write Python from their training data. That data is full of older patterns: raw
`requests`, `setuptools` and `setup.py`, `requirements.txt`, hand-made virtual environments,
`pip install`. Python tooling has changed a lot, and for the better: uv, PEP 621 metadata,
PEP 735 dependency groups, ruff, new type checkers, free-threaded builds. An agent with no
project rules falls back on the old ways.

`setup-magito` records a Python toolchain (uv, the uv build backend, `src/` layout, pytest,
ruff, prek) as a few lines in a project's `## Agent workflow` block, plus `pyproject.toml`
and prek templates under `skills/general/setup-magito/references/`. It does not tell the
agent to run everything through `uv run`, ban pip and `requirements.txt`, name a type
checker, or say anything about CI. Its ruff line length (100) differs from ruff's default
(88).

The pydevtools project rules file (https://pydevtools.com/configs/CLAUDE.md) covers most of
that. The user mostly agrees with it and wants magito's Python setup aligned with it.

## Proposed outcome

A Python project set up with `setup-magito` gets rules and config that steer any agent to
the current, stable Python toolchain, with versions resolved live rather than remembered.

- A new template, `skills/general/setup-magito/references/python-rules.md.template`, holds
  the `## Python` section (the draft below, 106 lines). `setup-magito` copies it into
  whichever of `CLAUDE.md` or `AGENTS.md` holds the project's instructions, in place of the
  toolchain lines the `## Agent workflow` block carries today. A re-run proposes a diff.
- `pyproject.toml.template` takes the pydevtools author's ruff, pytest, and pyrefly settings,
  `requires-python = ">=3.12"`, and the comment to reconsider ty. It carries no versions.
- `pre-commit-config.yaml.template` takes the author's hooks. Its revisions are filled by
  `prek autoupdate`.
- No CI workflow or Dependabot template.
- `setup-magito`'s Python toolchain section scaffolds in this order: check that uv is
  current, `uv init --lib` or `--package`, merge the template settings, `uv add --dev
  pytest ruff pyrefly`, copy the hook config and run `uvx prek autoupdate`. It verifies with
  `uv sync && uv run pytest && uv run ruff check . && uv run pyrefly check` on the skeleton.

Done when: scaffolding a fresh project produces the section and config above, every
version in them is current on the day it runs, and the four verify commands pass.

## Decisions so far

- This is its own intent, separate from ponytail (intent 0008). Tooling rules and
  code-size rules touch different files and ship independently.
- **The rules live in the project's own instruction file.** `setup-magito` copies a
  `## Python` section from a template into whichever of `CLAUDE.md` or `AGENTS.md` holds the
  project's instructions. It replaces the few toolchain lines the `## Agent workflow` block
  carries today. A re-run compares the project's copy with the template and proposes a diff.
  In guest mode it only proposes. Chosen over a pointer into magito's skill folder, which
  breaks when magito is removed, and over a separate `docs/agents/python.md`, which
  `AGENTS.md` cannot auto-load.
- **The section is the pydevtools file, copied, then changed only where this doc decides.**
  The build is a copy and a short list of edits, not a rewrite. The edits:
  - The title becomes `## Python` and each heading drops one level, since the section sits
    inside a project file.
  - The "last verified" version comment is removed. The attribution and guide link stay.
  - "Never call `python` ... directly" becomes "Do not call," and a PEP 723 script line is
    added under "Run code."
  - `uv init project-name` for an application or CLI becomes `uv init --package`. A
    `requires-python` line is added under "Create new projects."
  - The `setup-uv@v10.1.0` pin loses its version.
  - "Check types" names pyrefly only, keeps its `default` preset, and says type hints are
    optional.
  - "Do not add dependencies to pyproject.toml by hand" gains one sentence: tool tables are
    edited by hand, and a hand edit to a dependency list is followed by `uv lock`.
  - Two subsections are added at the end: "Choose libraries" and "Pick versions."
  Everything else stays word for word, including the coverage lines, the CI paragraph,
  `uv init --no-package`, and "prek (preferred) or pre-commit."
- **The section includes a short `### Choose libraries` subsection,** capped at about 12 lines. It
  says "standard library first," then names default libraries for common jobs (`httpx`,
  `pathlib`, `dataclasses`, `logging`, and so on). The audit called this code style rather
  than tooling. It goes in anyway, because training-data drift toward old libraries is the
  problem this intent exists to fix. The user edits the list before acceptance.
- **The type checker is pyrefly, on its `default` preset.** pyrefly is 1.x and marked stable;
  ty is still 0.0.x beta, and mypy is slow. The `pyproject.toml` template carries a comment
  next to `[tool.pyrefly]` saying to reconsider ty once it ships a stable release. Tested
  locally with pyrefly 1.3.2 on a file with two unannotated functions, a mixed-type list,
  and a real `None * 2` bug:
  - `default` reports no missing annotations. It reports the real `None` bug, plus the
    mixed-type list (it infers `list[int]` from the literal).
  - `basic` misses even `x: int = "a"`. Too lax to be worth running.
  - `strict` adds `implicit-any-parameter` for every unannotated parameter; `all` adds
    missing return annotations too. Those are the token sinks the user wants to avoid.
  - `# pyrefly: ignore[<code>]` silences one false error on its line.
  So the template writes `preset = "default"` explicitly, and the section tells agents that
  type hints are optional and never to switch to `strict` or annotate only to quiet the
  checker. Annotations stay where they help a reader, such as a public function.
- **Tool settings follow the pydevtools author's published configuration,** not magito's
  own taste. The source is the author's guide,
  https://pydevtools.com/handbook/explanation/modern-python-project-setup-guide-for-ai-assistants/.
  The templates take its settings as written:
  - ruff: `line-length = 88`, `target-version = "py312"`, lint `select = ["E", "F", "I",
    "B", "C4", "UP"]`, `ignore = ["E501"]` (the formatter handles line length), format
    `quote-style = "double"` and `indent-style = "space"`.
  - pytest: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`,
    `python_functions = ["test_*"]`, `addopts = ["--strict-markers", "--strict-config"]`.
  - pyrefly: `python-version = "3.12"`. Its guide sets no preset, which is pyrefly's
    `default`, so this agrees with the pyrefly decision above.
  - prek config: the `ruff-check` and `ruff-format` hooks, plus `trailing-whitespace`,
    `end-of-file-fixer`, `check-yaml`, `check-toml`, and `check-added-large-files`.
  - CI: a GitHub Actions workflow that checks out, sets up uv with caching, runs
    `uv sync --locked`, `uv run ruff check .`, and `uv run pytest`.
  This replaces magito's `line-length = 100` and its wider `select` list. The user chose the
  author's expertise over ruff's 0.16 default set, which was the agent's recommendation.
- **`requires-python = ">=3.12"`,** matching the author's ruff `target-version` and pyrefly
  `python-version`. The three move together. Replaces magito's `>=3.11`. Rejected: copying
  whatever `uv init` writes, which ties the floor to the machine.
- **No version comes from an agent's memory.** Training data is older than today's
  releases, so agents and review bots state stale versions with confidence (the user has
  seen a bot call Python 3.14 unstable). Three parts, no new skill:
  1. The templates carry settings, never versions. `setup-magito` fills versions live when
     it scaffolds: it checks that uv itself is current (`uv init` takes the `uv_build`
     bounds from the installed uv), then runs `uv add --dev pytest ruff pyrefly` and
     `uvx prek autoupdate`.
  2. The Python section tells agents never to write a version from memory, names the
     commands that resolve one (`uv add`, `uv tree --outdated`, `uv python list`,
     `uvx prek autoupdate`), and says to check with one of them before claiming a version
     does not exist. On-demand upgrade: `uv lock --upgrade && uvx prek autoupdate`.
  A third part, a `.github/dependabot.yml` in each project, was proposed and then dropped
  by the user, along with a CI workflow template.
  Verified locally on 2026-10-06: `uv add --dev` wrote the latest pytest 9.1.1, ruff
  0.16.10, and pyrefly 1.3.2; `uv python list` showed 3.14.6 stable and 3.15 beta;
  `prek autoupdate` runs `prek update`; this machine's uv 0.11.24 wrote stale `uv_build`
  bounds while 0.12.23 is out. Rejected: a magito skill for version audits, which would
  be prose run from the same stale memory unless it called these tools anyway.

## Affected users and systems

- The user, starting or adopting Python projects with any of magito's five tools.
- `setup-magito`'s Python toolchain section and its templates under `references/`.
- `verifying`, which names pytest.

## Out of scope

- magito's own repo. It stays stdlib-only Python with no test framework, by design.
- How much code an agent writes. That is intent 0008.
- External review bots, such as Gemini's on GitHub. magito cannot reach their
  instructions. The bot was only an example of stale knowledge.

## Constraints

- The rules file must read correctly as both `AGENTS.md` and `CLAUDE.md`, so no
  Claude-only syntax in its body.
- Guest mode: `setup-magito` never edits a file the team tracks.
- The whole project instruction file stays at or under about 200 lines. The `## Python`
  section gets a budget inside that (draft: 106 lines).

## Open questions

_None._

## Audit findings (2026-10-06)

A subagent checked the pydevtools file line by line against magito's templates and the
tools' current releases (uv 0.12.23, ruff 0.16.10, prek 0.5.5, pytest 9.1.1, setup-uv
v10.2.0, ty 0.0.84, pyrefly 1.3.2, mypy 2.4.0).

- **Keep most of it.** Nothing in the body is specific to Claude. The uv commands, "commit
  `uv.lock`," no `setup.py` or `requirements.txt`, pytest layout, ruff commands, prek
  through `uvx`, `# type: ignore` with an error code, and `[dependency-groups]` are all
  correct.
- **Wrong:** "use `uv init` for an application or CLI package." Plain `uv init` makes a flat
  `main.py` with no build system. A packaged CLI needs `--package`. `--lib` gives the
  `src/` layout magito wants.
- **Stale already:** the "last verified" header, the `setup-uv@v10.1.0` pin, and "isort via
  `select = ["I"]`" (ruff 0.16 turns it on by default).
- **Too strict:** "never call `python` directly" breaks PEP 723 scripts and hook scripts;
  soften to "use `uv run`." "Never edit `pyproject.toml` by hand" is wrong for tool tables;
  make it "prefer `uv add` for dependencies, and run `uv lock` after a hand edit."
- **Three type checkers** lets the agent pick at random. Name one.
- **magito's own templates are stale:** `uv_build` is pinned below 0.12, the ruff hook rev
  is `v0.15.21` (latest `v0.16.10`), and the explicit ruff `select` now narrows ruff 0.16's
  larger default set.
- **Gaps worth adding:** PEP 723 scripts (`uv init --script`, `uv add --script`,
  `uv run --script`); `--locked` in CI; a one-line `requires-python` policy; the project's
  check command.
- **Cross-tool:** Claude Code does not read `AGENTS.md`, and Gemini CLI and Antigravity read
  `GEMINI.md`. Whichever file holds the rules, the others need a pointer or symlink.
  `setup-magito` already handles this for the workflow block.

## Draft section (2026-10-06)

The `## Python` section as the template will hold it: the pydevtools file, copied, with the
deviations listed under "Decisions so far." 106 lines.

    ## Python

    <!-- Generated from pydevtools.com, the Python Developer Tooling Handbook -->
    <!-- Full explanations: https://pydevtools.com/handbook/explanation/modern-python-project-setup-guide-for-ai-assistants/ -->

    ### Manage packages

    This project uses uv. Do not use pip, pip-tools, poetry, or conda.

    - Add runtime dependency: `uv add <package>` (writes to `[project.dependencies]`)
    - Add dev dependency: `uv add --dev <package>` (writes to `[dependency-groups]` per PEP 735)
    - Remove dependency: `uv remove <package>`
    - Sync environment from lockfile: `uv sync`
    - Regenerate lockfile from constraints: `uv lock`
    - Upgrade locked versions: `uv lock --upgrade`
    - Commit `uv.lock` to version control (current uv guidance is to commit it for applications, CLIs, and libraries)

    ### Run code

    Always use `uv run` to execute Python code and tools. Do not call `python`, `pytest`, `ruff`, or other tools directly. They may not resolve to the project's virtual environment.

    - Run a script: `uv run python script.py`
    - Run a module: `uv run python -m module_name`
    - Run a tool: `uv run pytest`, `uv run ruff check .`
    - One-off tool (not a project dependency): `uvx <tool>`
    - Standalone script: declare its dependencies in a PEP 723 block. Create it with `uv init --script <file>`, add to it with `uv add --script <file> <package>`, and run it with `uv run --script <file>`

    ### Create new projects

    - Application or CLI package: `uv init --package project-name`
    - Library without a console script: `uv init --lib project-name`
    - Internal script or non-package project: `uv init --no-package project-name`
    - Set `requires-python = ">=3.12"`. Ruff's `target-version` and pyrefly's `python-version` match it; change all three together.
    - Always use `pyproject.toml` for metadata (PEP 621). Never create `setup.py`, `setup.cfg`, or `requirements.txt`.

    ### Test code

    - Framework: pytest
    - Run tests: `uv run pytest`
    - Test files go in `tests/` at the project root
    - Test file naming: `test_*.py`
    - Test function naming: `test_*`
    - No `__init__.py` needed in `tests/`
    - Coverage: `uv add --dev coverage`, then `uv run coverage run -m pytest` and `uv run coverage report`

    ### Configure continuous integration

    Use `astral-sh/setup-uv` in GitHub Actions. Let uv install Python and sync the locked environment; do not add a separate `actions/setup-python` step unless the workflow has a specific non-uv requirement.

    ### Lint and format code

    - Tool: ruff (handles both linting and formatting)
    - Lint: `uv run ruff check .`
    - Lint and auto-fix: `uv run ruff check --fix .`
    - Format: `uv run ruff format .`
    - Check formatting: `uv run ruff format --check .`
    - Configuration lives in `pyproject.toml` under `[tool.ruff]`

    ### Check types

    - Tool: pyrefly
    - Run: `uv run pyrefly check`
    - Configuration lives in `pyproject.toml` under `[tool.pyrefly]`. Keep its `default` preset. Never switch it to `strict` or `all`.
    - Type hints are optional. Add them where they help a reader, such as a public function. Do not add them only to quiet the checker.
    - Silence a false error on its line with `# pyrefly: ignore[<code>]`.

    ### Follow code style

    - Follow ruff's defaults for formatting (88 char line length, double quotes, spaces)
    - Import sorting is handled by ruff (`isort` rules enabled via `select = ["I"]`)
    - Do not add `# type: ignore` comments without an error code

    ### Install pre-commit hooks

    - Tool: prek (preferred) or pre-commit
    - Install prek hooks: `uvx prek install`
    - Install pre-commit hooks: `uvx pre-commit install`
    - Do not install pre-commit or prek with pip. Use `uvx`.

    ### Avoid these practices

    - Do not create or activate virtual environments manually. uv manages `.venv/` automatically.
    - Do not install packages globally or with `pip install`.
    - Do not create `requirements.txt` for dependency management. Use `pyproject.toml` and `uv.lock`.
    - Do not run `python setup.py` commands.
    - Do not add dependencies to pyproject.toml by hand. Use `uv add`. Tool tables such as `[tool.ruff]` are edited by hand; after any hand edit to a dependency list, run `uv lock`.
    - If you must edit pyproject.toml directly, write dev dependencies under `[dependency-groups]` (PEP 735), not the legacy `[tool.uv.dev-dependencies]` table.

    ### Choose libraries

    Reach for the standard library first. When it does not cover the job, use these defaults:

    - HTTP: `httpx`, not `requests` or `urllib`.
    - Paths: `pathlib`, not `os.path`.
    - Records: `dataclasses`. Use `pydantic` only to validate data from outside the program.
    - Messages from library code: `logging`, not `print`.
    - Shell commands: `subprocess.run` with a list of arguments, not `os.system` or `shell=True`.
    - Dates and times: timezone-aware `datetime` with `zoneinfo`, not naive datetimes or `pytz`.
    - Reading TOML: `tomllib`.

    ### Pick versions

    - Never write a version number from memory. Your training data is older than today's releases.
    - Resolve versions with tools: `uv add` picks the latest compatible release, `uv tree --outdated` lists what is behind, `uv python list` shows which Python releases exist, and `uvx prek autoupdate` bumps hook revisions.
    - Before you claim a version does not exist or is not stable, check with one of those.
    - Upgrade everything: `uv lock --upgrade && uvx prek autoupdate`.
