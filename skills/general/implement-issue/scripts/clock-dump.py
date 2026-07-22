#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
clock-dump.py — point-in-time JSONL snapshot of the session ledger.

Reads ~/.magito/ledger.db (or $MAGITO_LEDGER_DB, if set — same override
`clock` honors) read-only and prints one JSON object per line for every row
in clock_in, clock_out, and session_event, each tagged with "_table". JSONL,
not CSV: a clock_out or session_event summary can contain newlines, and CSV
breaks on that.

Usage:
    python3 clock-dump.py [--table clock_in|clock_out|session_event] [--out FILE]

Stdlib only, matching clock itself. Opens the database in SQLite's read-only
URI mode, so a dump can never write to the ledger.
"""
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

TABLES = ("clock_in", "clock_out", "session_event")


def db_path() -> Path:
    override = os.environ.get("MAGITO_LEDGER_DB")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".magito" / "ledger.db"


def main():
    ap = argparse.ArgumentParser(description="Dump the session ledger to JSONL, one object per line.")
    ap.add_argument("--table", choices=TABLES, help="Dump only this table (default: all three).")
    ap.add_argument("--out", help="Write JSONL here instead of stdout.")
    args = ap.parse_args()

    path = db_path()
    if not path.exists():
        print(f"clock-dump: no ledger at {path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    out = open(args.out, "w") if args.out else sys.stdout
    tables = (args.table,) if args.table else TABLES
    try:
        for table in tables:
            # table is drawn only from the fixed TABLES tuple above (argparse
            # choices=), never from free text, so this is not injectable.
            for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid"):
                record = {"_table": table, **dict(row)}
                out.write(json.dumps(record) + "\n")
    finally:
        conn.close()
        if args.out:
            out.close()


if __name__ == "__main__":
    main()
