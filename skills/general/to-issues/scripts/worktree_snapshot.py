#!/usr/bin/env python3
"""Capture and compare the files a spec reviewer must leave unchanged."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def die(message: str) -> None:
    print(f"worktree_snapshot.py: {message}", file=sys.stderr)
    raise SystemExit(2)


def git_paths(root: Path, *args: str) -> set[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", *args],
        text=False,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        die(result.stderr.decode(errors="replace").strip())
    return {Path(item.decode()) for item in result.stdout.split(b"\0") if item}


def file_digest(path: Path) -> dict[str, str]:
    if path.is_symlink():
        return {"kind": "symlink", "value": path.readlink().as_posix()}
    if not path.exists():
        return {"kind": "missing", "value": ""}
    if not path.is_file():
        return {"kind": "other", "value": ""}
    return {
        "kind": "file",
        "value": hashlib.sha256(path.read_bytes()).hexdigest(),
        # git tracks the executable bit, so a reviewer must not flip it either.
        "exec": "yes" if path.stat().st_mode & 0o111 else "no",
    }


def review_paths(root: Path, review_dir: Path) -> set[Path]:
    try:
        relative = review_dir.resolve().relative_to(root.resolve())
    except ValueError:
        die("review directory must be inside the main worktree")
    if not review_dir.exists():
        return set()
    paths = {
        relative / path.relative_to(review_dir)
        for path in review_dir.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if review_dir.is_symlink():
        paths.add(relative)
    return paths


def capture(root: Path, review_dir: Path, output: Path) -> None:
    root = root.resolve()
    tracked = git_paths(root)
    untracked = git_paths(root, "--others", "--exclude-standard")
    reviewed = review_paths(root, review_dir)
    paths = tracked | untracked | reviewed
    content = {path.as_posix(): file_digest(root / path) for path in sorted(paths)}
    output.write_text(json.dumps(content, sort_keys=True, indent=2) + "\n")


def compare(before: Path, after: Path) -> None:
    old = json.loads(before.read_text())
    new = json.loads(after.read_text())
    changed = sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))
    if changed:
        print("reviewer changed:")
        for path in changed:
            print(path)
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) == 5 and sys.argv[1] == "capture":
        capture(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
        return
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]))
        return
    die("usage: worktree_snapshot.py capture <main-root> <review-dir> <snapshot> | compare <before> <after>")


if __name__ == "__main__":
    main()
