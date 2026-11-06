#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Lists the repo's written rules that bear on a change, for a review to check it against.

    python3 standards.py <base>

For the committed diff from <base> to HEAD, it prints three sections: the standards docs
(CLAUDE.md or AGENTS.md, then docs/agents/GLOSSARY.md and docs/agents/CONVENTIONS.md), the
ADRs that bear on the changed files (newest first within each chain), and the doc lines
that name something the diff removed or renamed. See ../references/standards-review.md
for the procedure that uses this output.

Exit: 0 ok, 2 a usage error, a base git cannot resolve, or a failed git command.
Stdlib only, by design.
"""
import re
import subprocess
import sys
from pathlib import Path

STANDARDS_USAGE = "usage: standards.py <base>"
STANDARDS_HEADINGS = (
    "## Standards docs",
    "## ADRs, newest first within each chain",
    "## Doc lines that name something this diff removed or renamed",
)
GENERIC_NAMES = {"SKILL.md", "README.md", "INDEX.md"}  # matched only with their folder
ADR_PATH = re.compile(r"docs/adr/(\d{4})-[^/]*\.md")
BACKTICKED = re.compile(r"`([^`\n]+)`")
PLAIN_WORD = re.compile(r"[A-Za-z0-9]+")  # dropped: says too little to search for


def die(code, msg):
    print(f"standards.py: {msg}", file=sys.stderr)
    sys.exit(code)


def git_text(root, *args):
    """stdout of a git command in root; exits 2 with git's message when it fails."""
    r = subprocess.run(["git", "-C", root, *args], capture_output=True)
    if r.returncode != 0:
        die(2, f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "replace")


def blobs(root, rev, paths):
    """{path: text} for each path that exists at rev, read in one git cat-file call."""
    paths = list(paths)
    if not paths:
        return {}
    spec = "".join(f"{rev}:{p}\n" for p in paths).encode()
    r = subprocess.run(["git", "-C", root, "cat-file", "--batch"], input=spec, capture_output=True)
    if r.returncode != 0:
        die(2, f"git cat-file failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    out, pos, texts = r.stdout, 0, {}
    for p in paths:
        end = out.index(b"\n", pos)
        header = out[pos:end].split()
        pos = end + 1
        if header[-1] == b"missing":
            continue
        size = int(header[2])
        texts[p] = out[pos:pos + size].decode("utf-8", "replace")
        pos += size + 1
    return texts


def diff_changes(root, mb):
    """[(status, old_path, new_path)] for the committed diff from mb to HEAD."""
    raw = git_text(root, "diff", "--name-status", "-z", "-M", mb, "HEAD").split("\0")
    changes, i = [], 0
    while i < len(raw) and raw[i]:
        status = raw[i]
        if status[0] in "RC":
            changes.append((status[0], raw[i + 1], raw[i + 2]))
            i += 3
        else:
            changes.append((status[0], raw[i + 1], raw[i + 1]))
            i += 2
    return changes


def adr_cites(text, n):
    """Whether text cites ADR number n: `ADR 13`, `ADR 0013`, `ADR-0013`, or `adr/0013`."""
    return bool(re.search(rf"(?<![A-Za-z])ADR[ -]?0*{n}(?!\d)", text)) or f"adr/{n:04d}" in text


def adr_section(adrs, changed_paths):
    """The ADR lines: seeded by changed file names, extended along links to later ADRs,
    grouped into chains."""
    keys = set()
    for p in changed_paths:
        path = Path(p)
        keys.add(f"{path.parent.name}/{path.name}" if path.name in GENERIC_NAMES else path.name)
    found = {n for n, (_, text) in adrs.items() if any(k in text for k in keys)}

    def linked(a, b):  # a < b
        return adr_cites(adrs[b][1], a) or adr_cites(adrs[a][1], b)

    todo = list(found)
    while todo:
        a = todo.pop()
        for b in adrs:
            if b > a and b not in found and linked(a, b):
                found.add(b)
                todo.append(b)
    chains, seen = [], set()
    for n in sorted(found, reverse=True):
        if n in seen:
            continue
        chain, stack = set(), [n]
        while stack:
            x = stack.pop()
            if x in chain:
                continue
            chain.add(x)
            stack.extend(y for y in found if y not in chain and linked(min(x, y), max(x, y)))
        seen |= chain
        chains.append(sorted(chain, reverse=True))
    blocks = []
    for chain in chains:
        lines = []
        for n in chain:
            path, text = adrs[n]
            status = next((l.replace("**", "") for l in text.splitlines()
                           if l.startswith(("Status:", "**Status:**"))), "Status: none")
            lines.append(f"{path} — {status}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def vanished_names(changes, before, after):
    """Names the diff removed: deleted or renamed paths, and backticked terms a changed
    Markdown file stopped mentioning. Single plain words are dropped."""
    names = set()
    for status, old, new in changes:
        if status in "DR":
            names.update({old, Path(old).stem})
        if old.endswith(".md") and status != "A":
            gone_from = after.get(new, "") if status != "D" else ""
            names.update(t for t in BACKTICKED.findall(before.get(old, "")) if t not in gone_from)
    return {n for n in names if n and not PLAIN_WORD.fullmatch(n)}


def standards(base):
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode != 0:
        die(2, "not inside a git work tree")
    root = r.stdout.strip()
    if subprocess.run(["git", "-C", root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                      capture_output=True).returncode != 0:
        die(2, f"cannot resolve base '{base}'. {STANDARDS_USAGE}")
    mb = git_text(root, "merge-base", base, "HEAD").strip()
    tracked = [p for p in git_text(root, "ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0") if p]
    changes = diff_changes(root, mb)

    docs = []
    if "CLAUDE.md" in tracked:
        docs.append("CLAUDE.md")
    elif "AGENTS.md" in tracked:
        docs.append("AGENTS.md")
    docs += [p for p in ("docs/agents/GLOSSARY.md", "docs/agents/CONVENTIONS.md") if p in tracked]

    adr_paths = [p for p in tracked if ADR_PATH.fullmatch(p)]
    adr_texts = blobs(root, "HEAD", adr_paths)
    adrs = {int(ADR_PATH.fullmatch(p).group(1)): (p, adr_texts.get(p, "")) for p in adr_paths}
    adr_block = adr_section(adrs, {p for _, old, new in changes for p in (old, new)})

    changed_md = [c for c in changes if c[1].endswith(".md")]
    before = blobs(root, mb, {old for _, old, _ in changed_md})
    after = blobs(root, "HEAD", {new for s, _, new in changed_md if s != "D"})
    searched = [p for p in tracked if p.endswith(".md")
                and not p.startswith(("docs/adr/", "docs/intent/"))]
    texts = blobs(root, "HEAD", searched)
    groups = []
    for name in sorted(vanished_names(changes, before, after)):
        hits = [f"{p}:{i}: {line}" for p in sorted(texts)
                for i, line in enumerate(texts[p].splitlines(), 1) if name in line]
        if hits:
            groups.append("\n".join([f"`{name}`", *hits]))

    bodies = ["\n".join(docs), adr_block, "\n\n".join(groups)]
    print("\n\n".join(f"{h}\n{b or 'None.'}" for h, b in zip(STANDARDS_HEADINGS, bodies)))
    sys.exit(0)


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        die(2, STANDARDS_USAGE)
    standards(args[0])


if __name__ == "__main__":
    main()
