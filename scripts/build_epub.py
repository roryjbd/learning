#!/usr/bin/env python3
"""Build an EPUB per Study topic from docs/content, for Kindle and other e-readers.

Usage (from the repo root):
    python3 scripts/build_epub.py            # every topic
    python3 scripts/build_epub.py agentcore  # one topic

Writes dist/<topic-id>.epub. Each lesson becomes a chapter, followed by its
quiz and, on a new page, the answers with explanations. On macOS a cover is
rendered with Quick Look (qlmanage); elsewhere the book has no cover image.
"""
import datetime
import html
import json
import random
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "docs" / "content"
DIST = ROOT / "dist"
SITE = "https://roryjbd.github.io/learning/"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

CSS = """
body { font-family: serif; line-height: 1.5; }
h1 { font-size: 1.6em; margin: 0 0 0.3em; }
h2 { font-size: 1.25em; margin: 1.4em 0 0.4em; }
h3 { font-size: 1.05em; margin: 1.2em 0 0.3em; }
p.summary { font-style: italic; margin-bottom: 1.2em; }
code { font-family: monospace; font-size: 0.9em; }
pre { font-family: monospace; font-size: 0.75em; white-space: pre-wrap; border-left: 3px solid #888; padding-left: 0.6em; margin: 0.8em 0; }
.callout { border: 1px solid #999; border-left: 4px solid #333; padding: 0.4em 0.7em; margin: 1em 0; }
.callout .label { display: block; font-family: sans-serif; font-size: 0.75em; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; }
.flow li { margin-bottom: 0.5em; }
.flow span, .tiles span { display: block; }
.tiles div { border: 1px solid #999; padding: 0.3em 0.6em; margin: 0.4em 0; }
table { border-collapse: collapse; margin: 0.8em 0; font-size: 0.85em; }
th, td { border: 1px solid #999; padding: 0.25em 0.4em; text-align: left; vertical-align: top; }
.details { border: 1px dashed #999; padding: 0.4em 0.7em; margin: 1em 0; }
.quiz-q { margin: 1em 0 0.3em; font-weight: bold; }
.quiz-opts { list-style-type: upper-alpha; margin-top: 0.2em; }
.answers { page-break-before: always; }
.answers p { margin: 0.6em 0; }
.title-page { text-align: center; margin-top: 3em; }
"""


class XHTMLWriter(HTMLParser):
    """Re-serialise an HTML fragment as well-formed XHTML for e-readers."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0  # inside <script>

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.skip += 1
            return
        if self.skip:
            return
        # <details> isn't supported on Kindle: flatten to a boxed div.
        if tag == "details":
            tag, attrs = "div", [("class", "details")]
        elif tag == "summary":
            self.out.append("<p><strong>")
            return
        attr_text = "".join(f' {k}="{html.escape(v or k, quote=True)}"' for k, v in attrs)
        self.out.append(f"<{tag}{attr_text}{' /' if tag in VOID else ''}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and not self.skip:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "script":
            self.skip -= 1
            return
        if self.skip or tag in VOID:
            return
        if tag == "details":
            tag = "div"
        elif tag == "summary":
            self.out.append("</strong></p>")
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def to_xhtml(fragment):
    w = XHTMLWriter()
    w.feed(fragment)
    w.close()
    return "".join(w.out)


def page(title, body):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">
<head><meta charset="utf-8" /><title>{html.escape(title)}</title><link rel="stylesheet" type="text/css" href="style.css" /></head>
<body>
{body}
</body>
</html>
"""


def quiz_xhtml(lesson_id, quiz):
    """Questions with lettered options, then answers on a new page.

    Options are shuffled with a fixed seed per question, so correct answers
    aren't always in the same position but the book is the same every build.
    """
    letters = "ABCDEFGH"
    qs, answers = [], []
    for i, q in enumerate(quiz, 1):
        order = list(range(len(q["options"])))
        random.Random(f"{lesson_id}-{i}").shuffle(order)
        opts = "".join(f"<li>{html.escape(q['options'][j])}</li>" for j in order)
        qs.append(f'<p class="quiz-q">{i}. {html.escape(q["q"])}</p><ol class="quiz-opts">{opts}</ol>')
        right = letters[order.index(q["answer"])]
        answers.append(f"<p><strong>{i}. {right}</strong>: {html.escape(q['explain'])}</p>")
    return (
        "<h2>Check your understanding</h2>" + "".join(qs)
        + '<div class="answers"><h2>Answers</h2>' + "".join(answers) + "</div>"
    )


def render_cover(title, out_png):
    """Render a simple cover PNG via Quick Look. Returns True on success."""
    if not shutil.which("qlmanage"):
        return False
    words, lines, line = title.split(), [], ""
    for w in words:  # wrap the title at ~14 characters per line
        if line and len(line) + len(w) > 14:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    lines.append(line)
    text = "".join(
        f'<text x="140" y="{720 + i * 190}" font-family="Helvetica, Arial, sans-serif" font-weight="700" font-size="170" fill="#ffffff">{html.escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    # Quick Look renders a square, so draw a 1600x1600 cover and pad it to
    # Kindle's 1600x2560 portrait shape with sips afterwards.
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1600" viewBox="0 0 1600 1600">
<rect width="1600" height="1600" fill="#c2550f"/>
<rect x="140" y="460" width="220" height="16" fill="#fbe9dc"/>
{text}
<text x="140" y="1420" font-family="Helvetica, Arial, sans-serif" font-size="80" fill="#fbe9dc">Study notes and quizzes</text>
</svg>"""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "cover.svg"
        src.write_text(svg, encoding="utf-8")
        subprocess.run(["qlmanage", "-t", "-s", "1600", "-o", tmp, str(src)],
                       capture_output=True, check=False)
        rendered = Path(tmp) / "cover.svg.png"
        if not rendered.exists():
            return False
        subprocess.run(["sips", "-p", "2560", "1600", "--padColor", "C2550F", str(rendered), "--out", str(out_png)],
                       capture_output=True, check=False)
        if not out_png.exists():
            return False
    return True


def build(topic):
    tid, title = topic["id"], topic["title"]
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, SITE + tid)}"
    modified = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    files = {"style.css": CSS}
    chapters = []  # (filename, title)

    intro = (
        f'<div class="title-page"><h1>{html.escape(title)}</h1>'
        f"<p>{html.escape(topic['description'])}</p></div>"
        f"<h2>How to use this book</h2>"
        f"<p>There are {len(topic['lessons'])} lessons, each about ten minutes long. Every lesson ends "
        f"with a short quiz. Answer it in your head, then turn the page for the answers and explanations.</p>"
        f"<p>The same lessons, with interactive quizzes, are at {html.escape(SITE)}.</p>"
    )
    files["intro.xhtml"] = page(title, intro)
    chapters.append(("intro.xhtml", "About this book"))

    for n, lesson in enumerate(topic["lessons"], 1):
        raw = (CONTENT / tid / lesson["file"]).read_text(encoding="utf-8")
        start = raw.find('<script type="application/json" class="quiz">')
        body_html = raw[:start] if start >= 0 else raw
        quiz = json.loads(raw[start:].split(">", 1)[1].rsplit("</script>", 1)[0]) if start >= 0 else []
        name = f"ch{n:02d}.xhtml"
        heading = f"{n}. {lesson['title']}"
        body = (
            f"<h1>{html.escape(heading)}</h1>"
            f'<p class="summary">{html.escape(lesson["summary"])}</p>'
            + to_xhtml(body_html)
            + (quiz_xhtml(lesson["id"], quiz) if quiz else "")
        )
        files[name] = page(heading, body)
        chapters.append((name, heading))

    nav_items = "".join(f'<li><a href="{f}">{html.escape(t)}</a></li>' for f, t in chapters)
    files["nav.xhtml"] = page("Contents", f'<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{nav_items}</ol></nav>')

    # NCX for older Kindle firmware that ignores the EPUB 3 nav.
    nav_points = "".join(
        f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{html.escape(t)}</text></navLabel><content src="{f}"/></navPoint>'
        for i, (f, t) in enumerate(chapters, 1)
    )
    files["toc.ncx"] = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{book_id}"/></head>
<docTitle><text>{html.escape(title)}</text></docTitle>
<navMap>{nav_points}</navMap>
</ncx>
"""

    with tempfile.TemporaryDirectory() as tmp:
        cover_png = Path(tmp) / "cover.png"
        has_cover = render_cover(title, cover_png)
        cover_bytes = cover_png.read_bytes() if has_cover else None

    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="css" href="style.css" media-type="text/css"/>']
    spine = []
    if has_cover:
        manifest.append('<item id="cover-image" href="cover.png" media-type="image/png" properties="cover-image"/>')
        manifest.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
        files["cover.xhtml"] = page(title, '<div style="text-align:center"><img src="cover.png" alt="Cover" style="max-width:100%;height:auto" /></div>')
        spine.append('<itemref idref="cover" linear="no"/>')
    for f, _ in chapters:
        item_id = f.split(".")[0]
        manifest.append(f'<item id="{item_id}" href="{f}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{item_id}"/>')

    files["content.opf"] = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="en-GB">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{book_id}</dc:identifier>
<dc:title>{html.escape(title)}</dc:title>
<dc:creator>Study</dc:creator>
<dc:language>en-GB</dc:language>
<dc:description>{html.escape(topic['description'])}</dc:description>
<meta property="dcterms:modified">{modified}</meta>
{'<meta name="cover" content="cover-image"/>' if has_cover else ''}
</metadata>
<manifest>
{chr(10).join(manifest)}
</manifest>
<spine toc="ncx">
{chr(10).join(spine)}
</spine>
</package>
"""

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{tid}.epub"
    with zipfile.ZipFile(out, "w") as z:
        # mimetype must be first and uncompressed.
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
""", compress_type=zipfile.ZIP_DEFLATED)
        for name, text in files.items():
            z.writestr(f"OEBPS/{name}", text, compress_type=zipfile.ZIP_DEFLATED)
        if cover_bytes:
            z.writestr("OEBPS/cover.png", cover_bytes, compress_type=zipfile.ZIP_DEFLATED)
    print(f"{out.relative_to(ROOT)}  ({len(topic['lessons'])} lessons, {out.stat().st_size // 1024} KB{', with cover' if has_cover else ''})")
    return out


def main():
    catalogue = json.loads((CONTENT / "index.json").read_text(encoding="utf-8"))
    wanted = set(sys.argv[1:])
    topics = [t for t in catalogue["topics"] if not wanted or t["id"] in wanted]
    if wanted - {t["id"] for t in topics}:
        sys.exit(f"Unknown topic(s): {', '.join(sorted(wanted - {t['id'] for t in topics}))}")
    for topic in topics:
        build(topic)


if __name__ == "__main__":
    main()
