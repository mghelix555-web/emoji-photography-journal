#!/usr/bin/env python3
"""Publish due JSON entries from content/queue into the static journal."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "content" / "queue"
JOURNAL = ROOT / "journal"
INDEX = JOURNAL / "index.html"
REQUIRED_TEXT = (
    "slug", "titleEn", "titleJa", "category", "readTime", "image",
    "summaryEn", "summaryJa",
)


def atomic_write(path: Path, contents: str) -> None:
    """Replace a text file without exposing a partially written file."""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(contents)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def load_post(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        post = json.load(handle)
    missing = [key for key in REQUIRED_TEXT if not isinstance(post.get(key), str) or not post[key].strip()]
    if missing:
        raise ValueError(f"missing or invalid fields: {', '.join(missing)}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", post["slug"]):
        raise ValueError("slug must contain only lowercase letters, numbers, and hyphens")
    for key in ("bodyEn", "bodyJa"):
        if not isinstance(post.get(key), list) or not post[key] or not all(isinstance(value, str) and value.strip() for value in post[key]):
            raise ValueError(f"{key} must be a non-empty list of paragraphs")
    try:
        post["_date"] = date.fromisoformat(post.get("publishDate", ""))
    except (TypeError, ValueError) as error:
        raise ValueError("publishDate must use YYYY-MM-DD") from error
    image_path = (ROOT / post["image"]).resolve()
    if ROOT.resolve() not in image_path.parents or not image_path.is_file():
        raise ValueError(f"image does not exist inside the repository: {post['image']}")
    return post


def paragraphs(values: list[str]) -> str:
    return "".join(f"<p>{html.escape(value)}</p>" for value in values)


def article_html(post: dict) -> str:
    escaped = {key: html.escape(str(value), quote=True) for key, value in post.items() if not key.startswith("_")}
    iso_date = post["_date"].isoformat()
    display_date = post["_date"].strftime("%B %d, %Y").replace(" 0", " ")
    image = html.escape("../" + post["image"].lstrip("/"), quote=True)
    return f'''<!doctype html>
<!-- Scheduled post: {escaped['slug']} -->
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="{escaped['summaryJa']}"><title>{escaped['titleEn']} — Emoji Photography</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=Noto+Sans+JP:wght@300;400;500&family=Newsreader:ital,opsz,wght@0,6..72,300;1,6..72,300&display=swap" rel="stylesheet"><link rel="stylesheet" href="../styles.css"><script src="../script.js" defer></script></head>
<body class="interior-page"><header class="site-header"><a class="brand" href="../index.html"><span class="brand-mark" aria-hidden="true">◉</span><span>Emoji<br>Photography</span></a><button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav"><span>Menu</span><i></i><i></i></button><nav id="site-nav" class="site-nav" aria-label="Main navigation"><a href="index.html">Journal</a><a href="../index.html#gallery">Photography</a><a href="../index.html#about">About</a><a href="mailto:hello@emojiphotography.jp">Contact</a></nav><p class="issue">Tokyo · Japan<br>Photography Journal</p></header>
<main class="article-page" data-language="ja"><header class="article-masthead"><div class="story-meta"><span>{escaped['category']}</span><time datetime="{iso_date}">{display_date}</time><span>{escaped['readTime']}</span></div><h1>{escaped['titleEn']}<span lang="ja">{escaped['titleJa']}</span></h1></header><figure class="article-cover image-wrap"><img src="{image}" alt="{escaped['titleEn']}"></figure>
<div class="article-layout"><aside class="article-aside"><p>{escaped['category']}<br>{post['_date'].year}</p></aside><article class="article-body"><div class="article-body-ja" lang="ja">{paragraphs(post['bodyJa'])}</div><div class="article-body-en" lang="en">{paragraphs(post['bodyEn'])}</div></article><div class="language-switcher" data-language-switcher aria-label="Article language"><button type="button" data-language="ja" aria-pressed="true">JP</button><button type="button" data-language="en" aria-pressed="false">EN</button></div></div>
<nav class="article-nav" aria-label="Article navigation"><a class="back" href="index.html">← Back to journal</a></nav></main></body></html>
'''


def index_row(post: dict) -> str:
    e = {key: html.escape(str(value), quote=True) for key, value in post.items() if not key.startswith("_")}
    image = html.escape("../" + post["image"].lstrip("/"), quote=True)
    display_date = post["_date"].strftime("%m.%d.%Y")
    return f'''      <article class="journal-row reveal" data-post-slug="{e['slug']}"><a class="image-wrap" href="{e['slug']}.html"><img src="{image}" alt="{e['titleEn']}"></a><div><div class="story-meta"><span>{e['category']} · {display_date}</span><span>{e['readTime']}</span></div><a href="{e['slug']}.html"><h2>{e['titleEn']}<span lang="ja">{e['titleJa']}</span></h2><p>{e['summaryEn']}</p></a></div></article>
'''


def publish(path: Path, post: dict) -> None:
    article = JOURNAL / f"{post['slug']}.html"
    if not article.exists():
        atomic_write(article, article_html(post))
    elif f"<!-- Scheduled post: {post['slug']} -->" not in article.read_text(encoding="utf-8"):
        raise RuntimeError(f"refusing to overwrite existing article: journal/{article.name}")

    index = INDEX.read_text(encoding="utf-8")
    marker = '<section class="journal-list" aria-label="Journal articles">\n'
    slug_marker = f'data-post-slug="{html.escape(post["slug"], quote=True)}"'
    if slug_marker not in index:
        if marker not in index:
            raise RuntimeError("could not find journal list in journal/index.html")
        atomic_write(INDEX, index.replace(marker, marker + index_row(post), 1))

    stored = {key: value for key, value in post.items() if not key.startswith("_")}
    stored["published"] = True
    atomic_write(path, json.dumps(stored, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(timezone.utc).date(), help="date to publish through (YYYY-MM-DD; defaults to today in UTC)")
    args = parser.parse_args()
    published = 0
    for path in sorted(QUEUE.glob("*.json")):
        try:
            post = load_post(path)
            if post.get("published") is False and post["_date"] <= args.date:
                publish(path, post)
                published += 1
                print(f"Published {post['slug']}")
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
            raise SystemExit(f"Error in {path.relative_to(ROOT)}: {error}") from error
    print(f"Publishing complete: {published} post(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
