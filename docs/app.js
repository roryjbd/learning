// Study: a tiny offline-first study app. Hash routes:
//   #/                    home (topics)
//   #/t/<topic>           lesson list for a topic
//   #/t/<topic>/<lesson>  lesson + quiz

const app = document.getElementById('app');
const crumb = document.getElementById('crumb');
const back = document.getElementById('back');
const bar = document.getElementById('bar');
const foot = document.getElementById('foot');

// ---- Progress storage (per device, best effort) ----
const STORE_KEY = 'study.v1';

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) || { lessons: {}, last: null };
  } catch {
    return { lessons: {}, last: null };
  }
}
let state = loadState();

function saveState() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch { /* private mode etc. */ }
}

function lessonState(topicId, lessonId) {
  const key = `${topicId}/${lessonId}`;
  return (state.lessons[key] ||= {});
}

// ---- Content ----
let catalogue = null;

async function getCatalogue() {
  if (!catalogue) {
    const res = await fetch('content/index.json');
    catalogue = await res.json();
  }
  return catalogue;
}

async function getLesson(topic, lesson) {
  const res = await fetch(`content/${topic.id}/${lesson.file}`);
  if (!res.ok) throw new Error(`Couldn't load ${lesson.file}`);
  const html = await res.text();
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  const quizEl = tpl.content.querySelector('script.quiz');
  const quiz = quizEl ? JSON.parse(quizEl.textContent) : [];
  quizEl?.remove();
  return { body: tpl.content, quiz };
}

// ---- Helpers ----
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function setChrome({ title, backHref }) {
  crumb.textContent = title;
  document.title = title === 'Study' ? 'Study' : `${title} · Study`;
  back.hidden = !backHref;
  if (backHref) back.href = backHref;
}

function topicProgress(topic) {
  const done = topic.lessons.filter((l) => lessonState(topic.id, l.id).done).length;
  return { done, total: topic.lessons.length };
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---- Views ----
async function renderHome() {
  const cat = await getCatalogue();
  setChrome({ title: 'Study' });

  let resume = '';
  const last = state.last;
  if (last) {
    const topic = cat.topics.find((t) => t.id === last.topic);
    const lesson = topic?.lessons.find((l) => l.id === last.lesson);
    if (topic && lesson) {
      resume = `
        <div class="section-label">Pick up where you left off</div>
        <a class="card resume" href="#/t/${topic.id}/${lesson.id}">
          <div class="eyebrow">${esc(topic.title)}</div>
          <h3>${esc(lesson.title)}</h3>
          <p>${esc(lesson.summary)}</p>
        </a>`;
    }
  }

  const topics = cat.topics.map((t) => {
    const { done, total } = topicProgress(t);
    const pct = Math.round((done / total) * 100);
    return `
      <a class="card" href="#/t/${t.id}">
        <h2>${esc(t.title)}</h2>
        <p>${esc(t.description)}</p>
        <div class="meta"><span>${total} lessons</span><span>~${t.lessons.reduce((m, l) => m + l.minutes, 0)} min</span><span>${done}/${total} done</span></div>
        <div class="meter"><span style="width:${pct}%"></span></div>
      </a>`;
  }).join('');

  app.innerHTML = `
    <div class="hello">
      <h1>What are we learning?</h1>
      <p>Short lessons with a quiz at the end. Works offline.</p>
    </div>
    ${resume}
    <div class="section-label">Topics</div>
    ${topics}`;
}

async function renderTopic(topicId) {
  const cat = await getCatalogue();
  const topic = cat.topics.find((t) => t.id === topicId);
  if (!topic) return renderMissing();
  setChrome({ title: topic.title, backHref: '#/' });

  const { done, total } = topicProgress(topic);
  const rows = topic.lessons.map((l, i) => {
    const s = lessonState(topic.id, l.id);
    const score = s.best != null ? `<span class="pill ${s.best === s.total ? 'good' : ''}">Best ${s.best}/${s.total}</span>` : '';
    return `
      <a class="card" href="#/t/${topic.id}/${l.id}">
        <div class="lesson-row">
          <div class="lesson-num ${s.done ? 'done' : ''}">${s.done ? '✓' : i + 1}</div>
          <div>
            <h3>${esc(l.title)}</h3>
            <p>${esc(l.summary)}</p>
            <div class="meta"><span>${l.minutes} min read</span>${score}</div>
          </div>
        </div>
      </a>`;
  }).join('');

  app.innerHTML = `
    <div class="topic-head">
      <h1>${esc(topic.title)}</h1>
      <p>${esc(topic.description)}</p>
      <div class="meter"><span style="width:${Math.round((done / total) * 100)}%"></span></div>
    </div>
    <div class="section-label">${done}/${total} lessons done</div>
    ${rows}`;
}

async function renderLesson(topicId, lessonId) {
  const cat = await getCatalogue();
  const topic = cat.topics.find((t) => t.id === topicId);
  const idx = topic ? topic.lessons.findIndex((l) => l.id === lessonId) : -1;
  if (idx < 0) return renderMissing();
  const lesson = topic.lessons[idx];
  const next = topic.lessons[idx + 1];
  setChrome({ title: topic.title, backHref: `#/t/${topic.id}` });

  const s = lessonState(topic.id, lesson.id);
  const savedScroll = s.scroll;
  const { body, quiz } = await getLesson(topic, lesson);
  state.last = { topic: topic.id, lesson: lesson.id };
  saveState();

  app.innerHTML = `
    <header class="lesson-head">
      <div class="eyebrow">Lesson ${idx + 1} of ${topic.lessons.length} · ${lesson.minutes} min</div>
      <h1>${esc(lesson.title)}</h1>
      <p class="lede">${esc(lesson.summary)}</p>
    </header>
    <article></article>
    <section class="quiz" id="quiz"></section>
    <div class="next-up" id="next"></div>`;

  const article = app.querySelector('article');
  article.append(body);
  // Wide tables scroll inside their own box instead of the page.
  article.querySelectorAll('table').forEach((t) => {
    const wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    t.replaceWith(wrap);
    wrap.append(t);
  });

  renderQuiz(app.querySelector('#quiz'), quiz, topic, lesson);

  if (next) {
    app.querySelector('#next').innerHTML = `
      <div class="section-label">Up next</div>
      <a class="card" href="#/t/${topic.id}/${next.id}">
        <h3>${esc(next.title)}</h3><p>${esc(next.summary)}</p>
      </a>`;
  }

  // Put the reader back where they stopped last time.
  if (savedScroll > 0.02 && savedScroll < 0.97) {
    requestAnimationFrame(() => window.scrollTo(0, savedScroll * scrollRange()));
  }
}

function renderQuiz(root, questions, topic, lesson) {
  if (!questions.length) return;
  const s = lessonState(topic.id, lesson.id);
  const answers = new Array(questions.length).fill(null);

  root.innerHTML = `
    <h2>Check your understanding</h2>
    <p class="sub">${questions.length} questions. Tap an answer to see why.${s.best != null ? ` Your best so far: ${s.best}/${s.total}.` : ''}</p>
    <div class="qs"></div>
    <div class="result"></div>`;
  const list = root.querySelector('.qs');
  const result = root.querySelector('.result');

  questions.forEach((q, qi) => {
    const card = document.createElement('div');
    card.className = 'q';
    card.innerHTML = `<div class="q-num">Question ${qi + 1}</div><div class="q-text">${esc(q.q)}</div>`;
    const order = shuffle(q.options.map((text, i) => ({ text, i })));
    const buttons = order.map(({ text, i }) => {
      const b = document.createElement('button');
      b.className = 'opt';
      b.type = 'button';
      b.textContent = text;
      b.dataset.i = i;
      card.append(b);
      return b;
    });
    const explain = document.createElement('div');
    card.append(explain);

    card.addEventListener('click', (e) => {
      const btn = e.target.closest('.opt');
      if (!btn || answers[qi] !== null) return;
      const picked = Number(btn.dataset.i);
      answers[qi] = picked;
      const right = picked === q.answer;
      buttons.forEach((b) => {
        b.disabled = true;
        const i = Number(b.dataset.i);
        if (i === q.answer) b.classList.add('correct');
        else if (i === picked) b.classList.add('wrong');
        else b.classList.add('dim');
      });
      explain.className = 'explain';
      explain.innerHTML = `<b class="${right ? 'good' : 'bad'}">${right ? 'Correct.' : 'Incorrect.'}</b> ${esc(q.explain)}`;
      if (answers.every((a) => a !== null)) finish();
    });
    list.append(card);
  });

  function finish() {
    const score = answers.filter((a, i) => a === questions[i].answer).length;
    const total = questions.length;
    s.done = true;
    s.total = total;
    s.best = Math.max(s.best ?? 0, score);
    saveState();
    const msg = score === total ? 'All answers correct.'
      : score >= total * 0.6 ? 'Read the explanations for the questions you got wrong.'
      : 'Reread the sections covering the questions you got wrong.';
    result.innerHTML = `
      <div class="score">
        <div class="big">${score}/${total}</div>
        <p>${msg}</p>
        <div class="btn-row">
          <button class="btn" type="button" data-act="retry">Retake quiz</button>
          <a class="btn primary" href="#/t/${topic.id}">Back to lessons</a>
        </div>
      </div>`;
    result.querySelector('[data-act=retry]').addEventListener('click', () => {
      renderQuiz(root, questions, topic, lesson);
      root.scrollIntoView({ behavior: 'smooth' });
    });
  }
}

function renderMissing() {
  setChrome({ title: 'Not found', backHref: '#/' });
  app.innerHTML = `<p class="empty">That page doesn't exist. <a href="#/">Go home</a></p>`;
}

// ---- Reading progress ----
function scrollRange() {
  return Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
}

let scrollTimer = null;
// Off while a page is being swapped in, so the jump to the top doesn't
// overwrite the saved reading position.
let trackScroll = false;
window.addEventListener('scroll', () => {
  const route = parseRoute();
  const frac = Math.min(1, window.scrollY / scrollRange());
  bar.style.width = route.lesson ? `${frac * 100}%` : '0';
  if (!route.lesson || !trackScroll) return;
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(() => {
    lessonState(route.topic, route.lesson).scroll = frac;
    saveState();
  }, 250);
}, { passive: true });

// ---- Router ----
function parseRoute() {
  const [, t, topic, lesson] = location.hash.split('/');
  return t === 't' ? { topic, lesson } : {};
}

async function route() {
  const { topic, lesson } = parseRoute();
  trackScroll = false;
  clearTimeout(scrollTimer);
  bar.style.width = '0';
  window.scrollTo(0, 0);
  try {
    if (topic && lesson) await renderLesson(topic, lesson);
    else if (topic) await renderTopic(topic);
    else await renderHome();
  } catch (err) {
    console.error(err);
    app.innerHTML = `<p class="empty">Couldn't load this page. If you're offline, open it once with a connection first.</p>`;
  }
  app.focus({ preventScroll: true });
  requestAnimationFrame(() => { trackScroll = true; });
}

window.addEventListener('hashchange', route);
route();

// ---- Offline support ----
if ('serviceWorker' in navigator) {
  // New content arrived in the background: drop the in-memory catalogue and
  // redraw list pages. Lesson pages are left alone so a reader isn't moved.
  const refreshView = () => {
    catalogue = null;
    if (!parseRoute().lesson) route();
  };
  navigator.serviceWorker.addEventListener('message', (e) => {
    if (e.data?.type === 'content-updated') refreshView();
  });
  // A new app version took over (e.g. after a cache bump).
  let hadController = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (hadController) refreshView();
    hadController = true;
  });
  // Home-screen apps often resume from memory without reloading, so check for
  // new content whenever the app comes back to the foreground.
  let lastCheck = Date.now();
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible' || Date.now() - lastCheck < 30_000) return;
    lastCheck = Date.now();
    fetch('content/index.json').catch(() => {});
    navigator.serviceWorker.getRegistration().then((r) => r?.update()).catch(() => {});
  });

  navigator.serviceWorker.register('sw.js').then(() => navigator.serviceWorker.ready).then(() => {
    foot.textContent = 'Saved for offline use.';
  }).catch(() => {
    foot.textContent = 'Offline mode unavailable in this browser.';
  });
} else {
  foot.textContent = 'Offline mode unavailable in this browser.';
}
