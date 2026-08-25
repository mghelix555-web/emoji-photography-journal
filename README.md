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

## Schedule a journal article

Posts prepared in `content/queue/` are published automatically without changing the
existing Netlify configuration.

1. Upload the post's image to the repository (the repository root is fine, or use an
   image subfolder). Commit the image, and put its repository-relative path in the
   JSON `image` field, for example `_DSC0498.JPG`. The publisher references that file
   directly and does not copy or modify it.
2. Duplicate `content/queue/example-post.json` and rename the copy for your post.
   Give it a unique, lowercase, hyphenated `slug`, and fill in both the English and
   Japanese titles, summaries, and paragraph arrays. Leave `published` set to
   `false`.
3. Set `publishDate` in `YYYY-MM-DD` format. Dates are evaluated as UTC; a post is
   eligible on that date and remains eligible afterward if a run was missed.
4. Commit and push the JSON and image. Every day at 00:15 UTC, the **Publish scheduled
   posts** GitHub Actions workflow runs the Python publisher. It creates the bilingual
   article in `journal/`, adds it to the top of the journal archive, changes
   `published` to `true`, and commits the result directly to `main`. Netlify then sees
   the main-branch commit and deploys it as usual. Repeated runs do not duplicate a
   post.

To publish eligible posts manually, open the repository on GitHub, choose **Actions**,
select **Publish scheduled posts**, click **Run workflow**, select the `main` branch,
and click **Run workflow** again.

For a local preview, run `python3 scripts/publish_scheduled_posts.py`. This publishes
all entries due as of the current UTC date into your working tree, so review the diff
before committing (or restore it if the run was only a test).
