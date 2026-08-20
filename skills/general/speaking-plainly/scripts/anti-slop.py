#!/usr/bin/env python3
"""anti-slop.py — lint text against magito's canonical banned-voice list.

Reads `../references/anti-ai-markers.md` as data (never forks it) and flags the banned
words, phrases, and structures it defines. Sentence length and passive voice are the
job of the sibling `readability.py`, not this script.

The load-bearing problem: magito's product is prose that *quotes* slop as teaching
examples, so a naive scan flags the rule file and every example. This masks the same
regions the hooks blank before judging — fenced code, inline code, and double-quoted
spans — and skips the rule file itself by name.

Severity: an unqualified banned word/phrase/structure is an ERROR; a qualified word
("navigate (figurative)") is a WARNING, since only a human can tell the figurative use
from the literal one. Exit 1 on any error, else 0.

Stdlib only, Python 3.11+. Usage: anti-slop.py [FILE|-]   (default: stdin)
Verify with synthetic stdin, e.g.:  printf 'We leverage it.' | ./anti-slop.py -
"""
import sys
import re
import os

RULE_FILE = os.path.join(os.path.dirname(__file__), "..", "references", "anti-ai-markers.md")
RULE_BASENAME = "anti-ai-markers.md"

# Known contractions to flag.  Only full-word forms — bare 's after arbitrary words is
# skipped because it's indistinguishable from possessive 's without a real parser.
CONTRACTIONS = [
    "don't", "won't", "can't", "isn't", "aren't", "wasn't", "weren't",
    "hasn't", "haven't", "hadn't", "doesn't", "didn't",
    "couldn't", "shouldn't", "wouldn't", "mustn't",
    "it's", "that's", "there's", "what's", "here's", "let's",
    "I'm", "I'll", "I've", "I'd",
    "we'll", "we're", "we've", "we'd",
    "they'll", "they're", "they've", "they'd",
    "you'll", "you're", "you've", "you'd",
    "he's", "she's", "who's",
]
_CONTRACTION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(c) for c in
                        sorted(CONTRACTIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def normalize(text):
    """Fold smart quotes and dashes to ASCII so patterns match either form.
    Every replacement is one character for one, so byte offsets stay put."""
    return (text
            .replace("“", '"').replace("”", '"')
            .replace("‘", "'").replace("’", "'")
            .replace("—", "-").replace("–", "-"))


def blank(match):
    """Replace a matched region with spaces, keeping newlines so line numbers hold."""
    return re.sub(r"[^\n]", " ", match.group(0))


def mask_examples(text):
    """Blank the regions where slop is quoted as an example, not committed as prose:
    fenced code blocks, inline code spans, then double-quoted spans."""
    text = re.sub(r"```.*?```", blank, text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", blank, text)
    text = re.sub(r"\*+[^*\n]+\*+", blank, text)
    text = re.sub(r'"[^"\n]*"', blank, text)
    return text


def parse_rules(rule_text):
    """Pull the three enforceable lists out of anti-ai-markers.md.

    Returns (words, phrase_patterns, structure_patterns), where words is a list of
    (term, qualified, note) and the pattern lists hold compiled regexes."""
    sections = {}
    current = None
    for line in rule_text.splitlines():
        m = re.match(r"^##\s+(.*)", line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    words = []
    for line in sections.get("Banned Words", []):
        line = line.strip()
        if not line or line.lower().startswith("never use"):
            continue
        # Split on commas outside parentheses, so a comma inside a "(qualifier)" note
        # doesn't shred the entry.
        for raw in re.split(r",\s*(?![^()]*\))", line):
            entry = raw.strip()
            if not entry:
                continue
            m = re.match(r"^(.*?)\s*(?:\(([^)]*)\))?$", entry)
            term = m.group(1).strip()
            note = m.group(2)
            if term:
                words.append((term, note is not None, note))

    phrases = []
    for line in sections.get("Banned Phrases", []):
        for quoted in re.findall(r'"([^"]*)"', line):
            phrases.append((quoted, re.compile(_template_regex(quoted), re.IGNORECASE)))

    structures = []
    for line in sections.get("Banned Structures", []):
        for quoted in re.findall(r'"([^"]*)"', line):
            structures.append((quoted, re.compile(_template_regex(quoted), re.IGNORECASE)))

    return words, phrases, structures


def _word_regex(term):
    """Match a banned word or multiword term on word boundaries, whitespace flexible."""
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(r"\b" + body + r"\b", re.IGNORECASE)


def _template_regex(template):
    """Turn a banned phrase or structure template into a regex. Handles all the
    notations the list uses: '[a/b/c]' bracket alternation, '...' wildcard, standalone
    X/Y/Z placeholders, and flexible whitespace that spans newlines (so a multi-line
    structure like 'No X. No Y. Just Z.' still matches)."""
    template = normalize(template)
    out = []
    for seg in re.split(r"(\[[^\]]*\]|\.\.\.)", template):
        if seg == "...":
            out.append(r".*?")
        elif seg.startswith("[") and seg.endswith("]"):
            alts = [re.escape(a.strip()) for a in seg[1:-1].split("/")]
            out.append("(?:" + "|".join(alts) + ")")
        else:
            for tok in re.split(r"((?<![A-Za-z])[XYZ](?![A-Za-z]))", seg):
                out.append(r".+?" if tok in ("X", "Y", "Z") else re.escape(tok))
    # re.escape renders spaces as "\ " (for verbose mode); collapse any run of
    # escaped-or-plain spaces into a single flexible-whitespace matcher.
    return re.sub(r"(?:\\ | )+", r"\\s+", "".join(out))


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def lint(text, is_rule_file=False):
    """Return (findings, errors, warnings). A finding is a dict with line, severity,
    kind, label. Detection runs on masked text; display uses the original lines."""
    if is_rule_file:
        return [], 0, 0

    original_lines = text.splitlines()
    norm = normalize(text)
    masked = mask_examples(norm)

    with open(RULE_FILE, "r", encoding="utf-8") as f:
        words, phrases, structures = parse_rules(f.read())

    findings = []

    def add(lineno, severity, kind, label):
        findings.append({
            "line": lineno,
            "severity": severity,
            "kind": kind,
            "label": label,
            "context": original_lines[lineno - 1].strip() if 0 < lineno <= len(original_lines) else "",
        })

    for term, qualified, note in words:
        for m in _word_regex(term).finditer(masked):
            severity = "WARNING" if qualified else "ERROR"
            label = term + (f" ({note})" if note else "")
            add(line_of(masked, m.start()), severity, "word", label)

    for quoted, pattern in phrases:
        for m in pattern.finditer(masked):
            add(line_of(masked, m.start()), "ERROR", "phrase", f'"{quoted}"')

    for quoted, pattern in structures:
        for m in pattern.finditer(masked):
            add(line_of(masked, m.start()), "ERROR", "structure", f'"{quoted}"')

    for m in _CONTRACTION_RE.finditer(masked):
        add(line_of(masked, m.start()), "ERROR", "contraction", m.group(0))

    findings.sort(key=lambda f: (f["line"], 0 if f["severity"] == "ERROR" else 1))
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARNING")
    return findings, errors, warnings


def main():
    is_rule_file = False
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        path = sys.argv[1]
        is_rule_file = os.path.basename(path) == RULE_BASENAME
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("Empty input. Nothing to lint.")
        sys.exit(0)

    findings, errors, warnings = lint(text, is_rule_file=is_rule_file)

    if is_rule_file:
        print("Rule file (anti-ai-markers.md) — skipped; it is all examples.")
        sys.exit(0)

    if not findings:
        print("No banned-voice findings.")
        sys.exit(0)

    for f in findings:
        print(f"line {f['line']:<4} {f['severity']:<7} {f['kind']:<9} {f['label']}")
        if f["context"]:
            print(f"          | {f['context']}")

    print()
    print(f"{errors} error(s), {warnings} warning(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
