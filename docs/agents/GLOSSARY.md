<!-- GLOSSARY.md — project-specific vocabulary → its non-obvious meaning. Rules (from
     domain-modeling/GLOSSARY-FORMAT.md):
       • Project-specific terms ONLY. General programming or ML words (timeout, dataframe,
         gradient) never belong, however heavily used — ask "is this unique to THIS
         project's domain?" and only then add it.
       • Be opinionated: when several words name one concept, pick the best and list the
         rest under `_Avoid_`.
       • Keep definitions tight — one or two sentences; say what the term IS, not what it does.
       • Group under subheadings when natural clusters emerge; a flat list is fine otherwise.
     Add terms lazily, the moment one resolves — don't invent terms to fill this file.
     Auto-loaded while small; at scale, split into per-area GLOSSARY.md near the code and
     route them from INDEX.md. -->

# magito — glossary

magito's project-specific vocabulary. Kept deliberately small: `CLAUDE.md` carries most of
the domain language adequately at this size (see `docs/adr/0001-adopt-adr-log.md`). A term
earns a place here only once it is genuinely contested.

## Language

**ticket** — one unit of tracked work, whatever backend holds it: a GitHub issue, a Jira
ticket, a markdown file under `.scratch/`. Skills say *ticket* when the backend is unknown or
irrelevant, which is most of the time. _Avoid_ "issue" as the generic word — it is GitHub's
name for its own object, and using it generically is how backends got hardcoded into skills
in the first place. "Issue" stays correct when you mean a GitHub issue specifically, as
`#144` or in the name of the `to-issues` skill.

**tracker operation** — a named verb a skill calls instead of a backend command: *list open
tickets*, *fetch a ticket*, *publish a ticket*, *close a ticket*, and the rest.
[`issue-tracker.md`](./issue-tracker.md) is the one file that says how each is performed in
this repo; the canonical list of the operations themselves lives in
`skills/general/setup-magito/references/issue-tracker-other.md.template`.
