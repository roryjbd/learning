#!/usr/bin/env python3
"""Check reader-facing text against the plain-writing house style.

Run from the repo root:  python3 .claude/skills/plain-writing/scripts/check_style.py
Exits non-zero if any errors are found.
"""
import json
import re
import sys
from pathlib import Path

# Words and phrases that signal hype, filler or rhetorical framing.
BANNED = [
    # hype and evaluative adjectives
    r"powerful", r"seamless(ly)?", r"effortless(ly)?", r"game[- ]chang\w*", r"revolution\w*",
    r"cutting[- ]edge", r"best[- ]in[- ]class", r"world[- ]class", r"supercharg\w*", r"unlock\w*",
    r"unleash\w*", r"magic(al|ally)?", r"amazing(ly)?", r"incredibl[ey]", r"awesome", r"exciting",
    r"delight\w*", r"leverag\w*", r"empower\w*", r"next level", r"trivial(ly)?", r"massive(ly)?",
    r"huge(ly)?", r"dramatic(ally)?", r"stunning", r"boost\w*", r"blazing", r"breathtaking",
    r"painless(ly)?", r"terrible", r"brilliant",
    r"painful(ly)?", r"clever(ly)?", r"hand-rolled", r"beefy", r"tempting", r"awkward",
    # filler and hedging intensifiers
    r"simply", r"easily", r"of course", r"obviously", r"basically", r"really", r"very",
    r"super", r"for free", r"even simpler",
    r"actually", r"lots of", r"a lot of",
    # rhetorical framing
    r"imagine", r"here's", r"here is", r"you've probably", r"ever wondered", r"let's", r"time to",
    r"that's where", r"enter the", r"(is|as) [A-Z]\w+'s answer", r"the answer is", r"the catch",
    r"the trick", r"the good news", r"the bad news", r"the best part", r"the interesting part",
    r"the beauty", r"headline", r"the pitch", r"trust, but verify", r"not sure\?",
    r"the easy part", r"the hard part", r"rule of thumb", r"heads up", r"gotcha",
]
BANNED_RE = re.compile(r"\b(" + "|".join(BANNED) + r")\b", re.I)

# Exact phrases that contain a banned word but are allowed. Say why.
ALLOW = [
    "superset",  # technical term
]

LABELS = {"Key point", "Note", "Warning", "Limit", "Security"}
LABEL_RE = re.compile(r'<span class="label">(.*?)</span>')
CODE_RE = re.compile(r"<(pre|code)\b.*?</\1>", re.S)
TAG_RE = re.compile(r"<[^>]+>")

errors = []


def scan(where, text):
    for line_no, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for m in BANNED_RE.finditer(line):
            if any(a in low for a in ALLOW):
                continue
            errors.append(f"{where}:{line_no}: banned phrase '{m.group(0)}': {line.strip()[:90]}")
        if re.search(r"[A-Za-z)]!(\s|$)", line):
            errors.append(f"{where}:{line_no}: exclamation mark: {line.strip()[:90]}")


def strip_html(html):
    html = CODE_RE.sub(" ", html)
    return TAG_RE.sub(" ", html)


def check_lesson(path):
    raw = path.read_text(encoding="utf-8")
    for label in LABEL_RE.findall(raw):
        if label not in LABELS:
            errors.append(f"{path}: callout label '{label}' not in {sorted(LABELS)}")
    # Keep line numbers: blank out code and tags line by line.
    no_code = CODE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), raw)
    quiz = re.search(r'<script type="application/json" class="quiz">(.*?)</script>', no_code, re.S)
    prose = no_code.replace(quiz.group(1), "\n" * quiz.group(1).count("\n")) if quiz else no_code
    scan(str(path), TAG_RE.sub(" ", prose))
    if quiz:
        try:
            for i, q in enumerate(json.loads(quiz.group(1)), 1):
                text = " ".join([q.get("q", ""), q.get("explain", "")] + q.get("options", []))
                scan(f"{path} Q{i}", text)
        except json.JSONDecodeError:
            pass  # check_content.py reports bad quiz JSON


def main():
    for path in sorted(Path("docs/content").glob("*/*.html")):
        check_lesson(path)
    index = Path("docs/content/index.json")
    if index.exists():
        for t in json.loads(index.read_text())["topics"]:
            scan(f"{index} [{t['id']}]", f"{t['title']} {t['description']}")
            for l in t["lessons"]:
                scan(f"{index} [{t['id']}/{l['id']}]", f"{l['title']} {l['summary']}")
    readme = Path("README.md")
    if readme.exists():
        scan("README.md", CODE_RE.sub(" ", re.sub(r"```.*?```", " ", readme.read_text(), flags=re.S)))
    app = Path("docs/app.js")
    if app.exists():
        strings = re.findall(r"'([^'\n]{12,})'|`([^`]{12,})`", app.read_text())
        for s in ("".join(p) for p in strings):
            if " " in s and not s.strip().startswith(("<", "#", "/", ".")):
                scan("docs/app.js", strip_html(re.sub(r"\$\{[^}]*\}", " ", s)))

    for e in errors:
        print("ERROR ", e)
    print(f"\n{len(errors)} style error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
