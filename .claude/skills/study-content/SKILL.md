---
name: study-content
description: Adds or updates topics, lessons and quizzes in the Study app (docs/ in this repo, the offline study PWA on GitHub Pages). Use whenever the user asks for a new topic, new lessons, more quiz questions, or edits to existing study content, e.g. "add a topic on Kubernetes", "write 5 lessons on Postgres indexing", "add a lesson on AgentCore Evaluations", "the memory quiz is too easy".
---

# Adding Study content

Study is a static, offline-first app in `docs/`. Content is data: a catalogue (`docs/content/index.json`) and one HTML fragment per lesson. The app shell (`app.js`, `styles.css`, `index.html`, `sw.js`) normally doesn't change when adding content.

Follow these steps in order. Steps 1, 5 and 6 are not optional.

## 1. Plan the topic or lessons

- **Topic**: a short title, a one-sentence description, and a kebab-case `id` (it becomes the folder name and URL: `#/t/<id>`).
- **Lessons**: 4–7 lessons per topic, ordered so each builds on the last. The first is an orientation (what it is, the map of parts, the main decision). The last should usually be a hands-on "build it" capstone that combines the earlier lessons.
- Unless the user says otherwise, confirm the lesson list with the user in one line, then go ahead without waiting for a reply.

## 2. Ground it in current sources

Accuracy matters more than polish. The user studies this on the Tube and can't fact-check it there.

- **AWS topics**: use the AWS MCP server (`search_documentation`, `read_documentation`) and any relevant skill in `.claude/skills/` (`amazon-bedrock`'s `references/` covers AgentCore, for example).
- **Libraries, frameworks and SDKs**: use context7.
- **Anything else**: official docs via web search or fetch.
- Prefer exact numbers, limits, API and field names from the sources over memory. If you can't verify a detail, leave it out or say plainly that it may vary ("check the current docs for the default").
- Label preview or recently launched features as such ("in preview at the time of writing").
- Never invent API names, CLI flags or config fields. If a code sample uses a shape you couldn't confirm, simplify it to what you could.

## 3. Write each lesson

Copy `templates/lesson.html` as the starting point. File name: `docs/content/<topic-id>/NN-slug.html` (e.g. `03-memory.html`).

**Shape**
- 1,000–1,500 words of body text, about 9–12 minutes including the quiz. Calculate the reading time as words ÷ 200, plus about 3 minutes for the quiz.
- **No `<h1>`**: the app renders the title and summary from `index.json`.
- Open with 1–3 paragraphs naming the problem the concept solves, before any definitions.
- Use `<h2>` sections (and `<h3>` within them). Aim for 5–8 sections.
- End with `<h2>Takeaways</h2>` and 4–6 bullets that restate the lesson's key ideas.
- Then the quiz block (step 4).

**Voice**
- Write in second person and plain English, for a smart engineer who's new to the topic. Explain *why* before *how*.
- Use concrete examples throughout ("a coding agent that spends 20 minutes installing dependencies…").
- Keep code samples short, real and annotated with prose afterwards ("A few things to notice:"). Escape `<`, `>` and `&` inside `<pre><code>` as `&lt;`, `&gt;` and `&amp;`.
- Use British English, matching the existing lessons.

**Components** (styled in `styles.css`; use these instead of inventing new markup)

| Need | Markup |
|---|---|
| Key idea, tip, warning | `<div class="callout key\|warn"><span class="label">Key idea</span>…</div>` (plain `callout` for a tip) |
| Step-by-step flow or request path | `<ol class="flow"><li><b>Step</b><span>Detail</span></li>…</ol>` |
| Map of parts or services | `<div class="tiles"><div><b>Name</b><span>One line</span></div>…</div>` |
| Comparisons and options | `<table>` with `<thead>` (the app wraps it to scroll on phones) |
| Optional deep dive | `<details><summary>…</summary>…</details>` |

Use 1–3 callouts per lesson, and keep each `.flow` diagram to 4–7 steps. Inline `<svg>` is fine, but **no external images, scripts, fonts or iframes**: everything must work offline.

## 4. Write the quiz

The quiz is a JSON block at the end of the lesson file:

```html
<script type="application/json" class="quiz">
[
  {
    "q": "Question text",
    "options": ["A", "B", "C", "D"],
    "answer": 1,
    "explain": "Why B is right, and why the tempting wrong answer is wrong."
  }
]
</script>
```

- Write 5–6 questions with 4 options each. `answer` is the 0-based index into `options`.
- The app **shuffles options**, so never write "all of the above", "both A and B" or anything else that depends on order.
- Test understanding, not recall. At least half the questions should be scenarios ("Your container builds but never starts. Most likely cause?").
- Distractors must be plausible: real features used wrongly, or common misconceptions. Don't include joke options.
- `explain` is 1–2 sentences. Say why the right answer is right, and where it helps, why the most tempting wrong answer is wrong.
- Every question must be answerable from the lesson text.

## 5. Register it in the catalogue

Add the lesson (and the topic if it's new) to `docs/content/index.json`:

```json
{ "id": "memory", "file": "03-memory.html", "title": "…", "minutes": 10, "summary": "One sentence, shown under the title." }
```

The service worker reads this file to decide what to download for offline use. **A lesson that isn't listed here won't work offline.**

Don't bump `CACHE` in `docs/sw.js` for content-only changes. Bump it (e.g. `study-v1` → `study-v2`) only if `app.js`, `styles.css`, `index.html` or icons changed.

## 6. Check it

Run the checker from the repo root. It validates the catalogue, files, quiz JSON, answer indexes, length and offline safety:

```bash
python3 .claude/skills/study-content/scripts/check_content.py
```

Fix every error. Treat warnings as prompts to look again, not hard failures.

Then preview it with the `study` config in `.claude/launch.json` (port 8765) at the mobile preset, and check:
- the new lessons open from the topic page,
- nothing scrolls sideways (`document.documentElement.scrollWidth` equals the viewport width),
- the quiz renders and scores.

## 7. Publish

Pages deploys automatically from `main` → `/docs`. Commit and push only when the user asks or approves. After pushing, the site updates in about a minute, and phones pick up the new content in the background the next time the app is opened with signal.

If the user also wants the topic on their Kindle, run `python3 scripts/build_epub.py <topic-id>` to rebuild `dist/<topic-id>.epub` (it's gitignored), then send it the way they choose. Ask before sending anything.

Tell the user how many lessons were added, the word count and number of questions for each, and anything you couldn't verify.
