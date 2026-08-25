# Emoji Photography Journal

A bilingual photography journal and portrait portfolio, built as a lightweight static site.

## Run locally

```bash
python3 -m http.server 8888
```

Then open `http://localhost:8888`.

## Deploy

The site is ready for Netlify. Connect the repository and deploy; no build command is required.

## Add a journal article

Journal entries are plain HTML files, so no CMS or build step is needed:

1. Duplicate one of the files in `journal/`, such as `journal/the-color-of-morning.html`.
2. Rename the copy with a lowercase, hyphenated URL slug (for example, `a-day-in-osaka.html`).
3. Update the page `<title>`, metadata, heading, cover image, and both language sections:
   - `.article-body-ja` contains the Japanese article.
   - `.article-body-en` contains the English article.
4. Update the previous/next links in the new article and its neighboring articles.
5. Add a linked `.journal-row` to `journal/index.html`. Add a homepage card in `index.html` only when the article should be featured there.
6. Preview locally and confirm every article, language switch, image, and navigation link works.

Images currently use Unsplash placeholders. Replace each image URL and descriptive `alt` text when final photography is available.
