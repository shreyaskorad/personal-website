import { test, expect } from '@playwright/test';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const writingPath = path.resolve(process.cwd(), 'writing.html');
const writingUrl = pathToFileURL(writingPath).href;

test('writing page lists all articles', async ({ page }) => {
  await page.goto(writingUrl);
  await page.waitForSelector('.article-card');

  const visibleArticles = await page.locator('.article-card:not([hidden])');
  await expect(visibleArticles).toHaveCount(5);
});
