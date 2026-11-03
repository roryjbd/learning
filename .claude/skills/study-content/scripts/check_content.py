#!/usr/bin/env python3
"""Validate Study content: catalogue, lesson files, quizzes and offline safety.

Run from the repo root:  python3 .claude/skills/study-content/scripts/check_content.py
Exits non-zero if there are errors. Warnings are printed but don't fail.
"""
import json
import re
import sys
from pathlib import Path

CONTENT = Path("docs/content")
QUIZ_RE = re.compile(r'<script type="application/json" class="quiz">(.*?)</script>', re.S)
EXTERNAL_RE = re.compile(r'<(img|script|link|iframe|video|audio|source)\b[^>]*\b(src|href)\s*=\s*["\']?(https?:)?//', re.I)
ORDER_WORDS = re.compile(r"\b(all|none|both) of the above\b|\bboth [A-D] and [A-D]\b", re.I)

errors, warnings = [], []


def err(where, msg):
    errors.append(f"ERROR  {where}: {msg}")


def warn(where, msg):
    warnings.append(f"warn   {where}: {msg}")


def check_quiz(where, raw):
    try:
        quiz = json.loads(raw)
    except json.JSONDecodeError as e:
        return err(where, f"quiz JSON doesn't parse ({e})")
    if not isinstance(quiz, list) or not quiz:
        return err(where, "quiz must be a non-empty list")
    if not 4 <= len(quiz) <= 8:
        warn(where, f"{len(quiz)} quiz questions (aim for 5-6)")
    for i, q in enumerate(quiz, 1):
        qw = f"{where} Q{i}"
        if not isinstance(q, dict):
            err(qw, "question must be an object")
            continue
        for key in ("q", "options", "answer", "explain"):
            if key not in q:
                err(qw, f"missing '{key}'")
        opts = q.get("options", [])
        if not isinstance(opts, list) or len(opts) < 3:
            err(qw, "needs at least 3 options")
            continue
        if len(opts) != 4:
            warn(qw, f"{len(opts)} options (aim for 4)")
        if len(set(opts)) != len(opts):
            err(qw, "duplicate options")
        ans = q.get("answer")
        if not isinstance(ans, int) or not 0 <= ans < len(opts):
            err(qw, f"answer {ans!r} isn't a valid index into options")
        if any(ORDER_WORDS.search(o) for o in opts):
            err(qw, "options are shuffled, so avoid 'all/none of the above' style answers")
        if not str(q.get("explain", "")).strip():
            err(qw, "empty explain")
    return len(quiz)


def check_lesson(where, path):
    html = path.read_text(encoding="utf-8")
    m = QUIZ_RE.search(html)
    if not m:
        err(where, "no quiz block")
        body, n_q = html, 0
    else:
        body = html[: m.start()]
        n_q = check_quiz(where, m.group(1)) or 0
        if html[m.end():].strip():
            warn(where, "content after the quiz block")
    if re.search(r"<h1\b", body, re.I):
        err(where, "has an <h1>; the app renders the title from index.json")
    if EXTERNAL_RE.search(html):
        err(where, "loads an external resource; lessons must work offline")
    if "<h2>Takeaways</h2>" not in body:
        warn(where, "no '<h2>Takeaways</h2>' section")
    for code in re.findall(r"<pre><code>(.*?)</code></pre>", body, re.S):
        if re.search(r"<(?!/?(b|i|em|strong|span)\b)[A-Za-z/]", code):
            err(where, "unescaped '<' inside <pre><code> (use &lt;)")
            break
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    if not 800 <= words <= 1900:
        warn(where, f"{words} words (aim for 1,000-1,500)")
    return words, n_q


def main():
    index_path = CONTENT / "index.json"
    try:
        catalogue = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR  {index_path}: {e}")
        return 1

    topic_ids = set()
    for topic in catalogue.get("topics", []):
        tid = topic.get("id", "?")
        if tid in topic_ids:
            err(tid, "duplicate topic id")
        topic_ids.add(tid)
        for key in ("id", "title", "description", "lessons"):
            if key not in topic:
                err(tid, f"topic missing '{key}'")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", tid):
            err(tid, "topic id should be kebab-case")

        listed, lesson_ids = set(), set()
        print(f"\n{topic.get('title', tid)}")
        for lesson in topic.get("lessons", []):
            lid = lesson.get("id", "?")
            where = f"{tid}/{lid}"
            if lid in lesson_ids:
                err(where, "duplicate lesson id")
            lesson_ids.add(lid)
            for key in ("id", "file", "title", "minutes", "summary"):
                if key not in lesson:
                    err(where, f"lesson missing '{key}'")
            if not isinstance(lesson.get("minutes"), int):
                err(where, "minutes must be an integer")
            path = CONTENT / tid / lesson.get("file", "")
            listed.add(path.name)
            if not path.is_file():
                err(where, f"file not found: {path}")
                continue
            words, n_q = check_lesson(where, path)
            print(f"  {lesson.get('minutes', '?'):>3} min  {words:>5} words  {n_q} questions  {lesson.get('title', lid)}")

        folder = CONTENT / tid
        if folder.is_dir():
            for f in sorted(folder.glob("*.html")):
                if f.name not in listed:
                    warn(tid, f"{f.name} isn't listed in index.json, so it won't appear or work offline")

    print()
    for line in warnings + errors:
        print(line)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
