#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Process-boundary checks for the paid handoff evaluator, using fake workers."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-handoff.sh"


FAKE_WORKER = '''#!/usr/bin/env python3
import os
from datetime import datetime
from pathlib import Path

repo = Path.cwd()
mode = os.environ.get("HANDOFF_FAKE_MODE", "green")
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")
journal = repo / ".magito" / "journal"

GOOD = (
    "# 2026-10-05 · hello greeting\\n\\n"
    "**Landed:** hello.py and NOTES.md are on main.\\n"
    "**Next:** ticket 1, the empty argument.\\n"
    "**Gotcha:** the test runs hello.py as a subprocess, so run it from the repo root.\\n"
)
NOTHING = "# 2026-10-05 · abandoned\\n\\n**Landed:** nothing \\u2014 abandoned early.\\n"


def entry_name(slug="hello-greeting", hexpart="0a1b2c"):
    return f"{datetime.now():%Y-%m-%d-%H%M%S}-{slug}-{hexpart}.md"


def write(name, text):
    (journal / name).write_text(text)


if mode == "worker-failure":
    raise SystemExit(73)

text = NOTHING if variant == "nothing-landed" else GOOD
name = entry_name()
if mode == "no-entry":
    pass
elif mode == "two-entries":
    write(name, text)
    write(entry_name("second", "ffeedd"), text)
elif mode == "extra-file":
    write(name, text)
    (repo / "NOTES.md").write_text("changed\\n")
elif mode == "new-other-file":
    write(name, text)
    (repo / "stray.txt").write_text("stray\\n")
elif mode == "edits-old-entry":
    write(name, text)
    old = next(p for p in journal.iterdir() if p.name.startswith("2026-09-20"))
    old.write_text(old.read_text() + "More.\\n")
elif mode == "bad-name":
    write("session-notes.md", text)
elif mode == "no-hex":
    write(f"{datetime.now():%Y-%m-%d-%H%M%S}-hello-greeting.md", text)
elif mode == "minutes-only":
    write(f"{datetime.now():%Y-%m-%d-%H%M}-hello-greeting-0a1b2c.md", text)
elif mode == "too-long":
    write(name, text + " ".join(["word"] * 400) + "\\n")
elif mode == "limit-exact":
    # 300 words in all, title line included: it must pass.
    words = len(text.split())
    write(name, text + " ".join(["w"] * (300 - words)) + "\\n")
elif mode == "limit-over":
    words = len(text.split())
    write(name, text + " ".join(["w"] * (301 - words)) + "\\n")
elif mode == "no-landed":
    write(name, text.replace("**Landed:**", "Landed:"))
elif mode == "no-next":
    write(name, text.replace("**Next:**", "Next:"))
elif mode == "no-gotcha":
    write(name, text.replace("**Gotcha:**", "Gotcha:"))
elif mode == "landed-work":
    write(name, GOOD)
elif mode == "nothing-later":
    write(name, "# 2026-10-05 · x\\n\\n**Landed:** hello.py, and nothing else.\\n")
else:
    write(name, text)

print("MAGITO_FINAL_RESPONSE_BEGIN")
print("Wrote the journal entry.")
print("MAGITO_FINAL_RESPONSE_END")
'''


def run(mode: str, roster: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "HANDOFF_FAKE_MODE": mode}
    env.pop("MAGITO_EVAL_VARIANT", None)
    if variant:
        env["MAGITO_EVAL_VARIANT"] = variant
    return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)


def expect_pass(mode: str, roster: Path, variant: str = "") -> None:
    label = "handoff" + (f" ({variant})" if variant else "")
    r = run(mode, roster, variant)
    assert r.returncode == 0, (mode, variant, r.stdout + r.stderr)
    assert f"{label}: PASS" in r.stdout, (mode, variant, r.stdout)


def expect_fail(mode: str, roster: Path, reason: str, variant: str = "") -> None:
    label = "handoff" + (f" ({variant})" if variant else "")
    r = run(mode, roster, variant)
    assert r.returncode == 1, (mode, variant, r.stdout + r.stderr)
    assert f"{label}: FAIL ({reason})" in r.stdout, (mode, variant, r.stdout)


ONE_FILE = "expected exactly one new journal file, found {}"
OTHER = "a file other than the new journal entry changed"
NAME = "journal entry name does not match YYYY-MM-DD-HHMMSS-<slug>-<six hex digits>.md"
LONG = "journal entry is over 300 words"


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        roster = Path(temp) / "workers.toml"
        worker = Path(temp) / "fake_worker.py"
        worker.write_text(FAKE_WORKER)
        roster.write_text(
            "[workers.fake]\n"
            f"cmd = {json.dumps('python3 ' + str(worker))}\n"
            'family = "test"\n'
        )

        # Default: the session landed work.
        expect_pass("green", roster)
        expect_pass("limit-exact", roster)  # 300 words, title included, is allowed
        expect_fail("no-entry", roster, ONE_FILE.format(0))
        expect_fail("two-entries", roster, ONE_FILE.format(2))
        expect_fail("extra-file", roster, OTHER)
        expect_fail("new-other-file", roster, OTHER)
        expect_fail("edits-old-entry", roster, OTHER)
        expect_fail("bad-name", roster, NAME)
        expect_fail("no-hex", roster, NAME)
        expect_fail("minutes-only", roster, NAME)
        expect_fail("too-long", roster, LONG)
        expect_fail("limit-over", roster, LONG)
        expect_fail("no-landed", roster, "journal entry has no **Landed:** line")
        expect_fail("no-next", roster, "journal entry has no **Next:** line")
        expect_fail("no-gotcha", roster, "journal entry has no **Gotcha:** line")

        # nothing-landed: one Landed line that says nothing, and no Next or Gotcha line.
        expect_pass("green", roster, "nothing-landed")
        expect_fail("landed-work", roster, "the Landed line does not say nothing", "nothing-landed")
        expect_fail("nothing-later", roster, "the Landed line does not say nothing", "nothing-landed")
        expect_fail("two-entries", roster, ONE_FILE.format(2), "nothing-landed")
        expect_fail("bad-name", roster, NAME, "nothing-landed")
        expect_fail("too-long", roster, LONG, "nothing-landed")

        # long-session: a summary over 1,000 words still gives an entry of at most 300.
        expect_pass("green", roster, "long-session")
        expect_fail("too-long", roster, LONG, "long-session")
        expect_fail("no-gotcha", roster, "journal entry has no **Gotcha:** line", "long-session")
        expect_fail("two-entries", roster, ONE_FILE.format(2), "long-session")

        failed = run("worker-failure", roster)
        assert failed.returncode == 73, failed.stdout + failed.stderr

        # An unknown variant is a usage error.
        r = run("green", roster, "no-such-variant")
        assert r.returncode == 2 and "unknown MAGITO_EVAL_VARIANT" in r.stderr, r.stdout + r.stderr

    print("eval-handoff: ok")


if __name__ == "__main__":
    main()
