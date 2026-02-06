# Personal Website

## Playwright checks

This repo includes a Playwright test to verify the writing page lists all articles.

### Install

```zsh
npm install
```

### Run tests

```zsh
npm test
```

To run the browser visibly:

```zsh
npm run test:headed
```

## Feeds & sitemaps

This repo generates a sitemap, image sitemap, and RSS feed from `writing.html`.

### Generate feeds

```zsh
npm run generate:feeds
```

This updates:

- `sitemap.xml`
- `image-sitemap.xml`
- `rss.xml`
