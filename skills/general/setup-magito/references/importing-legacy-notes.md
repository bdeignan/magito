# Importing legacy notes into the session journal

Read this **only when `setup-magito`'s inventory actually finds pre-magito notes.** If the scan turned up nothing, skip it — never open this file to "check."

The goal: carry forward what a repo already knew, as proper session-journal entries, without destroying the originals and without flooding the journal with over-long dumps.

## What counts as legacy notes

Anything that held session knowledge before magito did: an old magito handoff file under `~/.magito/handoffs/<repo-slug>.md`, a `NOTES.md` or `TODO.md` at the repo root, a `docs/decisions/` folder, a `.beads/` (or similar) task database, or a store the user names when asked. A `CHANGELOG.md`, a README, or anything already version-controlled as product docs is **not** legacy notes — leave it.

## The one rule that governs everything: never destructive

Originals stay exactly where they are. The import only ever **writes new files** under `.magito/journal/`. It never edits, moves, or deletes the source. If detail is later needed, the original is still on disk. Say this to the user up front.

## Procedure

1. **Read the source and propose a mapping — before writing anything.** Decide how many entries the material becomes and what each one covers. Usually far fewer entries than the source has lines: a long `TODO.md` is often one entry ("open threads at magito adoption"), not one per item. Show the user the proposed mapping — entry count, each entry's topic, and which source material each pulls from.

2. **Ask whether it is worth carrying at all.** A pile of stale TODOs usually is not. Let the user cut entries from the mapping, merge them, or decline the whole import. Write nothing until they confirm.

3. **Summarize to the journal word cap — do not paste.** Each entry obeys the same limit as a normal session entry: aim ~200 words, 300 hard ceiling (the cap lives in the session-journal standard in `CLAUDE.md` — follow it there, don't restate a number here). Imported material is usually several times over it. Compress to the durable point, the way a handoff entry would. **This is exactly what the retired `journal import` got wrong** — it pasted entries several times over the cap, and those bloated entries became the precedent the next session copied. Summarize; the source keeps the detail.

4. **Timestamp from the source, so imported entries sort against real ones.** Take the date from the source — a file's mtime, or a date written in the note. Get a correctly-formatted, unique filename from `~/.magito/bin/journal name "<topic-slug>"`, then **replace the leading date in what it prints with the source date**, keeping the random hex suffix it generated. The filename is `YYYY-MM-DD-HHMMSS-<slug>-<hex>.md`; only the date part changes. This keeps the journal's uniqueness guarantee (the hex) while making the entry sort where it belongs in history, not at today.

   Example: `journal name "old-auth-decisions"` prints `.../2026-08-05-141230-old-auth-decisions-a1b2c3.md`. If the source note is dated 2025-11-02, write the file as `.../2025-11-02-141230-old-auth-decisions-a1b2c3.md`.

5. **Write each entry with your file-writing tool** (not through `journal` — it only reads). Use the normal entry shape: a dated `#` header line and the summary body. Mark it as imported in the body (e.g. a short "imported from `NOTES.md`" note) so a later reader knows its provenance.

6. **Confirm what landed.** List the new filenames, and remind the user the originals are untouched and can be deleted by hand whenever they choose — that is their call, not the import's.

## Checklist

- [ ] Mapping shown and confirmed before any write
- [ ] Every entry under the journal word cap
- [ ] Source files untouched
- [ ] Filenames carry the source date, not today's
- [ ] Provenance noted in each imported entry
