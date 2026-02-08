import fs from "fs";
import path from "path";

const rootDir = path.resolve(process.cwd());
const baseUrl = "https://shreyaskorad.in";

const xmlEscape = (value = "") => value
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/\"/g, "&quot;")
  .replace(/'/g, "&apos;");

const toDate = (dateString) => {
  if (!dateString) return null;
  const date = new Date(`${dateString}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? null : date;
};

const getLastMod = (filePath) => {
  try {
    const stat = fs.statSync(filePath);
    return stat.mtime.toISOString().split("T")[0];
  } catch {
    return new Date().toISOString().split("T")[0];
  }
};

const toAbsoluteUrl = (value = "") => {
  if (!value) return `${baseUrl}/`;

  try {
    return new URL(value).toString();
  } catch {
    return new URL(value, `${baseUrl}/`).toString();
  }
};

const extractArticles = () => {
  const writingPath = path.join(rootDir, "writing.html");
  const html = fs.readFileSync(writingPath, "utf8");
  const cardRegex = /<a[^>]*class="article-card"[^>]*>[\s\S]*?<\/a>/g;
  const cards = html.match(cardRegex) || [];

  const extractAttr = (content, name) => {
    const match = content.match(new RegExp(`${name}="([^"]+)"`));
    return match ? match[1] : "";
  };

  return cards
    .map((card) => {
      const href = extractAttr(card, "href");
      const date = extractAttr(card, "data-date");
      const title = extractAttr(card, "data-title");
      const excerpt = extractAttr(card, "data-excerpt");
      const imageMatch = card.match(/<img[^>]*class="article-thumb"[^>]*src="([^"]+)"/);
      const image = imageMatch ? imageMatch[1] : "";

      return {
        href,
        date,
        title,
        excerpt,
        image,
        filePath: href ? path.join(rootDir, href) : null
      };
    })
    .filter((article) => article.href);
};

const pages = [
  { loc: "/", file: "index.html" },
  { loc: "/index.html", file: "index.html" },
  { loc: "/about.html", file: "about.html" },
  { loc: "/work.html", file: "work.html" },
  { loc: "/writing.html", file: "writing.html" },
  { loc: "/contact.html", file: "contact.html" }
];

const articles = extractArticles();

const sitemapUrls = [
  ...pages.map((page) => ({
    loc: toAbsoluteUrl(page.loc),
    lastmod: getLastMod(path.join(rootDir, page.file))
  })),
  ...articles.map((article) => ({
    loc: toAbsoluteUrl(article.href),
    lastmod: getLastMod(article.filePath || "")
  }))
];

const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapUrls
  .map((url) => `  <url>\n    <loc>${xmlEscape(url.loc)}</loc>\n    <lastmod>${url.lastmod}</lastmod>\n  </url>`)
  .join("\n")}
</urlset>
`;

const imageEntries = articles
  .filter((article) => article.image)
  .map((article) => ({
    loc: toAbsoluteUrl(article.href),
    imageLoc: toAbsoluteUrl(article.image),
    title: article.title,
    caption: article.excerpt
  }));

const imageSitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
${imageEntries
  .map(
    (entry) =>
      `  <url>\n    <loc>${xmlEscape(entry.loc)}</loc>\n    <image:image>\n      <image:loc>${xmlEscape(entry.imageLoc)}</image:loc>\n      <image:title>${xmlEscape(entry.title)}</image:title>\n      <image:caption>${xmlEscape(entry.caption)}</image:caption>\n    </image:image>\n  </url>`
  )
  .join("\n")}
</urlset>
`;

const rssItems = articles
  .map((article) => {
    const url = toAbsoluteUrl(article.href);
    const pubDate = toDate(article.date);
    return `    <item>\n      <title>${xmlEscape(article.title)}</title>\n      <link>${xmlEscape(url)}</link>\n      <guid>${xmlEscape(url)}</guid>\n      <description>${xmlEscape(article.excerpt)}</description>\n      <pubDate>${pubDate ? pubDate.toUTCString() : ""}</pubDate>\n    </item>`;
  })
  .join("\n");

const rssXml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Shreyas Korad — Writing</title>
    <link>${baseUrl}/writing.html</link>
    <description>Articles and insights on learning design, gamification, and L&amp;D strategy.</description>
    <language>en</language>
${rssItems}
  </channel>
</rss>
`;

fs.writeFileSync(path.join(rootDir, "sitemap.xml"), sitemapXml);
fs.writeFileSync(path.join(rootDir, "image-sitemap.xml"), imageSitemapXml);
fs.writeFileSync(path.join(rootDir, "rss.xml"), rssXml);

console.log("Generated sitemap.xml, image-sitemap.xml, and rss.xml");
