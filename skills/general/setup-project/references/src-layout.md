# src/ layout scaffold

{{project}}/
├── pyproject.toml              # from pyproject.toml.template
├── README.md
├── .pre-commit-config.yaml     # from pre-commit-config.yaml.template
├── src/
│   └── {{package}}/
│       └── __init__.py         # empty, or just a __version__
└── tests/
    └── test_smoke.py

test_smoke.py contains exactly:

    import {{package}}

    def test_imports():
        assert {{package}} is not None

Placeholders: {{project}} = directory name; {{package}} = importable name
(lowercase, underscores). Fill both everywhere; never leave a {{...}} in
written output.
