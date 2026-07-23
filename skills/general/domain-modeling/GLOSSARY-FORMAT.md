# GLOSSARY.md Format

## Structure

```md
# {Context Name}

{One or two sentences: what this context is and why it exists.}

## Language

**Feature**:
A column used as model input, engineered from raw fields; never includes the target.
_Avoid_: variable, predictor, signal

**Target**:
The column the model predicts.
_Avoid_: label (use only for classification), outcome, y

**Leakage**:
Target or future information reaching a feature, inflating offline metrics.
_Avoid_: contamination, peeking
```

## Rules

- **Be opinionated.** When several words name one concept, pick the best and list the rest under `_Avoid_`.
- **Keep definitions tight.** One or two sentences. Define what it IS, not what it does.
- **Project-specific terms only.** General programming or ML concepts (timeout, dataframe, gradient) don't belong, even if used heavily. Ask: is this unique to *this* project's domain? Only then add it.
- **Group under subheadings** when natural clusters emerge; a flat list is fine otherwise.

## Multi-context repos

A `CONTEXT-MAP.md` at the root lists each context, where it lives, and how they relate:

```md
# Context Map

## Contexts

- [Ingestion](./src/ingestion/GLOSSARY.md) — pulls and validates raw source data
- [Modeling](./src/modeling/GLOSSARY.md) — trains and evaluates models

## Relationships

- **Ingestion → Modeling**: Ingestion emits a validated `feature frame`; Modeling consumes it.
```

If `CONTEXT-MAP.md` exists, read it to find the contexts. If only a `docs/agents/GLOSSARY.md` exists, single context. If neither, create `docs/agents/GLOSSARY.md` lazily when the first term resolves.
