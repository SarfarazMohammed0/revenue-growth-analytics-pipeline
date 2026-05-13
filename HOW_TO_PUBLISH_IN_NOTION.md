# How to Publish This in Notion

You have two clean ways to get this project into Notion as a shareable portfolio page.

## Option 1 — Paste (fastest, 30 seconds)

1. Open Notion → create a new page
2. Title it: **Executive KPI Dashboard — End-to-End Data Pipeline**
3. Open `NOTION_PAGE.md` in any text editor and copy the **entire contents**
4. Paste directly into the Notion page

Notion will auto-convert all the Markdown — headings, code blocks, tables, lists — into native Notion blocks. Tables become real Notion tables, code blocks get syntax-highlighted, headers create a sidebar table of contents.

## Option 2 — Import (preserves more structure)

1. Notion → top-left menu → **Settings & members** → **Settings** → scroll to **Import**
2. Choose **Markdown & CSV**
3. Select the `NOTION_PAGE.md` file
4. Notion creates a new page with the full structure

## After importing

A few quick polish steps that take 2 minutes and make a real difference:

- **Cover image**: hit `/cover` and pick a dark abstract one (purple/blue work well for data themes)
- **Icon**: 📊 or 📈
- **Replace placeholders**: at the bottom of the page, fill in your GitHub repo URL, live demo URL, and LinkedIn URL
- **Share**: top-right **Share** → **Publish to web** → toggle on → copy the public link

You can paste that public link directly into job applications and recruiter messages.

## Suggested cover layout

```
[Cover image]
📊 Executive KPI Dashboard — End-to-End Data Pipeline
[A one-line tagline showing as the page description]
```

## Pushing the code to GitHub

The Notion page links to your GitHub repo, so publish the code too:

```bash
cd exec-kpi-dashboard
git init
git add .
git commit -m "Initial commit: end-to-end KPI pipeline"
gh repo create exec-kpi-dashboard --public --source=. --push
```

Then update the GitHub link at the bottom of the Notion page.
