#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

ROOT = Path("/Users/shreyas-clawd/Downloads/personal-website")
POSTS_DIR = ROOT / "posts"
ASSETS_DIR = ROOT / "assets" / "images" / "blog"
TEMPLATE_PATH = POSTS_DIR / "_template.html"
WRITING_INDEX = ROOT / "writing.html"
DEFAULT_IMAGE = ASSETS_DIR / "default.jpg"
FALLBACK_IMAGE = ASSETS_DIR / "publishing-without-wordpress.jpg"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug


def format_date(value: str | None) -> str:
    if value:
        return value
    return datetime.now().strftime("%B %-d, %Y")


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def core_keywords(text: str) -> set[str]:
    tokens = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    stop = {"that", "this", "with", "from", "your", "just", "into", "when", "what", "have", "will", "about", "than", "then", "they", "their", "them", "over", "under", "back", "make", "keep", "only", "also", "more", "most", "very", "some", "same", "still", "even", "been", "were", "does", "dont", "cant", "need", "want", "like", "good", "best", "work", "time", "post", "blog"}
    return {t for t in tokens if t not in stop}


def month_year(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%B %Y")
    except ValueError:
        return date_str


def ensure_default_image() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if DEFAULT_IMAGE.exists():
        return
    if FALLBACK_IMAGE.exists():
        DEFAULT_IMAGE.write_bytes(FALLBACK_IMAGE.read_bytes())


def download_image(url: str, filename: str) -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    target = ASSETS_DIR / filename
    urlretrieve(url, target)
    return target


def build_article_html(sections: list[dict], bullets: list[str], closing: str) -> str:
    lines = ["        <article class=\"post-content\">"]
    for section in sections:
        heading = escape(section["heading"])
        lines.append(f"            <h2>{heading}</h2>")
        for paragraph in section.get("paragraphs", []):
            lines.append(f"            <p>{escape(paragraph)}</p>")
    if bullets:
        lines.append("            <ul>")
        for item in bullets:
            lines.append(f"                <li>{escape(item)}</li>")
        lines.append("            </ul>")
    if closing:
        lines.append(f"            <p>{escape(closing)}</p>")
    lines.append("        </article>")
    return "\n".join(lines)


def replace_article_section(template: str, article_html: str) -> str:
    start = template.find("<article class=\"post-content\">")
    if start == -1:
        raise ValueError("Template missing post-content section")
    end = template.find("</article>", start)
    if end == -1:
        raise ValueError("Template missing closing article tag")
    end += len("</article>")
    return template[:start] + article_html + template[end:]


def insert_writing_entry(html: str, entry: str) -> str:
    marker = "<section class=\"article-list\">"
    if marker not in html:
        raise ValueError("writing.html missing article list section")
    return html.replace(marker, marker + "\n\n" + entry, 1)


def validate_text(text: str) -> None:
    if "—" in text:
        raise ValueError("Em dash found in content")
    if "<blockquote" in text:
        raise ValueError("Blockquote tag found in content")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON payload")
    parser.add_argument("--force", action="store_true", help="Overwrite existing post")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    title = payload["title"].strip()
    slug = payload.get("slug") or slugify(title)
    date_str = format_date(payload.get("date"))
    tags = payload.get("tags", [])
    lead = payload.get("lead", "").strip()
    excerpt = payload.get("excerpt", "").strip() or lead
    meta_description = payload.get("meta_description", "").strip() or excerpt
    sections = payload.get("sections", [])
    bullets = payload.get("bullets", [])
    closing = payload.get("closing", "").strip()

    if len(sections) < 2:
        raise ValueError("At least two sections are required")

    article_text = "\n".join(
        [lead, closing, meta_description]
        + [p for section in sections for p in section.get("paragraphs", [])]
        + bullets
    )
    validate_text(article_text)

    core = core_keywords(lead)
    closing_tokens = core_keywords(closing)
    if core and closing_tokens.isdisjoint(core):
        raise ValueError("Closing paragraph must echo the core concept from the lead.")

    count = word_count(article_text)
    if count < 150 or count > 200:
        raise ValueError(f"Word count {count} is outside 150-200 range")

    read_time = payload.get("read_time")
    if not read_time:
        read_time = max(2, round(count / 200))

    image = payload.get("image", {})
    image_url = image.get("url")
    image_filename = image.get("filename")
    image_alt = image.get("alt", "")
    image_credit = image.get("credit", "")

    if not image_filename:
        if image_url:
            ext = Path(urlparse(image_url).path).suffix or ".jpg"
            image_filename = f"{slug}{ext}"
        else:
            image_filename = "default.jpg"

    if image_url:
        download_image(image_url, image_filename)
    else:
        ensure_default_image()

    tags_text = ", ".join(tags) if tags else "Writing"

    template = TEMPLATE_PATH.read_text()
    article_html = build_article_html(sections, bullets, closing)
    html = replace_article_section(template, article_html)

    replacements = {
        "POST_TITLE": title,
        "META_DESCRIPTION": meta_description,
        "PUBLISH_DATE": date_str,
        "READ_TIME": str(read_time),
        "TAGS": tags_text,
        "INTRO_LEAD": lead,
        "IMAGE_FILE": image_filename,
        "IMAGE_ALT": image_alt,
        "IMAGE_CREDIT": image_credit,
    }

    for key, value in replacements.items():
        html = html.replace(f"<!-- {key} -->", escape(value))

    post_path = POSTS_DIR / f"{slug}.html"
    if post_path.exists() and not args.force:
        raise FileExistsError(f"Post already exists: {post_path}")
    post_path.write_text(html)

    entry = (
        "            <article class=\"article-item\">\n"
        f"                <h3><a href=\"posts/{slug}.html\">{escape(title)}</a></h3>\n"
        f"                <p class=\"article-meta\">Shreyas Korad  |  {month_year(date_str)}</p>\n"
        "                <p class=\"article-excerpt\">\n"
        f"                    {escape(excerpt)}\n"
        "                </p>\n"
        "            </article>\n"
    )

    writing_html = WRITING_INDEX.read_text()
    WRITING_INDEX.write_text(insert_writing_entry(writing_html, entry))

    print(f"Published {post_path}")


if __name__ == "__main__":
    main()
