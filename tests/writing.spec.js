import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const writingPath = path.resolve(process.cwd(), 'writing.html');
const writingUrl = pathToFileURL(writingPath).href;

async function expectedPostCount() {
  const postsDir = path.resolve(process.cwd(), 'posts');
  const entries = await fs.readdir(postsDir);
  return entries.filter((entry) => entry.endsWith('.html') && entry !== '_template.html').length;
}

test('writing page lists all articles', async ({ page }) => {
  await page.goto(writingUrl);
  await page.waitForSelector('.article-card');

  const visibleArticles = page.locator('.article-card:not([hidden])');
  await expect(visibleArticles).toHaveCount(await expectedPostCount());
});
