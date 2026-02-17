#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
ASSETS_DIR = ROOT / "assets" / "images" / "blog"
TEMPLATE_PATH = POSTS_DIR / "_template.html"
WRITING_INDEX = ROOT / "writing.html"
DEFAULT_IMAGE = ASSETS_DIR / "default.jpg"
FALLBACK_IMAGE = ASSETS_DIR / "publishing-without-wordpress.jpg"
MIN_IMAGE_BYTES = 80_000
DATE_INPUT_FORMATS = ("%B %d, %Y", "%Y-%m-%d", "%d %b %Y")
UNSPLASH_THEME_IDS = {
    "base": [
        "1461749280684-dccba630e2f6",
        "1472214103451-9374bd1c798e",
        "1504384308090-c894fdcc538d",
        "1522075469751-3a6694fb2f61",
        "1517248135467-4c7edcad34c4",
    ],
    "tech": [
        "1498050108023-c5249f4df085",
        "1484417894907-623942c8ee29",
        "1497366811353-6870744d04b2",
        "1518779578993-ec3579fee39f",
        "1460925895917-afdab827c52f",
    ],
    "productivity": [
        "1517248135467-4c7edcad34c4",
        "1451187580459-43490279c0fa",
        "1492724441997-5dc865305da7",
        "1497366754035-f200968a6e72",
        "1465101046530-73398c7f28ca",
    ],
    "leadership": [
        "1465101046530-73398c7f28ca",
        "1443890923422-7819ed4101c0",
        "1519389950473-47ba0277781c",
        "1501854140801-50d01698950b",
        "1469474968028-56623f02e42e",
    ],
    "learning": [
        "1494173853739-c21f58b16055",
        "1487014679447-9f8336841d58",
        "1517048676732-d65bc937f952",
        "1496307042754-b4aa456c4a2d",
        "1438761681033-6461ffad8d80",
    ],
    "business": [
        "1496307042754-b4aa456c4a2d",
        "1469474968028-56623f02e42e",
        "1438761681033-6461ffad8d80",
        "1443890923422-7819ed4101c0",
        "1501854140801-50d01698950b",
    ],
    "abstract": [
        "1460925895917-afdab827c52f",
        "1501854140801-50d01698950b",
        "1485217988980-11786ced9454",
        "1499951360447-b19be8fe80f5",
        "1517694712202-14dd9538aa97",
    ],
}
UNSPLASH_KEYWORD_THEME = {
    "ai": "tech",
    "code": "tech",
    "coding": "tech",
    "developer": "tech",
    "software": "tech",
    "automation": "tech",
    "tech": "tech",
    "technology": "tech",
    "workflow": "productivity",
    "productivity": "productivity",
    "writing": "productivity",
    "publish": "productivity",
    "wordpress": "productivity",
    "content": "productivity",
    "leadership": "leadership",
    "team": "leadership",
    "human": "leadership",
    "collaboration": "leadership",
    "learning": "learning",
    "training": "learning",
    "skills": "learning",
    "education": "learning",
    "ld": "learning",
    "strategy": "business",
    "business": "business",
    "economy": "business",
    "infrastructure": "business",
    "startup": "business",
    "future": "abstract",
    "edge": "abstract",
    "systems": "abstract",
    "concept": "abstract",
    "object": "abstract",
}
CLAIM_KEYWORDS_RE = re.compile(r"\b(study|report|survey|analysis)\b", re.IGNORECASE)
STAT_SIGNAL_RE = re.compile(r"\b(20\d{2}|[0-9]+(?:\.[0-9]+)?%|[0-9]+(?:\.[0-9]+)?x)\b")
URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug


def format_date(value: str | None) -> str:
    parsed = parse_date(value)
    if parsed:
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    if value:
        return value
    return datetime.now().strftime("%B %d, %Y").replace(" 0", " ")


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


def ordered_unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def stable_index(seed: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def extract_unsplash_photo_id(url: str) -> str:
    match = re.search(r"photo-([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else ""


def unsplash_photo_url(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1400&h=900&fm=jpg&q=78"


def infer_unsplash_themes(title: str, lead: str, tags: list[str], query_override: str | None) -> list[str]:
    values = [tag.lower() for tag in tags if tag]
    source = " ".join([query_override or "", title, lead]).lower()
    values.extend(re.findall(r"\b[a-z0-9]+\b", source))
    themes: list[str] = []
    for value in values:
        theme = UNSPLASH_KEYWORD_THEME.get(value)
        if theme:
            themes.append(theme)
    return ordered_unique(themes)


def month_year(date_str: str) -> str:
    parsed = parse_date(date_str)
    if parsed:
        return parsed.strftime("%B %Y")
    return date_str


def short_date(date_str: str) -> str:
    parsed = parse_date(date_str)
    if parsed:
        return parsed.strftime("%d %b %Y").lstrip("0")
    return date_str


def iso_date(date_str: str) -> str:
    parsed = parse_date(date_str)
    if parsed:
        return parsed.strftime("%Y-%m-%d")
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


def build_unsplash_url(title: str, lead: str, tags: list[str], query_override: str | None = None) -> str:
    themes = infer_unsplash_themes(title, lead, tags, query_override)
    candidate_ids: list[str] = []
    for theme in themes:
        candidate_ids.extend(UNSPLASH_THEME_IDS.get(theme, []))
    candidate_ids.extend(UNSPLASH_THEME_IDS["base"])
    candidate_ids = ordered_unique(candidate_ids)

    seed = "|".join([title.strip().lower(), lead.strip().lower(), ",".join(sorted([t.lower() for t in tags])), (query_override or "").strip().lower()])
    selected_id = candidate_ids[stable_index(seed, len(candidate_ids))]
    return unsplash_photo_url(selected_id)


def normalize_citations(raw_citations: object) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    if not isinstance(raw_citations, list):
        return citations

    seen_urls: set[str] = set()
    for item in raw_citations:
        if isinstance(item, str):
            url = item.strip()
            label = url
        elif isinstance(item, dict):
            url = str(item.get("url", "")).strip()
            label = (
                str(item.get("title", "")).strip()
                or str(item.get("label", "")).strip()
                or url
            )
        else:
            continue

        if not re.match(r"^https?://", url, flags=re.IGNORECASE):
            continue
        if url in seen_urls:
            continue

        seen_urls.add(url)
        citations.append({"title": label, "url": url})

    return citations


def build_article_html(
    sections: list[dict],
    bullets: list[str],
    closing: str,
    citations: list[dict[str, str]],
) -> str:
    lines = ["        <article class=\"post-content\">"]
    for section in sections:
        for paragraph in section.get("paragraphs", []):
            lines.append(f"            <p>{escape(paragraph)}</p>")
    if bullets:
        for item in bullets:
            lines.append(f"            <p>{escape(item)}</p>")
    if closing:
        lines.append(f"            <p>{escape(closing)}</p>")
    if citations:
        lines.append("            <h2>Sources</h2>")
        lines.append("            <ul>")
        for citation in citations:
            title = citation.get("title", "").strip() or citation.get("url", "").strip()
            url = citation.get("url", "").strip()
            lines.append(
                "                <li>"
                f"<a href=\"{escape(url, quote=True)}\" target=\"_blank\" rel=\"noopener\">"
                f"{escape(title)}</a>"
                "</li>"
            )
        lines.append("            </ul>")
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


def upsert_writing_entry(html: str, slug: str, entry: str) -> str:
    href = f"href=\"posts/{slug}.html\""
    idx = html.find(href)
    if idx == -1:
        return insert_writing_entry(html, entry)

    block_start = html.rfind("<a ", 0, idx)
    if block_start == -1:
        return insert_writing_entry(html, entry)

    line_start = html.rfind("\n", 0, block_start)
    if line_start != -1:
        block_start = line_start + 1

    block_end = html.find("</a>", idx)
    if block_end == -1:
        return insert_writing_entry(html, entry)
    block_end += len("</a>")
    if block_end < len(html) and html[block_end] == "\n":
        block_end += 1

    return html[:block_start] + entry + html[block_end:]


def validate_text(text: str) -> None:
    if "—" in text:
        raise ValueError("Em dash found in content")
    if "<blockquote" in text:
        raise ValueError("Blockquote tag found in content")


def validate_citation_support(text: str, citations: list[dict[str, str]]) -> None:
    has_claim_keywords = CLAIM_KEYWORDS_RE.search(text) is not None
    has_stat_signal = STAT_SIGNAL_RE.search(text) is not None
    has_url = URL_RE.search(text) is not None or any(c.get("url") for c in citations)
    if has_claim_keywords and has_stat_signal and not has_url:
        raise ValueError("Research/statistical claim detected without source URL")


def warn(message: str) -> None:
    print(f"[publish_post] warning: {message}", file=sys.stderr)


def run_git_command_result(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def run_git_command(args: list[str]) -> None:
    result = run_git_command_result(args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def current_branch() -> str:
    result = run_git_command_result(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        return "HEAD"
    return (result.stdout or "").strip() or "HEAD"


def cleanup_repo_state() -> None:
    subprocess.run(["git", "rebase", "--abort"], cwd=ROOT, capture_output=True, text=True)
    subprocess.run(["git", "merge", "--abort"], cwd=ROOT, capture_output=True, text=True)
    subprocess.run(["git", "cherry-pick", "--abort"], cwd=ROOT, capture_output=True, text=True)
    subprocess.run(["git", "am", "--abort"], cwd=ROOT, capture_output=True, text=True)


def ensure_primary_branch() -> None:
    if current_branch() != "HEAD":
        return
    checkout = run_git_command_result(["git", "checkout", "main"])
    if checkout.returncode != 0:
        checkout = run_git_command_result(["git", "checkout", "master"])
    if checkout.returncode != 0:
        raise RuntimeError("Repository is detached and could not switch to main/master")


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
    result = run_git_command_result(["git", "stash", "pop"])
    if result.returncode != 0:
        warn("Auto-stash could not be restored cleanly; resolve with `git stash list` and `git stash pop`.")


def commit_and_push(files: list[Path], message: str) -> None:
    if not (ROOT / ".git").exists():
        raise RuntimeError("Git repository not found at site root")

    cleanup_repo_state()
    ensure_primary_branch()

    run_git_command(["git", "add", *[str(f) for f in files]])

    did_stash = stash_changes_keep_index()

    try:
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if diff.returncode == 0:
            return

        run_git_command(["git", "commit", "-m", message])

        last_error = ""
        for attempt in range(1, 4):
            push = run_git_command_result(["git", "push", "origin", "HEAD:main"])
            if push.returncode == 0:
                return

            last_error = (push.stderr or push.stdout or f"push attempt {attempt} failed").strip()
            warn(f"Push attempt {attempt} failed; trying fetch/rebase retry")

            cleanup_repo_state()
            fetch = run_git_command_result(["git", "fetch", "origin", "main"])
            if fetch.returncode != 0:
                last_error = (fetch.stderr or fetch.stdout or last_error).strip()
                time.sleep(attempt * 2)
                continue

            rebase = run_git_command_result(["git", "rebase", "-X", "theirs", "origin/main"])
            if rebase.returncode != 0:
                run_git_command_result(["git", "rebase", "--abort"])
                last_error = (rebase.stderr or rebase.stdout or last_error).strip()

            time.sleep(attempt * 2)

        raise RuntimeError(f"Push failed after retries: {last_error}")
    finally:
        if did_stash:
            pop_stash()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON payload")
    parser.add_argument("--force", action="store_true", help="Overwrite existing post")
    parser.add_argument("--no-git", action="store_true", help="Skip git commit/push")
    parser.add_argument("--max-retries", type=int, default=1, help="Compatibility flag; retries are handled by wrapper scripts")
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
    citations = normalize_citations(payload.get("citations", []))

    if len(sections) < 2:
        raise ValueError("At least two sections are required")

    article_text = "\n".join(
        [lead, closing, meta_description]
        + [p for section in sections for p in section.get("paragraphs", [])]
        + bullets
    )
    validate_text(article_text)
    validate_citation_support(article_text, citations)

    core = core_keywords(lead)
    closing_tokens = core_keywords(closing)
    if core and closing_tokens.isdisjoint(core):
        warn("Closing paragraph does not echo the core concept from the lead; continuing anyway")

    count = word_count(article_text)
    if count < 150 or count > 200:
        warn(f"Word count {count} is outside 150-200 range; continuing anyway")

    read_time = payload.get("read_time")
    if not read_time:
        read_time = max(2, round(count / 200))

    image = payload.get("image", {})
    image_url = image.get("url")
    image_filename = image.get("filename")
    image_alt = image.get("alt", "")
    image_credit = image.get("credit", "")
    image_query = image.get("query", "")
    lock_image_url = bool(image.get("lock_image_url", False))

    # Default behavior favors fresh, non-repetitive Unsplash picks unless explicitly locked.
    if (not lock_image_url) or (not image_url):
        image_url = build_unsplash_url(title, lead, tags, image_query)
        image_credit = image_credit or "Photo by Unsplash."
        image_alt = image_alt or title

    if not image_filename:
        unsplash_id = extract_unsplash_photo_id(image_url or "")
        if unsplash_id:
            image_filename = f"{slug}-{unsplash_id[:10]}.jpg"
        elif image_url:
            ext = Path(urlparse(image_url).path).suffix or ".jpg"
            image_filename = f"{slug}{ext}"
        else:
            image_filename = f"{slug}.jpg"

    if image_url:
        try:
            downloaded = download_image(image_url, image_filename)
            size = downloaded.stat().st_size
            if size < MIN_IMAGE_BYTES:
                downloaded.unlink(missing_ok=True)
                warn(f"Downloaded image too small ({size} bytes); using default image")
                ensure_default_image()
                image_filename = "default.jpg"
                image_credit = image_credit or ""
        except Exception as exc:
            warn(f"Image download failed ({exc}); using default image")
            ensure_default_image()
            image_filename = "default.jpg"
            image_credit = image_credit or ""
    else:
        ensure_default_image()

    tags_text = ", ".join(tags) if tags else "Writing"
    image_cache_key = iso_date(date_str).replace("-", "") or datetime.now().strftime("%Y%m%d")
    image_src = f"{image_filename}?v={image_cache_key}"

    template = TEMPLATE_PATH.read_text()
    article_html = build_article_html(sections, bullets, closing, citations)
    html = replace_article_section(template, article_html)

    replacements = {
        "POST_TITLE": title,
        "META_DESCRIPTION": meta_description,
        "PUBLISH_DATE": date_str,
        "READ_TIME": str(read_time),
        "TAGS": tags_text,
        "INTRO_LEAD": lead,
        "IMAGE_FILE": image_src,
        "IMAGE_ALT": image_alt,
        "IMAGE_CREDIT": image_credit,
    }

    for key, value in replacements.items():
        html = html.replace(f"<!-- {key} -->", escape(value))

    post_path = POSTS_DIR / f"{slug}.html"
    if post_path.exists() and not args.force:
        warn(f"Post already exists: {post_path}; overwriting existing file")
    post_path.write_text(html)

    tag_list = ",".join([t.lower() for t in tags]) if tags else "writing"
    entry = (
        f"                <a href=\"posts/{slug}.html\" class=\"article-card\" data-tags=\"{escape(tag_list)}\" data-date=\"{iso_date(date_str)}\" data-title=\"{escape(title)}\" data-excerpt=\"{escape(excerpt)}\">\n"
        f"                    <img class=\"article-thumb\" src=\"assets/images/blog/{escape(image_src)}\" alt=\"\" loading=\"lazy\">\n"
        "                    <div class=\"article-body\">\n"
        f"                        <span class=\"article-date\">{short_date(date_str)}</span>\n"
        f"                        <h3>{escape(title)}</h3>\n"
        f"                        <p>{escape(excerpt)}</p>\n"
        f"                        <span class=\"article-read-time\">{read_time} min read</span>\n"
        "                    </div>\n"
        "                </a>\n"
    )

    writing_html = WRITING_INDEX.read_text()
    WRITING_INDEX.write_text(upsert_writing_entry(writing_html, slug, entry))

    if not args.no_git:
        image_path = ASSETS_DIR / image_filename
        files_to_commit = [post_path, WRITING_INDEX]
        if image_path.exists():
            files_to_commit.append(image_path)
        commit_and_push(files_to_commit, f"Add blog post: {title}")

    print(f"Published {post_path}")


if __name__ == "__main__":
    main()
