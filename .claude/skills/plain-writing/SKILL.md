---
name: plain-writing
description: House writing style for this repo - plain, factual, no hype. Use whenever writing or editing any reader-facing text here, including Study lessons, quizzes, topic and lesson summaries in index.json, the README, UI strings in docs/app.js, commit messages and PR descriptions. Load it before writing, then run its checker.
---

# Plain writing

The reader is an engineer studying on a phone with no signal. They want accurate information, explained clearly, in as few words as it takes. They don't want to be sold to or entertained.

The chosen style is **plain explanatory**: second person, explain *why* before *how*, but state everything directly. No scene-setting, no marketing voice, no filler.

## Rules

1. **Lead with the fact.** Open a lesson or section with what the thing is, or what problem it solves, in one or two plain sentences. Don't open with a story, a question or a hypothetical.
2. **Explain why in concrete terms.** Give the reason as a cost, a limit, a failure or a risk ("a small model is more likely to get a hard task wrong"), not as a feeling ("you've probably wondered…").
3. **No hype or evaluative adjectives.** Don't call anything powerful, seamless, exciting, trivial or huge. If something is faster, cheaper or better, say by how much and who measured it.
4. **Attribute claims.** Vendor statements and benchmarks are "GitHub reports…" or "AWS says…", never stated as plain fact. Note known caveats.
5. **Be exact.** Use exact names, numbers, limits, dates and statuses from the source. Label previews ("public preview at the time of writing, November 2026"). If you can't verify something, leave it out or say it's unverified.
6. **Examples are brief and labelled.** Write "For example, a coding agent that spends 20 minutes installing dependencies loses that work when the session times out", not a narrative that starts with "Imagine…".
7. **One idea per sentence.** Keep paragraphs short. Cut sentences that only introduce the next sentence ("Here's how it works:", "This is the part people trip over.").
8. **No rhetorical framing.** Don't write "X is the answer", "enter X", "that's where X comes in", "the catch", "the good news", "the headline", "time to…" or "let's…".
9. **Callouts are for facts the reader must not miss.** Use only these labels: `Key point`, `Note`, `Warning`, `Limit`, `Security`. Use one to three per lesson.
10. **Takeaways and quiz explanations are terse.** Takeaways are short factual bullets. An `explain` field says why the answer is right, and why the most tempting wrong answer is wrong, in one or two sentences, with no praise ("Great!") or scolding.
11. **UI text is neutral.** Use "Correct." and "Incorrect.", not "Nice!" or "Not quite."
12. **British English**, with no exclamation marks in prose.

## Before and after

Before:

> Here's a decision you've probably made a hundred times: you open Copilot Chat, look at the model picker, and wonder whether this task needs the expensive frontier model or whether the fast cheap one will do. […] **Copilot Fusion** is GitHub's answer.

After:

> Before Fusion, you chose a model for each request. A large model costs more credits; a small one is more likely to get a hard task wrong. The Auto option chose for you, but it still sent each request to a single model.
>
> Copilot Fusion replaces Auto. It became generally available on 28 October 2026 on all Copilot plans. You choose an effort level (Standard, High or Max), and Fusion decides which models to use.

What changed: the scene-setting, the rhetorical question and "GitHub's answer" are gone. The problem is stated as a cost trade-off, and the facts (date, plans, what you choose) come first.

## Check it

Run from the repo root:

```bash
python3 .claude/skills/plain-writing/scripts/check_style.py
```

It scans lesson HTML (prose and quizzes), `docs/content/index.json`, `README.md` and the UI strings in `docs/app.js` for banned phrases, exclamation marks and callout labels outside the allowed set. It exits non-zero on any error. A clean run doesn't prove the text is plain, so read it back against the rules too.

When a banned word is genuinely the right term (for example a product name), rephrase if you can. If you can't, add the exact phrase to `ALLOW` in the script with a comment saying why.
