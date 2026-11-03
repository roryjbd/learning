# learning

`docs/` is **Study**, a small offline-first web app of lessons and quizzes. It's built to be saved to an iPhone home screen and read on the Tube with no signal. There's no build step: just static files, served by GitHub Pages from `main` → `/docs`.

## On your phone

1. Open the Pages URL in Safari while you have signal.
2. Share → **Add to Home Screen**.
3. Open it **once from the home screen icon** while still online. The home-screen app has its own storage, separate from Safari, and that first launch is when it downloads every lesson.
4. After that it works offline. Progress and quiz scores are saved on the device.

When you push new content, the app picks it up in the background the next time you open it with signal, and shows it on the open after that.

## Run locally

```bash
python3 -m http.server 8765 --directory docs
```

## Adding content

- **A lesson** is an HTML fragment in `docs/content/<topic>/`, with its quiz in a `<script type="application/json" class="quiz">` block at the end. Each question looks like `{ "q", "options", "answer" (index), "explain" }`, and options are shuffled when shown.
- **List it** in `docs/content/index.json` under its topic. The service worker reads this file to decide what to download for offline use.
- **A new topic** is a new entry in `topics` plus a folder under `docs/content/`.
- If you change `app.js`, `styles.css` or `index.html`, bump `CACHE` in `docs/sw.js`. That makes phones replace the old copies cleanly.

Lesson components: `.callout` (add `.key` or `.warn`), `ol.flow` for step diagrams, `.tiles` for a two-column grid, and plain `table`, `pre` and `details`.
