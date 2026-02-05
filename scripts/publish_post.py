#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
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
MIN_IMAGE_BYTES = 10_000


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
    stop = {
        "that",
        "this",
        "with",
        "from",
        "your",
        "just",
        "into",
        "when",
        "what",
        "have",
        "will",
        "about",
        "than",
        "then",
        "they",
        "their",
        "them",
        "over",
        "under",
        "back",
        "make",
        "keep",
        "only",
        "also",
        "more",
        "most",
        "very",
        "some",
        "same",
        "still",
        "even",
        "been",
        "were",
        "does",
        "dont",
        "cant",
        "need",
        "want",
        "like",
        "good",
        "best",
        "work",
        "time",
        "post",
        "blog",
    }
    return {t for t in tokens if t not in stop}


def month_year(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%B %Y")
    except ValueError:
        return date_str


def iso_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


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


def build_unsplash_url(title: str, lead: str, tags: list[str]) -> str:
    keywords = list(core_keywords(lead or title))
    if tags:
        keywords.extend([t.lower() for t in tags])
    cleaned = []
    for word in keywords:
        if word not in cleaned:
            cleaned.append(word)
    query = ",".join(cleaned[:4]) or "learning,work"
    return f"https://images.unsplash.com/featured/?{query}"


def build_article_html(sections: list[dict], bullets: list[str], closing: str) -> str:
    lines = ["        <article class=\"post-content\">"]
    for section in sections:
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
    marker = "<div class=\"article-list\" id=\"article-list\">"
    if marker not in html:
        raise ValueError("writing.html missing article list section")
    return html.replace(marker, marker + "\n" + entry, 1)


def validate_text(text: str) -> None:
    if "—" in text:
        raise ValueError("Em dash found in content")
    if "<blockquote" in text:
        raise ValueError("Blockquote tag found in content")


def run_git_command(args: list[str]) -> None:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def has_unstaged_changes() -> bool:
    result = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT)
    if result.returncode != 0:
        return True
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(untracked.stdout.strip())


def stash_changes_keep_index() -> bool:
    if not has_unstaged_changes():
        return False
    result = subprocess.run(
        ["git", "stash", "push", "-u", "-k", "-m", "openclaw-auto-stash"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def pop_stash() -> None:
    subprocess.run(["git", "stash", "pop"], cwd=ROOT, capture_output=True, text=True)


def commit_and_push(files: list[Path], message: str) -> None:
    if not (ROOT / ".git").exists():
        raise RuntimeError("Git repository not found at site root")

    run_git_command(["git", "add", *[str(f) for f in files]])

    did_stash = stash_changes_keep_index()

    try:
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if diff.returncode == 0:
            return

        run_git_command(["git", "commit", "-m", message])

        dry_run = subprocess.run(["git", "push", "--dry-run"], cwd=ROOT, capture_output=True, text=True)
        if dry_run.returncode != 0:
            raise RuntimeError(dry_run.stderr.strip() or dry_run.stdout.strip())

        run_git_command(["git", "push"])
    finally:
        if did_stash:
            pop_stash()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON payload")
    parser.add_argument("--force", action="store_true", help="Overwrite existing post")
    parser.add_argument("--no-git", action="store_true", help="Skip git commit/push")
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
            image_filename = f"{slug}.jpg"

    if not image_url:
        image_url = build_unsplash_url(title, lead, tags)
        image_credit = image_credit or "Photo by Unsplash."
        image_alt = image_alt or title

    if image_url:
        downloaded = download_image(image_url, image_filename)
        if downloaded.stat().st_size < MIN_IMAGE_BYTES:
            downloaded.unlink(missing_ok=True)
            ensure_default_image()
            image_filename = "default.jpg"
            image_credit = image_credit or ""
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

    tag_list = ",".join([t.lower() for t in tags]) if tags else "writing"
    entry = (
        f"                <article class=\"article-card\" data-tags=\"{escape(tag_list)}\" data-date=\"{iso_date(date_str)}\" data-title=\"{escape(title)}\" data-excerpt=\"{escape(excerpt)}\">\n"
        f"                    <span class=\"article-date\">{month_year(date_str)}</span>\n"
        f"                    <h3><a href=\"posts/{slug}.html\">{escape(title)}</a></h3>\n"
        f"                    <p>{escape(excerpt)}</p>\n"
        f"                    <span class=\"article-read-time\">{read_time} min read</span>\n"
        "                </article>\n"
    )

    writing_html = WRITING_INDEX.read_text()
    WRITING_INDEX.write_text(insert_writing_entry(writing_html, entry))

    if not args.no_git:
        image_path = ASSETS_DIR / image_filename
        files_to_commit = [post_path, WRITING_INDEX]
        if image_path.exists():
            files_to_commit.append(image_path)
        commit_and_push(files_to_commit, f"Add blog post: {title}")

    print(f"Published {post_path}")


if __name__ == "__main__":
    main()
