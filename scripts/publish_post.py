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
QUALITY_MIN_WORDS = 170
QUALITY_MAX_WORDS = 300
QUALITY_MIN_HEADINGS = 0
QUALITY_MIN_PARAGRAPHS = 5
QUALITY_MAX_DUP_SENTENCES = 1
QUALITY_MAX_DUP_PARAGRAPHS = 1
CITATION_MAX_COUNT = 4
DISABLE_BODY_H2 = True

STUDY_SOURCE_POOL = [
    {
        "title": "Generative AI at Work (NBER Working Paper 31161)",
        "url": "https://www.nber.org/papers/w31161",
        "topics": ["ai", "productivity", "workforce", "learning"],
    },
    {
        "title": "OECD Skills Outlook 2023",
        "url": "https://www.oecd.org/skills/oecd-skills-outlook-e11c1c2d-en.htm",
        "topics": ["learning", "skills", "workforce", "policy"],
    },
    {
        "title": "The Future of Jobs Report 2025 (World Economic Forum)",
        "url": "https://www.weforum.org/reports/the-future-of-jobs-report-2025",
        "topics": ["skills", "workforce", "business", "leadership"],
    },
    {
        "title": "2024 Workplace Learning Report (LinkedIn Learning)",
        "url": "https://learning.linkedin.com/resources/workplace-learning-report-2024",
        "topics": ["learning", "ld", "skills", "management"],
    },
    {
        "title": "Gallup: State of the Global Workplace",
        "url": "https://www.gallup.com/workplace/349484/state-of-the-global-workplace.aspx",
        "topics": ["workforce", "engagement", "management", "leadership"],
    },
    {
        "title": "Our World in Data: Artificial Intelligence",
        "url": "https://ourworldindata.org/artificial-intelligence",
        "topics": ["ai", "workforce", "trends"],
    },
    {
        "title": "Training language models to follow instructions with human feedback (arXiv:2203.02155)",
        "url": "https://arxiv.org/abs/2203.02155",
        "topics": ["ai", "technical", "alignment"],
    },
    {
        "title": "On the Opportunities and Risks of Foundation Models (arXiv:2108.07258)",
        "url": "https://arxiv.org/abs/2108.07258",
        "topics": ["ai", "technical", "governance", "risk"],
    },
    {
        "title": "GPTs are GPTs: An Early Look at the Labor Market Impact Potential of Large Language Models (arXiv:2303.10130)",
        "url": "https://arxiv.org/abs/2303.10130",
        "topics": ["ai", "workforce", "economics"],
    },
    {
        "title": "A Survey of Large Language Models (arXiv:2303.18223)",
        "url": "https://arxiv.org/abs/2303.18223",
        "topics": ["ai", "technical"],
    },
]

STUDY_URL_PATTERNS = [
    r"nber\.org/papers/",
    r"arxiv\.org/abs/",
    r"doi\.org/",
    r"ourworldindata\.org/",
    r"gallup\.com/workplace/",
    r"weforum\.org/reports/",
    r"oecd\.org/(en/)?skills/",
    r"learning\.linkedin\.com/resources/workplace-learning-report",
    r"nature\.com/articles/",
    r"science\.org/doi/",
    r"cell\.com/",
    r"jamanetwork\.com/",
]

TOPIC_KEYWORDS = {
    "learning": ("learning", "l&d", "ld", "training", "upskill", "reskill", "instruction"),
    "skills": ("skill", "skills", "capability", "competency"),
    "workforce": ("workforce", "jobs", "talent", "employee", "team", "manager"),
    "productivity": ("productivity", "efficiency", "cycle", "roi", "kpi", "metric"),
    "leadership": ("leader", "leadership", "executive", "stakeholder", "decision"),
    "ai": ("ai", "artificial intelligence", "llm", "model", "automation", "genai", "copilot"),
    "technical": ("prompt", "token", "transformer", "inference", "fine-tune", "embedding"),
    "governance": ("risk", "governance", "policy", "regulation", "compliance"),
}
TITLE_TRAILING_STOPWORDS = {"and", "with", "for", "to", "about", "on", "of"}
STYLE_DRIFT_PATTERNS = [
    re.compile(r"\bbuild on this core idea\b", flags=re.IGNORECASE),
    re.compile(r"\bclarify one constraint\b", flags=re.IGNORECASE),
    re.compile(r"\bkeep one claim and one proof point\b", flags=re.IGNORECASE),
    re.compile(r"\bproduced visible improvement\b", flags=re.IGNORECASE),
    re.compile(r"\bwhen i work on\b", flags=re.IGNORECASE),
    re.compile(r"\bpractical guidance for teams\b", flags=re.IGNORECASE),
    re.compile(r"\buse one baseline metric,\s*one weekly experiment\b", flags=re.IGNORECASE),
    re.compile(r"\bkeep .{0,90} practical by pairing one study link\b", flags=re.IGNORECASE),
]
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
INSTRUCTION_LINE_PATTERNS = [
    re.compile(r"\bcite at least\b.*\bstudy link", flags=re.IGNORECASE),
    re.compile(r"\bremove unsupported (?:statistical )?claims?\b", flags=re.IGNORECASE),
    re.compile(r"\bsource link rule\b", flags=re.IGNORECASE),
    re.compile(r"\bevery external claim must include\b", flags=re.IGNORECASE),
    re.compile(r"\bif a source cannot be verified\b", flags=re.IGNORECASE),
    re.compile(r"\breturn only markdown\b", flags=re.IGNORECASE),
    re.compile(r"\bno json\b", flags=re.IGNORECASE),
    re.compile(r"\bno process commentary\b", flags=re.IGNORECASE),
    re.compile(r"^\s*task:\s*", flags=re.IGNORECASE),
    re.compile(r"^\s*generated:\s*", flags=re.IGNORECASE),
    re.compile(r"^\s*rewrite priorities\b", flags=re.IGNORECASE),
    re.compile(r"^\s*publish flow\b", flags=re.IGNORECASE),
    re.compile(r"\bquality score\b", flags=re.IGNORECASE),
    re.compile(r"\bmatched post:\b", flags=re.IGNORECASE),
]
FRAGMENT_ENDING_RE = re.compile(
    r"\b(?:by|for|with|to|from|of|in|on|at|as|and|or|but|so|than|then|if|when|while|because|that|which)\.?\s*$",
    flags=re.IGNORECASE,
)


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


def normalize_spaces(text: str) -> str:
    return " ".join(str(text or "").split())


def normalize_display_title(raw: str, max_words: int = 14, max_chars: int = 96) -> str:
    title = normalize_spaces(raw)
    if not title:
        return ""
    title = re.sub(
        r"\b(with\s+\d+\s*(?:source links?|citations?|references?)|for this task|right now|return only markdown|no json|no process commentary)\b[\s\S]*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = title.strip(" -:;,.")
    words = [w for w in title.split() if w]
    while words and words[-1].lower() in TITLE_TRAILING_STOPWORDS:
        words.pop()
    if len(words) > max_words:
        words = words[:max_words]
    title = " ".join(words).strip()
    if len(title) > max_chars:
        title = title[:max_chars].rsplit(" ", 1)[0].strip()
    if title:
        title = title[0].upper() + title[1:]
    title = re.sub(r"\bAi\b", "AI", title)
    title = re.sub(r"\bL&d\b", "L&D", title)
    title = re.sub(r"\bLd\b", "L&D", title)
    title = re.sub(r"\bLxd\b", "LxD", title)
    return title.strip(" -:;,.")


def is_instructional_line(text: str) -> bool:
    value = normalize_spaces(text)
    if not value:
        return False
    return any(pattern.search(value) for pattern in INSTRUCTION_LINE_PATTERNS)


def is_likely_sentence_fragment(text: str) -> bool:
    value = normalize_spaces(text)
    if not value:
        return False
    words = value.split()
    if len(words) < 4 and value[-1] not in ".!?":
        return True
    if len(words) >= 5 and FRAGMENT_ENDING_RE.search(value):
        return True
    return False


def sanitize_content_line(text: str) -> str:
    value = normalize_spaces(text)
    if not value:
        return ""
    if is_instructional_line(value):
        return ""
    if is_likely_sentence_fragment(value):
        return ""
    if any(pattern.search(value) for pattern in STYLE_DRIFT_PATTERNS):
        return ""
    if value[-1] not in ".!?":
        value += "."
    return value


def split_sentences(text: str) -> list[str]:
    value = normalize_spaces(text)
    if not value:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", value) if part.strip()]


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

        if is_generic_citation_title(label):
            label = citation_title_from_url(url)
        seen_urls.add(url)
        citations.append({"title": label, "url": url})

    return citations


def parse_citation_policy(payload: dict[str, object]) -> dict[str, object]:
    raw = payload.get("_citation_policy", {})
    if not isinstance(raw, dict):
        raw = {}
    try:
        target_count = int(raw.get("target_count", 0))
    except Exception:
        target_count = 0
    try:
        required_new_domains = int(raw.get("required_new_domains", 0))
    except Exception:
        required_new_domains = 0
    recent_raw = raw.get("recent_domains", [])
    recent_domains: set[str] = set()
    if isinstance(recent_raw, list):
        for value in recent_raw:
            domain = normalize_spaces(str(value or "")).lower().strip()
            if domain:
                recent_domains.add(domain)
    return {
        "target_count": max(0, min(CITATION_MAX_COUNT, target_count)),
        "required_new_domains": max(0, required_new_domains),
        "recent_domains": recent_domains,
    }


def is_study_url(url: str) -> bool:
    value = normalize_spaces(url).lower()
    if not value.startswith("http"):
        return False
    for pattern in STUDY_URL_PATTERNS:
        if re.search(pattern, value):
            return True
    return False


def citation_domain(url: str) -> str:
    try:
        host = urlparse(normalize_spaces(url)).netloc.lower()
    except Exception:
        host = ""
    if host.startswith("www."):
        host = host[4:]
    return host


def infer_topics(text: str) -> set[str]:
    value = normalize_spaces(text).lower()
    topics: set[str] = set()
    if not value:
        return {"workforce"}
    for topic, words in TOPIC_KEYWORDS.items():
        for word in words:
            if word in value:
                topics.add(topic)
                break
    if not topics:
        topics.add("workforce")
    return topics


def is_technical_topic(topics: set[str]) -> bool:
    if not topics:
        return False
    business_topics = {"learning", "skills", "workforce", "productivity", "leadership"}
    if topics & business_topics:
        return False
    return "technical" in topics or ("ai" in topics and "governance" not in topics)


def recent_study_usage(max_posts: int = 60) -> dict[str, int]:
    usage: dict[str, int] = {}
    posts = sorted(
        [p for p in POSTS_DIR.glob("*.html") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:max_posts]
    for post in posts:
        try:
            text = post.read_text()
        except Exception:
            continue
        urls = {u.rstrip(".,;:!?") for u in re.findall(r"https?://[^\s\"'<)]+", text, flags=re.IGNORECASE)}
        for url in urls:
            if not is_study_url(url):
                continue
            key = normalize_spaces(url).lower()
            usage[key] = usage.get(key, 0) + 1
    return usage


def default_study_citations(seed: str, count: int = 3) -> list[dict[str, str]]:
    if not STUDY_SOURCE_POOL:
        return []
    target = max(2, min(8, count))
    usage = recent_study_usage()
    topics = infer_topics(seed)
    technical = is_technical_topic(topics)

    def rank_key(item: dict[str, object]) -> tuple[object, ...]:
        item_topics = set(item.get("topics", []) if isinstance(item.get("topics", []), list) else [])
        topical_miss = 0 if (item_topics & topics) else 1
        technical_penalty = 0
        if not technical and "technical" in item_topics and not (item_topics & {"workforce", "learning", "skills"}):
            technical_penalty = 1
        return (
            topical_miss,
            technical_penalty,
            usage.get(str(item["url"]).lower(), 0),
            hashlib.sha256(f"{seed}|{item['url']}".encode("utf-8")).hexdigest(),
        )

    ranked = sorted(
        STUDY_SOURCE_POOL,
        key=rank_key,
    )
    return [{"title": str(item["title"]), "url": str(item["url"])} for item in ranked[:target]]


def is_generic_citation_title(title: str) -> bool:
    value = normalize_spaces(title).lower()
    if not value:
        return True
    if value in {"source", "study", "reference", "link"}:
        return True
    if re.match(r"^source\s*\d*$", value):
        return True
    if re.match(r"^reference\s*\d*$", value):
        return True
    return False


def citation_title_from_url(url: str) -> str:
    value = normalize_spaces(url)
    lower = value.lower()
    for item in STUDY_SOURCE_POOL:
        if item["url"].lower() == lower:
            return item["title"]
    if "nber.org/papers/" in lower:
        return "NBER Working Paper"
    if "arxiv.org/abs/" in lower:
        return "arXiv preprint"
    if "doi.org/" in lower:
        return "DOI-linked study"
    if "ourworldindata.org/" in lower:
        return "Our World in Data"
    if "gallup.com/workplace/" in lower:
        return "Gallup workplace research"
    if "weforum.org/reports/" in lower:
        return "World Economic Forum report"
    if "oecd.org/" in lower:
        return "OECD report"
    if "learning.linkedin.com/" in lower:
        return "LinkedIn Learning report"
    return value


def ensure_study_citations(
    citations: list[dict[str, str]],
    seed: str,
    min_count: int = 0,
    required_new_domains: int = 0,
    recent_domains: set[str] | None = None,
    max_count: int = CITATION_MAX_COUNT,
) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in citations:
        url = normalize_spaces(item.get("url", ""))
        title = normalize_spaces(item.get("title", "") or url)
        if not url or url in seen:
            continue
        if is_generic_citation_title(title):
            title = citation_title_from_url(url)
        seen.add(url)
        cleaned.append({"title": title, "url": url})

    target = max(0, min(int(min_count), max_count))
    required_new_domains = max(0, int(required_new_domains))
    prior_domains = {normalize_spaces(d).lower().strip() for d in (recent_domains or set()) if normalize_spaces(d)}
    if target <= 0:
        return []

    topics = infer_topics(seed)
    technical = is_technical_topic(topics)
    max_arxiv = target if technical else max(1, target // 2)
    arxiv_count = sum(1 for item in cleaned if citation_domain(item.get("url", "")) == "arxiv.org")
    domains = {citation_domain(item.get("url", "")) for item in cleaned if citation_domain(item.get("url", ""))}
    new_domain_count = len({d for d in domains if d and d not in prior_domains})

    for item in default_study_citations(seed, count=max(8, target + 3)):
        url = item["url"]
        if url in seen:
            continue
        domain = citation_domain(url)
        if not technical and domain == "arxiv.org" and arxiv_count >= max_arxiv:
            continue
        seen.add(url)
        cleaned.append({"title": item["title"], "url": url})
        if domain == "arxiv.org":
            arxiv_count += 1
        if domain:
            domains.add(domain)
            if domain not in prior_domains:
                new_domain_count += 1
        if len(cleaned) >= target and new_domain_count >= required_new_domains:
            break

    usage = recent_study_usage()
    ranked = sorted(
        cleaned,
        key=lambda item: (
            1 if (not technical and citation_domain(item["url"]) == "arxiv.org") else 0,
            usage.get(item["url"].lower(), 0),
            hashlib.sha256(f"{seed}|{item['url']}".encode("utf-8")).hexdigest(),
        ),
    )
    selected: list[dict[str, str]] = []
    selected_domains: set[str] = set()
    selected_arxiv = 0
    desired = target
    for item in ranked:
        domain = citation_domain(item["url"])
        if not technical and domain == "arxiv.org" and selected_arxiv >= max_arxiv:
            continue
        selected.append(item)
        if domain:
            selected_domains.add(domain)
        if domain == "arxiv.org":
            selected_arxiv += 1
        selected_new_domains = {d for d in selected_domains if d and d not in prior_domains}
        if len(selected) >= desired and len(selected_new_domains) >= required_new_domains:
            break

    if len({d for d in selected_domains if d and d not in prior_domains}) < required_new_domains:
        for item in ranked:
            if item in selected:
                continue
            domain = citation_domain(item["url"])
            if domain and domain not in selected_domains and domain not in prior_domains:
                selected.append(item)
                selected_domains.add(domain)
                if len({d for d in selected_domains if d and d not in prior_domains}) >= required_new_domains:
                    break

    if required_new_domains > 0 and selected:
        chosen: list[dict[str, str]] = []
        chosen_domains: set[str] = set()
        for item in selected:
            domain = citation_domain(item.get("url", ""))
            if not domain or domain in prior_domains:
                continue
            if item in chosen:
                continue
            chosen.append(item)
            chosen_domains.add(domain)
            if len(chosen_domains) >= required_new_domains:
                break
        for item in selected:
            if item in chosen:
                continue
            chosen.append(item)
            if len(chosen) >= target:
                break
        selected = chosen

    return selected[:target]


def inline_citation_anchor(citations: list[dict[str, str]], paragraph_index: int) -> str:
    if not citations:
        return ""
    idx = paragraph_index % len(citations)
    citation = citations[idx]
    url = citation.get("url", "").strip()
    title = citation.get("title", "").strip() or f"Source {idx + 1}"
    if not url:
        return ""
    return (
        f' <sup><a href="{escape(url, quote=True)}" target="_blank" rel="noopener" '
        f'title="{escape(title, quote=True)}">[{idx + 1}]</a></sup>'
    )


def build_article_html(
    sections: list[dict],
    bullets: list[str],
    closing: str,
    citations: list[dict[str, str]],
) -> str:
    lines = ["        <article class=\"post-content\">"]
    paragraph_index = 0
    for section in sections:
        heading = str(section.get("heading", "")).strip()
        if heading and not DISABLE_BODY_H2:
            lines.append(f"            <h2>{escape(heading)}</h2>")
        for paragraph in section.get("paragraphs", []):
            anchor = inline_citation_anchor(citations, paragraph_index)
            lines.append(f"            <p>{escape(paragraph)}{anchor}</p>")
            paragraph_index += 1
    # Body bullets are intentionally not rendered in public posts to keep
    # narrative flow and avoid repetitive template-like sections.
    if closing:
        anchor = inline_citation_anchor(citations, paragraph_index)
        lines.append(f"            <p>{escape(closing)}{anchor}</p>")
    if citations:
        lines.append("            <p><strong>References</strong></p>")
        lines.append("            <ol>")
        for idx, citation in enumerate(citations, start=1):
            title = citation.get("title", "").strip() or citation.get("url", "").strip()
            url = citation.get("url", "").strip()
            lines.append(
                "                <li>"
                f"{escape(title)}. "
                f"<a href=\"{escape(url, quote=True)}\" target=\"_blank\" rel=\"noopener\">"
                f"{escape(url)}</a>"
                "</li>"
            )
        lines.append("            </ol>")
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


def _find_writing_entry_bounds(html: str, marker: str) -> tuple[int, int] | None:
    idx = html.find(marker)
    if idx == -1:
        return None

    block_start = html.rfind("<a ", 0, idx)
    if block_start == -1:
        return None

    line_start = html.rfind("\n", 0, block_start)
    if line_start != -1:
        block_start = line_start + 1

    block_end = html.find("</a>", idx)
    if block_end == -1:
        return None
    block_end += len("</a>")
    if block_end < len(html) and html[block_end] == "\n":
        block_end += 1
    return (block_start, block_end)


def _normalize_title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def dedupe_writing_entries(html: str) -> str:
    marker = "<div class=\"article-list\" id=\"article-list\">"
    start = html.find(marker)
    if start == -1:
        return html
    list_start = start + len(marker)
    end_marker = "id=\"no-results\""
    list_end = html.find(end_marker, list_start)
    if list_end == -1:
        list_end = html.find("</div>", list_start)
    if list_end == -1:
        return html

    body = html[list_start:list_end]
    blocks = re.findall(r"\s*<a [\s\S]*?</a>\s*", body, flags=re.IGNORECASE)
    if not blocks:
        return html

    seen: set[str] = set()
    kept: list[str] = []
    for block in blocks:
        href_match = re.search(r'href="([^"]+)"', block, flags=re.IGNORECASE)
        title_match = re.search(r'data-title="([^"]+)"', block, flags=re.IGNORECASE)
        href = str(href_match.group(1) if href_match else "").strip().lower()
        title_key = _normalize_title_key(title_match.group(1) if title_match else "")
        dedupe_key = f"title:{title_key}" if title_key else f"href:{href}"
        if dedupe_key and dedupe_key in seen:
            continue
        if dedupe_key:
            seen.add(dedupe_key)
        if href:
            seen.add(f"href:{href}")
        if title_key:
            seen.add(f"title:{title_key}")
        kept.append(block.strip())

    rebuilt = "\n" + "\n".join(kept) + "\n" if kept else "\n"
    return html[:list_start] + rebuilt + html[list_end:]


def upsert_writing_entry(html: str, slug: str, entry: str) -> str:
    href = f"href=\"posts/{slug}.html\""
    markers = [href]
    title_match = re.search(r'data-title="([^"]+)"', entry, flags=re.IGNORECASE)
    if title_match:
        title_marker = f'data-title="{title_match.group(1)}"'
        markers.append(title_marker)
        title_key = _normalize_title_key(title_match.group(1))
        if title_key:
            key_pattern = re.compile(r'data-title="([^"]+)"', flags=re.IGNORECASE)
            for match in key_pattern.finditer(html):
                if _normalize_title_key(match.group(1)) == title_key:
                    markers.append(match.group(0))
                    break

    updated = html
    replaced = False
    for marker in markers:
        bounds = _find_writing_entry_bounds(updated, marker)
        if bounds is None:
            continue
        block_start, block_end = bounds
        updated = updated[:block_start] + entry + updated[block_end:]
        replaced = True
        break

    if not replaced:
        updated = insert_writing_entry(updated, entry)
    return dedupe_writing_entries(updated)


def validate_text(text: str) -> None:
    if "—" in text:
        raise ValueError("Em dash found in content")
    if "<blockquote" in text:
        raise ValueError("Blockquote tag found in content")


def validate_citation_support(
    text: str,
    citations: list[dict[str, str]],
    *,
    required_count: int = 0,
    required_new_domains: int = 0,
    recent_domains: set[str] | None = None,
    max_count: int = CITATION_MAX_COUNT,
) -> None:
    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]
    for line in lines:
        if is_instructional_line(line):
            raise ValueError(f"Instruction text leaked into body content: {line[:120]}")
        if is_likely_sentence_fragment(line):
            raise ValueError(f"Sentence fragment detected in body content: {line[:120]}")

    has_claim_keywords = CLAIM_KEYWORDS_RE.search(text) is not None
    has_stat_signal = STAT_SIGNAL_RE.search(text) is not None
    has_url = URL_RE.search(text) is not None or any(c.get("url") for c in citations)
    if has_claim_keywords and has_stat_signal and not has_url:
        raise ValueError("Research/statistical claim detected without source URL")
    min_required = max(0, int(required_count))
    if min_required > 0 and len(citations) < min_required:
        raise ValueError(f"At least {min_required} citations are required for this post")
    if len(citations) > max_count:
        raise ValueError(f"Citation count {len(citations)} exceeds maximum {max_count}")
    for citation in citations:
        url = normalize_spaces(citation.get("url", ""))
        title = normalize_spaces(citation.get("title", ""))
        if not re.match(r"^https?://", url, flags=re.IGNORECASE):
            raise ValueError(f"Citation URL must be absolute http(s): {url}")
        if is_generic_citation_title(title):
            raise ValueError(f"Citation title must be specific, not generic: {title or 'empty'}")
    required_new = max(0, int(required_new_domains))
    if required_new > 0 and citations:
        prior = {normalize_spaces(value).lower().strip() for value in (recent_domains or set()) if normalize_spaces(value)}
        domains = {citation_domain(item.get("url", "")) for item in citations if citation_domain(item.get("url", ""))}
        new_domains = {domain for domain in domains if domain not in prior}
        if len(new_domains) < required_new:
            raise ValueError("Citations must include at least one domain not used in recent posts")


def validate_quality_structure(
    lead: str,
    sections: list[dict],
    bullets: list[str],
    closing: str,
    meta_description: str,
) -> None:
    heading_count = 0
    paragraphs: list[str] = []
    for section in sections:
        heading = normalize_spaces(section.get("heading", ""))
        if heading:
            heading_count += 1
        raw_paragraphs = section.get("paragraphs", [])
        if isinstance(raw_paragraphs, list):
            paragraphs.extend([normalize_spaces(p) for p in raw_paragraphs if normalize_spaces(p)])

    if normalize_spaces(closing):
        paragraphs.append(normalize_spaces(closing))

    quality_text = "\n".join([lead, *paragraphs, *bullets, meta_description])
    total_words = word_count(quality_text)
    if total_words < QUALITY_MIN_WORDS:
        raise ValueError(f"Word count {total_words} is below minimum {QUALITY_MIN_WORDS}")
    if total_words > QUALITY_MAX_WORDS:
        raise ValueError(f"Word count {total_words} exceeds maximum {QUALITY_MAX_WORDS}")

    paragraph_count = len(paragraphs)
    if paragraph_count < QUALITY_MIN_PARAGRAPHS:
        raise ValueError(f"Paragraph count {paragraph_count} is below minimum {QUALITY_MIN_PARAGRAPHS}")

    if heading_count < QUALITY_MIN_HEADINGS:
        raise ValueError(f"Heading count {heading_count} is below minimum {QUALITY_MIN_HEADINGS}")

    duplicate_paragraphs = max(0, len(paragraphs) - len({p.lower() for p in paragraphs}))
    if duplicate_paragraphs > QUALITY_MAX_DUP_PARAGRAPHS:
        raise ValueError(
            f"Duplicate paragraph count {duplicate_paragraphs} exceeds maximum {QUALITY_MAX_DUP_PARAGRAPHS}"
        )

    sentences = split_sentences(quality_text)
    duplicate_sentences = max(0, len(sentences) - len({s.lower() for s in sentences}))
    if duplicate_sentences > QUALITY_MAX_DUP_SENTENCES:
        raise ValueError(
            f"Duplicate sentence count {duplicate_sentences} exceeds maximum {QUALITY_MAX_DUP_SENTENCES}"
        )

    style_drift = sum(1 for line in paragraphs if any(pattern.search(line) for pattern in STYLE_DRIFT_PATTERNS))
    if style_drift > 0:
        raise ValueError("Style drift detected from boilerplate/meta writing patterns")


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
    title = normalize_display_title(payload["title"].strip()) or payload["title"].strip()
    slug = payload.get("slug") or slugify(title)
    date_str = format_date(payload.get("date"))
    tags = [normalize_spaces(t).lower() for t in payload.get("tags", []) if normalize_spaces(t)] if isinstance(payload.get("tags", []), list) else []
    lead = sanitize_content_line(payload.get("lead", "") or payload.get("excerpt", "") or title)
    excerpt = sanitize_content_line(payload.get("excerpt", "") or lead) or lead
    meta_description = sanitize_content_line(payload.get("meta_description", "") or excerpt) or excerpt

    sections: list[dict[str, object]] = []
    raw_sections = payload.get("sections", [])
    if isinstance(raw_sections, list):
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            heading = normalize_spaces(item.get("heading", ""))
            paragraphs_raw = item.get("paragraphs", [])
            if isinstance(paragraphs_raw, str):
                paragraphs_raw = [paragraphs_raw]
            if not isinstance(paragraphs_raw, list):
                paragraphs_raw = []
            paragraphs = [sanitize_content_line(p) for p in paragraphs_raw if sanitize_content_line(p)]
            if paragraphs:
                sections.append({"heading": heading, "paragraphs": paragraphs[:6]})

    bullets: list[str] = []
    raw_bullets = payload.get("bullets", [])
    if isinstance(raw_bullets, list):
        bullets = [sanitize_content_line(b) for b in raw_bullets if sanitize_content_line(b)]

    closing = sanitize_content_line(payload.get("closing", "") or lead) or lead
    citation_policy = parse_citation_policy(payload)
    citations = normalize_citations(payload.get("citations", []))
    citations = ensure_study_citations(
        citations,
        seed=f"{slug}|{title}|{','.join(tags)}",
        min_count=int(citation_policy["target_count"]),
        required_new_domains=int(citation_policy["required_new_domains"]),
        recent_domains=set(citation_policy["recent_domains"]),
        max_count=CITATION_MAX_COUNT,
    )

    if len(sections) < 2:
        raise ValueError("At least two sections are required")

    article_text = "\n".join(
        [lead, closing, meta_description]
        + [p for section in sections for p in section.get("paragraphs", [])]
        + bullets
    )
    validate_text(article_text)
    validate_citation_support(
        article_text,
        citations,
        required_count=int(citation_policy["target_count"]),
        required_new_domains=int(citation_policy["required_new_domains"]),
        recent_domains=set(citation_policy["recent_domains"]),
        max_count=CITATION_MAX_COUNT,
    )
    validate_quality_structure(lead, sections, bullets, closing, meta_description)

    core = core_keywords(lead)
    closing_tokens = core_keywords(closing)
    if core and closing_tokens.isdisjoint(core):
        warn("Closing paragraph does not echo the core concept from the lead; continuing anyway")

    count = word_count(article_text)

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
