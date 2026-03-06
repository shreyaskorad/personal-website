#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLISH_SCRIPT = ROOT / 'scripts' / 'publish_post.py'
FEED_SCRIPT = ROOT / 'scripts' / 'generate-feeds.js'
STATE_DIR = Path('/Users/shreyas-clawd/.openclaw/state')
LOCK_FILE = STATE_DIR / 'publish.lock'
HISTORY_FILE = Path('/Users/shreyas-clawd/.openclaw/state/publish-image-history.json')
SANITIZED_PAYLOAD = STATE_DIR / 'publish-payload.sanitized.json'
QUALITY_HISTORY_FILE = STATE_DIR / 'publish-quality-history.json'
QUALITY_REPORT_FILE = STATE_DIR / 'publish-quality-report.json'
RESEARCH_REPORT_FILE = STATE_DIR / 'publish-research-report.json'

RESEARCH_TIMEOUT_SECONDS = 8
RESEARCH_MAX_QUERIES = 3
RESEARCH_MAX_ITEMS = 10
RESEARCH_IDEA_LIMIT = 3
FOCUS_AREA_QUERY_HINTS = {
    'gamification': 'gamification workplace learning behavior change',
    'learning-design': 'learning and development workflow manager coaching capability',
    'data-analytics': 'learning analytics performance measurement workplace teams',
    'behavior-science': 'behavior science habit formation decision quality teams',
    'ai-learning': 'generative ai learning design workplace capability building',
}
RESEARCH_TOKEN_STOPWORDS = {
    'with', 'from', 'that', 'this', 'their', 'there', 'where', 'when', 'what', 'which',
    'about', 'into', 'through', 'between', 'around', 'using', 'used', 'use', 'based',
    'study', 'paper', 'result', 'results', 'approach', 'method', 'methods', 'analysis',
    'system', 'models', 'model', 'learning', 'development', 'teams', 'workplace',
}
FOCUS_AREA_FILTER_TERMS = {
    'gamification': {'gamification', 'game', 'motivation', 'engagement'},
    'learning-design': {'learning', 'training', 'coaching', 'enablement', 'instruction', 'capability'},
    'data-analytics': {'data', 'analytics', 'metric', 'measurement', 'performance', 'dashboard'},
    'behavior-science': {'behavior', 'behaviour', 'habit', 'nudge', 'decision', 'bias'},
    'ai-learning': {'ai', 'automation', 'model', 'llm', 'copilot'},
}
BUSINESS_CONTEXT_TERMS = {
    'learning', 'training', 'workplace', 'workforce', 'manager', 'team', 'organization',
    'employee', 'capability', 'coaching', 'enablement', 'leadership', 'performance',
    'analytics', 'gamification', 'behavior', 'behaviour', 'habit', 'decision',
}

IMPROVEMENT_ENGINE_FILE = STATE_DIR / 'publish-improvement-engine.json'
OPTIONAL_CITATION_MAX = 2
OPTIONAL_CITATION_MIN_CONFIDENCE = 0.78

VOICE_BANNED_PATTERNS = [
    re.compile(r'\bin today\'s fast-paced world\b', flags=re.IGNORECASE),
    re.compile(r'\bgame changer\b', flags=re.IGNORECASE),
    re.compile(r'\bleverage ai\b', flags=re.IGNORECASE),
    re.compile(r'\bnext level\b', flags=re.IGNORECASE),
    re.compile(r'\bunlock potential\b', flags=re.IGNORECASE),
    re.compile(r'\bmove the needle\b', flags=re.IGNORECASE),
]
VOICE_FILLER_PREFIX_RE = re.compile(r'^(this (?:article|post|piece)|in summary|to conclude)[:,\-]\s*', flags=re.IGNORECASE)
TRUSTED_CITATION_DOMAINS = {
    'nber.org', 'oecd.org', 'weforum.org', 'gallup.com', 'ourworldindata.org',
    'arxiv.org', 'doi.org', 'nature.com', 'science.org', 'cell.com', 'jamanetwork.com',
    'learning.linkedin.com',
}
RECENT_IMAGE_WINDOW = 12
QUALITY_MIN_TOTAL = 22
QUALITY_MAX_PASSES = 4
QUALITY_DELTA_PER_ITERATION = 0
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
        'title': 'Generative AI at Work (NBER Working Paper 31161)',
        'url': 'https://www.nber.org/papers/w31161',
        'topics': ['ai', 'productivity', 'workforce', 'learning'],
    },
    {
        'title': 'OECD Skills Outlook 2023',
        'url': 'https://www.oecd.org/skills/oecd-skills-outlook-e11c1c2d-en.htm',
        'topics': ['learning', 'skills', 'workforce', 'policy'],
    },
    {
        'title': 'The Future of Jobs Report 2025 (World Economic Forum)',
        'url': 'https://www.weforum.org/reports/the-future-of-jobs-report-2025',
        'topics': ['skills', 'workforce', 'business', 'leadership'],
    },
    {
        'title': '2024 Workplace Learning Report (LinkedIn Learning)',
        'url': 'https://learning.linkedin.com/resources/workplace-learning-report-2024',
        'topics': ['learning', 'ld', 'skills', 'management'],
    },
    {
        'title': 'Gallup: State of the Global Workplace',
        'url': 'https://www.gallup.com/workplace/349484/state-of-the-global-workplace.aspx',
        'topics': ['workforce', 'engagement', 'management', 'leadership'],
    },
    {
        'title': 'Our World in Data: Artificial Intelligence',
        'url': 'https://ourworldindata.org/artificial-intelligence',
        'topics': ['ai', 'workforce', 'trends'],
    },
    {
        'title': 'Training language models to follow instructions with human feedback (arXiv:2203.02155)',
        'url': 'https://arxiv.org/abs/2203.02155',
        'topics': ['ai', 'technical', 'alignment'],
    },
    {
        'title': 'On the Opportunities and Risks of Foundation Models (arXiv:2108.07258)',
        'url': 'https://arxiv.org/abs/2108.07258',
        'topics': ['ai', 'governance', 'risk', 'technical'],
    },
    {
        'title': 'GPTs are GPTs: An Early Look at the Labor Market Impact Potential of Large Language Models (arXiv:2303.10130)',
        'url': 'https://arxiv.org/abs/2303.10130',
        'topics': ['ai', 'workforce', 'economics'],
    },
    {
        'title': 'A Survey of Large Language Models (arXiv:2303.18223)',
        'url': 'https://arxiv.org/abs/2303.18223',
        'topics': ['ai', 'technical'],
    },
]

STUDY_URL_PATTERNS = [
    r'nber\.org/papers/',
    r'arxiv\.org/abs/',
    r'doi\.org/',
    r'ourworldindata\.org/',
    r'gallup\.com/workplace/',
    r'weforum\.org/reports/',
    r'oecd\.org/(en/)?skills/',
    r'learning\.linkedin\.com/resources/workplace-learning-report',
    r'nature\.com/articles/',
    r'science\.org/doi/',
    r'cell\.com/',
    r'jamanetwork\.com/',
]

TOPIC_KEYWORDS = {
    'learning': ('learning', 'l&d', 'ld', 'training', 'upskill', 'reskill', 'curriculum', 'instruction'),
    'skills': ('skill', 'skills', 'capability', 'capabilities', 'competency'),
    'workforce': ('workforce', 'jobs', 'hiring', 'talent', 'employee', 'team', 'manager'),
    'productivity': ('productivity', 'efficiency', 'throughput', 'cycle-time', 'roi', 'kpi', 'metric'),
    'leadership': ('leadership', 'leader', 'executive', 'decision', 'stakeholder'),
    'ai': ('ai', 'artificial intelligence', 'llm', 'model', 'automation', 'genai', 'copilot'),
    'technical': ('prompt', 'token', 'transformer', 'fine-tune', 'inference', 'embedding'),
    'governance': ('risk', 'governance', 'policy', 'regulation', 'compliance'),
}

TITLE_TRAILING_STOPWORDS = {'and', 'with', 'for', 'to', 'about', 'on', 'of'}
CATEGORY_PREFIX_PATTERNS = (
    r'gamified\s+learning',
    r'gamification',
    r'l\s*&\s*d',
    r'learning\s+and\s+development',
    r'learning\s+design',
    r'lxd',
    r'ai',
    r'modern\s+l\s*&\s*d',
    r'modern\s+ld',
    r'data\s+and\s+analytics',
    r'behaviou?r\s+science',
)
LEADING_CATEGORY_LABEL_RE = re.compile(
    r'^\s*(?:' + '|'.join(CATEGORY_PREFIX_PATTERNS) + r')\b(?:\s*[:\-|]\s*|\s+)+',
    flags=re.IGNORECASE,
)
STYLE_DRIFT_PATTERNS = [
    re.compile(r'\bbuild on this core idea\b', flags=re.IGNORECASE),
    re.compile(r'\bclarify one constraint\b', flags=re.IGNORECASE),
    re.compile(r'\bkeep one claim and one proof point\b', flags=re.IGNORECASE),
    re.compile(r'\bproduced visible improvement\b', flags=re.IGNORECASE),
    re.compile(r'\bwhen i work on\b', flags=re.IGNORECASE),
    re.compile(r'\bpractical guidance for teams\b', flags=re.IGNORECASE),
    re.compile(r'\buse one baseline metric,\s*one weekly experiment\b', flags=re.IGNORECASE),
    re.compile(r'\bkeep .{0,90} practical by pairing one study link\b', flags=re.IGNORECASE),
]

UNSPLASH_THEME_IDS = {
    'base': [
        '1461749280684-dccba630e2f6',
        '1472214103451-9374bd1c798e',
        '1504384308090-c894fdcc538d',
        '1522075469751-3a6694fb2f61',
        '1517248135467-4c7edcad34c4',
    ],
    'tech': [
        '1498050108023-c5249f4df085',
        '1484417894907-623942c8ee29',
        '1497366811353-6870744d04b2',
        '1518779578993-ec3579fee39f',
        '1460925895917-afdab827c52f',
    ],
    'productivity': [
        '1517248135467-4c7edcad34c4',
        '1451187580459-43490279c0fa',
        '1492724441997-5dc865305da7',
        '1497366754035-f200968a6e72',
        '1465101046530-73398c7f28ca',
    ],
    'leadership': [
        '1465101046530-73398c7f28ca',
        '1443890923422-7819ed4101c0',
        '1519389950473-47ba0277781c',
        '1501854140801-50d01698950b',
        '1469474968028-56623f02e42e',
    ],
    'learning': [
        '1494173853739-c21f58b16055',
        '1487014679447-9f8336841d58',
        '1517048676732-d65bc937f952',
        '1496307042754-b4aa456c4a2d',
        '1438761681033-6461ffad8d80',
    ],
    'business': [
        '1496307042754-b4aa456c4a2d',
        '1469474968028-56623f02e42e',
        '1438761681033-6461ffad8d80',
        '1443890923422-7819ed4101c0',
        '1501854140801-50d01698950b',
    ],
    'abstract': [
        '1460925895917-afdab827c52f',
        '1501854140801-50d01698950b',
        '1485217988980-11786ced9454',
        '1499951360447-b19be8fe80f5',
        '1517694712202-14dd9538aa97',
    ],
}

UNSPLASH_KEYWORD_THEME = {
    'ai': 'tech',
    'code': 'tech',
    'coding': 'tech',
    'developer': 'tech',
    'software': 'tech',
    'automation': 'tech',
    'tech': 'tech',
    'technology': 'tech',
    'workflow': 'productivity',
    'productivity': 'productivity',
    'writing': 'productivity',
    'publish': 'productivity',
    'wordpress': 'productivity',
    'content': 'productivity',
    'leadership': 'leadership',
    'team': 'leadership',
    'human': 'leadership',
    'collaboration': 'leadership',
    'learning': 'learning',
    'training': 'learning',
    'skills': 'learning',
    'education': 'learning',
    'ld': 'learning',
    'strategy': 'business',
    'business': 'business',
    'economy': 'business',
    'infrastructure': 'business',
    'startup': 'business',
    'future': 'abstract',
    'edge': 'abstract',
    'systems': 'abstract',
    'concept': 'abstract',
    'object': 'abstract',
}

QUALITY_DIMENSIONS = ('clarity', 'specificity', 'evidence', 'originality', 'actionability')
QUALITY_ACTION_TERMS = {
    'define', 'measure', 'track', 'review', 'ship', 'test', 'improve', 'set', 'map', 'audit',
    'reduce', 'increase', 'prioritize', 'publish', 'validate', 'align'
}
QUALITY_METRIC_TERMS = {
    'kpi', 'metric', 'metrics', 'conversion', 'retention', 'throughput', 'cycle', 'cycle-time',
    'activation', 'adoption', 'latency', 'revenue', 'cost', 'efficiency', 'baseline', 'lift'
}
QUALITY_CLICHE_PATTERNS = [
    r'\bgame changer\b',
    r'\bleverage ai\b',
    r'\bin today\'s fast-paced world\b',
    r'\bnext level\b',
    r'\bmove the needle\b',
    r'\bunlock potential\b',
]
SECTION_HEADING_DEFAULTS = [
    'Key context',
    'Execution move',
    'Review checkpoint',
    'Next iteration',
]
INSTRUCTION_LINE_PATTERNS = [
    re.compile(r'\bcite at least\b.*\bstudy link', flags=re.IGNORECASE),
    re.compile(r'\bremove unsupported (?:statistical )?claims?\b', flags=re.IGNORECASE),
    re.compile(r'\bsource link rule\b', flags=re.IGNORECASE),
    re.compile(r'\bevery external claim must include\b', flags=re.IGNORECASE),
    re.compile(r'\bif a source cannot be verified\b', flags=re.IGNORECASE),
    re.compile(r'\breturn only markdown\b', flags=re.IGNORECASE),
    re.compile(r'\bno json\b', flags=re.IGNORECASE),
    re.compile(r'\bno process commentary\b', flags=re.IGNORECASE),
    re.compile(r'^\s*task:\s*', flags=re.IGNORECASE),
    re.compile(r'^\s*generated:\s*', flags=re.IGNORECASE),
    re.compile(r'^\s*rewrite priorities\b', flags=re.IGNORECASE),
    re.compile(r'^\s*publish flow\b', flags=re.IGNORECASE),
    re.compile(r'\bquality score\b', flags=re.IGNORECASE),
    re.compile(r'\bmatched post:\b', flags=re.IGNORECASE),
]
FRAGMENT_ENDING_RE = re.compile(
    r'\b(?:by|for|with|to|from|of|in|on|at|as|and|or|but|so|than|then|if|when|while|because|that|which)\.?\s*$',
    flags=re.IGNORECASE,
)


def warn(message: str) -> None:
    print(f'[publish_pipeline] warning: {message}', file=sys.stderr)


def die(message: str, code: int = 1) -> None:
    print(f'[publish_pipeline] error: {message}', file=sys.stderr)
    raise SystemExit(code)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or '').strip()
        raise RuntimeError(f"Command failed ({' '.join(cmd)}): {detail}")
    return proc


def cleanup_repo_state() -> None:
    subprocess.run(['git', 'rebase', '--abort'], cwd=ROOT, text=True, capture_output=True)
    subprocess.run(['git', 'merge', '--abort'], cwd=ROOT, text=True, capture_output=True)


def has_worktree_changes() -> bool:
    proc = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, text=True, capture_output=True)
    return bool((proc.stdout or '').strip())


def stash_local_changes() -> str | None:
    stamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    note = f'openclaw-publish-autostash-{stamp}'
    proc = subprocess.run(
        ['git', 'stash', 'push', '-u', '-m', note],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    output = f"{proc.stdout or ''}\n{proc.stderr or ''}".strip()
    if 'No local changes to save' in output:
        return None
    if proc.returncode != 0:
        raise RuntimeError(f'Failed to stash local changes: {output}')

    ref_proc = subprocess.run(
        ['git', 'stash', 'list', '--format=%gd', '-n', '1'],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    stash_ref = (ref_proc.stdout or '').strip().splitlines()[0] if (ref_proc.stdout or '').strip() else ''
    if not stash_ref:
        raise RuntimeError('Stash succeeded but no stash reference was found')
    return stash_ref


def restore_stash(stash_ref: str | None) -> None:
    if not stash_ref:
        return
    pop = subprocess.run(['git', 'stash', 'pop', stash_ref], cwd=ROOT, text=True, capture_output=True)
    if pop.returncode != 0:
        detail = (pop.stderr or pop.stdout or '').strip()
        warn(f'Failed to auto-restore stashed changes ({stash_ref}): {detail}')


def slugify(text: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug or 'untitled-post'


def sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = text.replace('—', '-')
    text = re.sub(r'<\s*blockquote[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*/\s*blockquote\s*>', '', text, flags=re.IGNORECASE)
    return ' '.join(text.strip().split())


def strip_category_prefix(text: str) -> str:
    value = sanitize_text(text)
    if not value:
        return value
    stripped = LEADING_CATEGORY_LABEL_RE.sub('', value).strip()
    return stripped or value


def normalize_display_title(raw: str, *, max_words: int = 14, max_chars: int = 96) -> str:
    title = sanitize_text(raw)
    if not title:
        return ''

    title = re.sub(
        r'\b(with\s+\d+\s*(?:source links?|citations?|references?)|for this task|right now|return only markdown|no json|no process commentary)\b[\s\S]*$',
        '',
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r'\s*[|:]\s*(draft|rewrite|publish|task).*$','', title, flags=re.IGNORECASE)
    title = strip_category_prefix(title)
    title = title.strip(' -:;,.')

    words = [w for w in title.split() if w]
    while words and words[-1].lower() in TITLE_TRAILING_STOPWORDS:
        words.pop()
    if len(words) > max_words:
        words = words[:max_words]
    title = ' '.join(words).strip()
    if len(title) > max_chars:
        title = title[:max_chars].rsplit(' ', 1)[0].strip()

    if title:
        title = title[0].upper() + title[1:]
    title = re.sub(r'\bAi\b', 'AI', title)
    title = re.sub(r'\bL&d\b', 'L&D', title)
    title = re.sub(r'\bLd\b', 'L&D', title)
    title = re.sub(r'\bLxd\b', 'LxD', title)
    return title.strip(' -:;,.')


def is_instructional_line(text: str) -> bool:
    value = sanitize_text(text)
    if not value:
        return False
    return any(pattern.search(value) for pattern in INSTRUCTION_LINE_PATTERNS)


def is_likely_sentence_fragment(text: str) -> bool:
    value = sanitize_text(text)
    if not value:
        return False
    words = value.split()
    if len(words) < 4 and value[-1] not in '.!?':
        return True
    if len(words) >= 5 and FRAGMENT_ENDING_RE.search(value):
        return True
    return False


def sanitize_content_line(text: str) -> str:
    value = sanitize_text(text)
    if not value:
        return ''
    if is_instructional_line(value):
        return ''
    if is_likely_sentence_fragment(value):
        return ''
    if any(pattern.search(value) for pattern in STYLE_DRIFT_PATTERNS):
        return ''
    if value[-1] not in '.!?':
        value += '.'
    return value


def word_count(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text))


def core_keywords(text: str) -> set[str]:
    stop = {
        'that', 'this', 'with', 'from', 'your', 'just', 'into', 'when', 'what', 'have',
        'will', 'about', 'than', 'then', 'they', 'their', 'them', 'over', 'under', 'back',
        'make', 'keep', 'only', 'also', 'more', 'most', 'very', 'some', 'same', 'still',
        'even', 'been', 'were', 'does', 'dont', 'cant', 'need', 'want', 'like', 'good',
        'best', 'work', 'time', 'post', 'blog'
    }
    tokens = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    return {t for t in tokens if t not in stop}


def ensure_sections(raw_sections: Any, lead: str, excerpt: str, closing: str, title: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    if isinstance(raw_sections, list):
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            heading = sanitize_text(item.get('heading', ''))
            raw_paragraphs = item.get('paragraphs', [])
            if isinstance(raw_paragraphs, str):
                raw_paragraphs = [raw_paragraphs]
            if not isinstance(raw_paragraphs, list):
                raw_paragraphs = []
            paragraphs = [sanitize_content_line(p) for p in raw_paragraphs if sanitize_content_line(p)]
            if paragraphs:
                sections.append({'heading': heading, 'paragraphs': paragraphs[:6]})

    if len(sections) >= 2:
        return ensure_section_headings(sections, title)

    body_a = sanitize_content_line(excerpt) or sanitize_content_line(lead) or sanitize_content_line(
        f'{title} is useful only when it improves a recurring decision in real work.'
    )
    body_b = sanitize_content_line(closing) or sanitize_content_line(
        'The practical move is to test one small change, review outcomes weekly, and keep only what improves execution.'
    )
    warn('Payload sections were incomplete; generated fallback sections')
    fallback = [
        {
            'heading': '' if DISABLE_BODY_H2 else 'Key context',
            'paragraphs': [
                body_a,
                sanitize_content_line(
                    'Teams get better outcomes when they connect learning moments to actual handoffs, reviews, and coaching conversations.'
                ),
            ],
        },
        {
            'heading': '' if DISABLE_BODY_H2 else 'Execution move',
            'paragraphs': [
                body_b,
                sanitize_content_line(
                    'Choose one decision checkpoint this week, assign ownership, and compare behavior before and after the change.'
                ),
            ],
        },
    ]
    return ensure_section_headings(fallback, title)


def ensure_section_headings(sections: list[dict[str, Any]], title: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    title_topic = sanitize_text(title) or 'this topic'
    for idx, section in enumerate(sections):
        heading = sanitize_text(section.get('heading', ''))
        if DISABLE_BODY_H2:
            heading = ''
        elif not heading:
            if idx < len(SECTION_HEADING_DEFAULTS):
                heading = SECTION_HEADING_DEFAULTS[idx]
            else:
                heading = f'{title_topic}: section {idx + 1}'
        paragraphs = [sanitize_content_line(p) for p in section.get('paragraphs', []) if sanitize_content_line(p)]
        if not paragraphs:
            continue
        normalized.append({'heading': heading, 'paragraphs': paragraphs[:6]})
    return normalized


def normalize_tags(raw_tags: Any, title: str, lead: str) -> list[str]:
    tags: list[str] = []
    if isinstance(raw_tags, list):
        tags = [sanitize_text(t).lower().replace(' ', '-') for t in raw_tags if sanitize_text(t)]
    if not tags:
        tags = [t for t in list(core_keywords(f'{title} {lead}'))[:3]]
    if not tags:
        tags = ['writing', 'insights']
    return tags[:3]


def normalize_citations(raw_citations: Any) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    if not isinstance(raw_citations, list):
        return citations

    seen_urls: set[str] = set()
    for item in raw_citations:
        if isinstance(item, str):
            url = sanitize_text(item)
            label = url
        elif isinstance(item, dict):
            url = sanitize_text(item.get('url', ''))
            label = sanitize_text(item.get('title', '') or item.get('label', '') or url)
        else:
            continue

        if not re.match(r'^https?://', url, flags=re.IGNORECASE):
            continue
        if url in seen_urls:
            continue

        seen_urls.add(url)
        if is_generic_citation_title(label):
            label = citation_title_from_url(url)
        citations.append({'title': label, 'url': url})

    return citations[:CITATION_MAX_COUNT]


def parse_citation_policy(payload: dict[str, Any]) -> dict[str, Any]:
    # Citations are disabled by product choice.
    return {
        'target_count': 0,
        'required_new_domains': 0,
        'recent_domains': set(),
    }


def is_study_url(url: str) -> bool:
    value = sanitize_text(url).lower()
    if not value.startswith('http'):
        return False
    for pattern in STUDY_URL_PATTERNS:
        if re.search(pattern, value):
            return True
    return False


def citation_domain(url: str) -> str:
    try:
        host = urlparse(sanitize_text(url)).netloc.lower()
    except Exception:
        host = ''
    if host.startswith('www.'):
        host = host[4:]
    return host


def infer_topics(text: str) -> set[str]:
    value = sanitize_text(text).lower()
    topics: set[str] = set()
    if not value:
        return {'workforce'}
    for topic, words in TOPIC_KEYWORDS.items():
        for word in words:
            if word in value:
                topics.add(topic)
                break
    if not topics:
        topics.add('workforce')
    return topics


def is_technical_topic(topics: set[str]) -> bool:
    if not topics:
        return False
    business_topics = {'learning', 'skills', 'workforce', 'productivity', 'leadership'}
    if topics & business_topics:
        return False
    return 'technical' in topics or ('ai' in topics and 'governance' not in topics)



def detect_focus_areas(title: str, lead: str, tags: list[str]) -> list[str]:
    text = sanitize_text(f"{title} {lead} {' '.join(tags)}").lower()
    focus: list[str] = []
    rules = [
        ('gamification', r'\b(gamif|game|playful|serious game)'),
        ('learning-design', r'\b(l&d|\bld\b|lxd|learning|instruction|enablement|coaching)'),
        ('data-analytics', r'\b(data|analytics|metric|kpi|measurement|dashboard)'),
        ('behavior-science', r'\b(behavio(?:u)?r|habit|nudge|decision quality|bias)'),
        ('ai-learning', r'\b(ai|genai|llm|model|automation|copilot)'),
    ]
    for key, pattern in rules:
        if re.search(pattern, text):
            focus.append(key)
    if not focus:
        focus = ['learning-design', 'data-analytics']
    return ordered_unique(focus)


def build_research_queries(title: str, lead: str, tags: list[str]) -> list[str]:
    focus = detect_focus_areas(title, lead, tags)
    queries: list[str] = []
    for key in focus:
        hint = FOCUS_AREA_QUERY_HINTS.get(key, '').strip()
        if hint:
            queries.append(hint)
    token_seed = sanitize_text(f"{title} {' '.join(tags)}")
    tokens = re.findall(r'\b[a-zA-Z]{4,}\b', token_seed)
    if tokens:
        queries.append(' '.join(tokens[:8]))
    if sanitize_text(lead):
        lead_tokens = re.findall(r'\b[a-zA-Z]{4,}\b', sanitize_text(lead))
        if lead_tokens:
            queries.append(' '.join(lead_tokens[:8]))
    return ordered_unique([q for q in queries if sanitize_text(q)])[:RESEARCH_MAX_QUERIES]


def fetch_json(url: str, timeout: int = RESEARCH_TIMEOUT_SECONDS) -> dict[str, Any]:
    req = Request(url, headers={'User-Agent': 'openclaw-publish-pipeline/1.0'})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode('utf-8', errors='ignore')
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def fetch_text(url: str, timeout: int = RESEARCH_TIMEOUT_SECONDS) -> str:
    req = Request(url, headers={'User-Agent': 'openclaw-publish-pipeline/1.0'})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def rebuild_openalex_abstract(inverted: Any) -> str:
    if not isinstance(inverted, dict):
        return ''
    max_pos = -1
    for positions in inverted.values():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int) and pos > max_pos:
                    max_pos = pos
    if max_pos < 0:
        return ''
    words = [''] * (max_pos + 1)
    for token, positions in inverted.items():
        if not isinstance(token, str) or not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int) and 0 <= pos < len(words) and not words[pos]:
                words[pos] = token
    return sanitize_text(' '.join([w for w in words if w]))


def first_sentence(text: str, max_words: int = 22) -> str:
    value = sanitize_text(text)
    if not value:
        return ''
    sentence = re.split(r'(?<=[.!?])\s+', value)[0].strip()
    sentence = re.sub(r'^(introduction|abstract|background)\s*[:\-]\s*', '', sentence, flags=re.IGNORECASE)
    sentence = re.sub(r'^[A-Z]{3,}\s+', '', sentence)
    words = sentence.split()
    if len(words) > max_words:
        words = words[:max_words]
    while words and words[-1].lower() in {'of', 'and', 'to', 'for', 'with', 'in', 'on', 'at', 'by'}:
        words.pop()
    sentence = ' '.join(words).rstrip(',;:')
    if sentence and sentence[-1] not in '.!?':
        sentence += '.'
    return sentence


def lower_first(text: str) -> str:
    value = sanitize_text(text)
    if not value:
        return ''
    if len(value) == 1:
        return value.lower()
    return value[0].lower() + value[1:]


def fetch_openalex_items(query: str, per_page: int = 6) -> list[dict[str, Any]]:
    page_size = max(1, min(25, per_page))
    urls = [
        'https://api.openalex.org/works?filter=title.search:'
        + quote_plus(query)
        + f'&sort=publication_date:desc&per-page={page_size}',
        'https://api.openalex.org/works?search='
        + quote_plus(query)
        + f'&sort=publication_date:desc&per-page={page_size}',
    ]

    items: list[dict[str, Any]] = []
    for url in urls:
        payload = fetch_json(url)
        for entry in payload.get('results', []) if isinstance(payload.get('results', []), list) else []:
            if not isinstance(entry, dict):
                continue
            title = sanitize_text(entry.get('display_name', ''))
            if not title:
                continue
            summary = rebuild_openalex_abstract(entry.get('abstract_inverted_index', {}))
            if not summary:
                summary = sanitize_text(entry.get('primary_location', {}).get('source', {}).get('display_name', ''))
            year = entry.get('publication_year') if isinstance(entry.get('publication_year'), int) else 0
            cited = entry.get('cited_by_count') if isinstance(entry.get('cited_by_count'), int) else 0
            url_value = sanitize_text(entry.get('id', '')) or sanitize_text(entry.get('doi', ''))
            if url_value and url_value.startswith('https://openalex.org/'):
                doi_value = sanitize_text(entry.get('doi', ''))
                if doi_value:
                    url_value = doi_value
            items.append(
                {
                    'title': title,
                    'summary': summary,
                    'year': year,
                    'signal': cited,
                    'url': url_value,
                    'source': 'OpenAlex',
                    'query': query,
                }
            )
        if items:
            break
    return items


def fetch_arxiv_items(query: str, max_results: int = 4) -> list[dict[str, Any]]:
    url = (
        'http://export.arxiv.org/api/query?search_query=all:'
        + quote_plus(query)
        + f'&start=0&max_results={max(1, min(20, max_results))}&sortBy=submittedDate&sortOrder=descending'
    )
    raw = fetch_text(url)
    root = ET.fromstring(raw)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    items: list[dict[str, Any]] = []
    for entry in root.findall('atom:entry', ns):
        title = sanitize_text(entry.findtext('atom:title', default='', namespaces=ns))
        if not title:
            continue
        summary = sanitize_text(entry.findtext('atom:summary', default='', namespaces=ns))
        published = sanitize_text(entry.findtext('atom:published', default='', namespaces=ns))
        year = 0
        if re.match(r'^\d{4}-\d{2}-\d{2}', published):
            year = int(published[:4])
        link = ''
        for candidate in entry.findall('atom:link', ns):
            href = sanitize_text(candidate.attrib.get('href', ''))
            rel = sanitize_text(candidate.attrib.get('rel', ''))
            if href and (not rel or rel == 'alternate'):
                link = href
                break
        items.append(
            {
                'title': title,
                'summary': summary,
                'year': year,
                'signal': 0,
                'url': link,
                'source': 'arXiv',
                'query': query,
            }
        )
    return items


def gather_live_research(title: str, lead: str, tags: list[str]) -> dict[str, Any]:
    queries = build_research_queries(title, lead, tags)
    focus = detect_focus_areas(title, lead, tags)
    all_items: list[dict[str, Any]] = []
    failures: list[str] = []
    for query in queries:
        try:
            all_items.extend(fetch_openalex_items(query))
        except Exception as exc:
            failures.append(f'openalex:{query}:{sanitize_text(exc)}')
        if 'ai-learning' in focus:
            try:
                all_items.extend(fetch_arxiv_items(query))
            except Exception as exc:
                failures.append(f'arxiv:{query}:{sanitize_text(exc)}')

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in all_items:
        title_key = re.sub(r'\W+', ' ', sanitize_text(item.get('title', '')).lower()).strip()
        if not title_key or title_key in seen:
            continue
        seen.add(title_key)
        deduped.append(item)

    seed_text = sanitize_text(' '.join([title, lead, ' '.join(tags), ' '.join(queries)])).lower()
    seed_tokens = {
        tok for tok in re.findall(r'\b[a-z]{4,}\b', seed_text)
        if tok not in RESEARCH_TOKEN_STOPWORDS
    }
    strict_seed = {
        tok for tok in re.findall(r'\b[a-z]{4,}\b', sanitize_text(f"{title} {' '.join(tags)}").lower())
        if tok not in RESEARCH_TOKEN_STOPWORDS
    }
    focus_terms: set[str] = set()
    for key in focus:
        focus_terms |= FOCUS_AREA_FILTER_TERMS.get(key, set())

    def relevance_score(item: dict[str, Any]) -> int:
        hay = sanitize_text(f"{item.get('title', '')} {item.get('summary', '')}").lower()
        hay_tokens = {
            tok for tok in re.findall(r'\b[a-z]{3,}\b', hay)
            if tok not in RESEARCH_TOKEN_STOPWORDS
        }
        if re.search(r'\b(emergency|hospital|patient|clinical|surgery|biomedical|molecule|genome|protein)\b', hay):
            return -10

        has_business_context = bool(hay_tokens & BUSINESS_CONTEXT_TERMS)
        if not has_business_context:
            return -6

        overlap = len(hay_tokens & seed_tokens)
        strict_overlap = len(hay_tokens & strict_seed)
        focus_overlap = len(hay_tokens & focus_terms)
        practice_bonus = 1 if re.search(r'\b(workforce|workplace|manager|team|training|coaching|behavior|analytics|capability)\b', hay) else 0
        drift_penalty = 1 if re.search(r'\b(3d|vision|image|video|robot)\b', hay) else 0
        focus_guard = -2 if focus_terms and focus_overlap == 0 else 0
        strict_guard = -4 if strict_seed and strict_overlap == 0 else 0
        return (overlap * 3) + (strict_overlap * 3) + (focus_overlap * 2) + practice_bonus + focus_guard + strict_guard - drift_penalty

    scored = [(relevance_score(item), item) for item in deduped]
    strong = [pair for pair in scored if pair[0] >= 4]
    selected_scored = strong if strong else [pair for pair in scored if pair[0] >= 1]

    ranked = [
        item for _, item in sorted(
            selected_scored,
            key=lambda pair: (
                pair[0],
                int(pair[1].get('year') or 0),
                int(pair[1].get('signal') or 0),
                sanitize_text(pair[1].get('title', '')),
            ),
            reverse=True,
        )[:RESEARCH_MAX_ITEMS]
    ]

    ideas: list[str] = []
    for item in ranked:
        title_text = sanitize_text(item.get('title', ''))
        if not title_text:
            continue
        phrase_words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9&'-]*", title_text) if w]
        phrase = ' '.join(phrase_words[:8]).strip(' -:;,.')
        if not phrase:
            continue
        candidate = (
            f"One useful direction is {lower_first(phrase)} applied to one weekly team decision with one observable behavior metric."
        )
        idea = sanitize_content_line(candidate)
        if idea:
            ideas.append(idea)
        if len(ideas) >= RESEARCH_IDEA_LIMIT:
            break

    return {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'queries': queries,
        'focus': focus,
        'sources': ranked,
        'ideas': ideas,
        'failures': failures,
    }


def apply_live_research(payload: dict[str, Any]) -> dict[str, Any]:
    title = sanitize_text(payload.get('title', ''))
    lead = sanitize_text(payload.get('lead', ''))
    tags = payload.get('tags', []) if isinstance(payload.get('tags', []), list) else []

    research = gather_live_research(title, lead, [sanitize_text(t) for t in tags if sanitize_text(t)])
    payload['_research_brief'] = {
        'generated_at': research.get('generated_at', ''),
        'queries': research.get('queries', []),
        'sources': [
            {
                'title': item.get('title', ''),
                'year': item.get('year', 0),
                'url': item.get('url', ''),
                'source': item.get('source', ''),
            }
            for item in research.get('sources', [])
        ],
        'failures': research.get('failures', []),
    }

    sections = payload.get('sections', [])
    if not isinstance(sections, list) or not sections:
        return payload

    ideas = research.get('ideas', []) if isinstance(research.get('ideas', []), list) else []
    if not ideas:
        return payload

    existing = {sanitize_text(p).lower() for p in collect_paragraphs(payload)}
    inserted = 0
    section_idx = 0
    for idea in ideas:
        line = sanitize_content_line(idea)
        if not line or line.lower() in existing:
            continue
        target = sections[section_idx % len(sections)]
        paragraphs = target.setdefault('paragraphs', [])
        if not isinstance(paragraphs, list):
            paragraphs = []
            target['paragraphs'] = paragraphs
        if len(paragraphs) >= 6:
            section_idx += 1
            continue
        paragraphs.append(line)
        existing.add(line.lower())
        inserted += 1
        section_idx += 1
        if inserted >= RESEARCH_IDEA_LIMIT:
            break

    if inserted > 0:
        warn(f'Applied {inserted} live research ideas to payload sections')
    return payload


def recent_study_usage(max_posts: int = 60) -> dict[str, int]:
    usage: dict[str, int] = {}
    posts = sorted(
        [p for p in (ROOT / 'posts').glob('*.html') if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:max_posts]
    for post in posts:
        try:
            text = post.read_text()
        except Exception:
            continue
        urls = {u.rstrip('.,;:!?') for u in re.findall(r'https?://[^\s"\'<)]+', text, flags=re.IGNORECASE)}
        for url in urls:
            if not is_study_url(url):
                continue
            key = sanitize_text(url).lower()
            usage[key] = usage.get(key, 0) + 1
    return usage


def default_study_citations(seed: str, count: int = 3) -> list[dict[str, str]]:
    target = max(2, min(8, count))
    if not STUDY_SOURCE_POOL:
        return []
    usage = recent_study_usage()
    topics = infer_topics(seed)
    technical = is_technical_topic(topics)

    def rank_key(item: dict[str, Any]) -> tuple[Any, ...]:
        item_topics = set(item.get('topics', []) or [])
        topical_miss = 0 if (item_topics & topics) else 1
        technical_penalty = 0
        if not technical and 'technical' in item_topics and not (item_topics & {'workforce', 'learning', 'skills'}):
            technical_penalty = 1
        return (
            topical_miss,
            technical_penalty,
            usage.get(item['url'].lower(), 0),
            hashlib.sha256(f'{seed}|{item["url"]}'.encode('utf-8')).hexdigest(),
        )

    ranked = sorted(
        STUDY_SOURCE_POOL,
        key=rank_key,
    )
    return [{'title': item['title'], 'url': item['url']} for item in ranked[:target]]


def is_generic_citation_title(title: str) -> bool:
    value = sanitize_text(title).lower()
    if not value:
        return True
    if value in {'source', 'study', 'reference', 'link'}:
        return True
    if re.match(r'^source\s*\d*$', value):
        return True
    if re.match(r'^reference\s*\d*$', value):
        return True
    return False


def citation_title_from_url(url: str) -> str:
    value = sanitize_text(url)
    lower = value.lower()
    for item in STUDY_SOURCE_POOL:
        if item['url'].lower() == lower:
            return item['title']
    if 'nber.org/papers/' in lower:
        return 'NBER Working Paper'
    if 'arxiv.org/abs/' in lower:
        return 'arXiv preprint'
    if 'doi.org/' in lower:
        return 'DOI-linked study'
    if 'ourworldindata.org/' in lower:
        return 'Our World in Data'
    if 'gallup.com/workplace/' in lower:
        return 'Gallup workplace research'
    if 'weforum.org/reports/' in lower:
        return 'World Economic Forum report'
    if 'oecd.org/' in lower:
        return 'OECD report'
    if 'learning.linkedin.com/' in lower:
        return 'LinkedIn Learning report'
    return value


def ensure_study_citations(
    citations: list[dict[str, str]],
    *,
    seed: str,
    min_count: int = 0,
    required_new_domains: int = 0,
    recent_domains: set[str] | None = None,
    max_count: int = CITATION_MAX_COUNT,
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in citations:
        url = sanitize_text(item.get('url', ''))
        title = sanitize_text(item.get('title', '') or url)
        if not url or url in seen:
            continue
        if is_generic_citation_title(title):
            title = citation_title_from_url(url)
        seen.add(url)
        filtered.append({'title': title, 'url': url})

    target = max(0, min(int(min_count), max_count))
    required_new_domains = max(0, int(required_new_domains))
    prior_domains = {sanitize_text(d).lower().strip() for d in (recent_domains or set()) if sanitize_text(d)}
    if target <= 0:
        return []

    topics = infer_topics(seed)
    technical = is_technical_topic(topics)
    max_arxiv = target if technical else max(1, target // 2)
    usage = recent_study_usage()

    domain_count = len({citation_domain(item['url']) for item in filtered if citation_domain(item['url'])})
    arxiv_count = sum(1 for item in filtered if citation_domain(item['url']) == 'arxiv.org')
    new_domain_count = len({d for d in {citation_domain(item['url']) for item in filtered} if d and d not in prior_domains})

    for item in default_study_citations(seed, count=max(8, target + 3)):
        url = item['url']
        if url in seen:
            continue
        domain = citation_domain(url)
        if not technical and domain == 'arxiv.org' and arxiv_count >= max_arxiv:
            continue
        seen.add(url)
        filtered.append({'title': item['title'], 'url': url})
        if domain == 'arxiv.org':
            arxiv_count += 1
        if domain:
            domain_count = len({citation_domain(c['url']) for c in filtered if citation_domain(c['url'])})
            if domain not in prior_domains:
                new_domain_count += 1
        if len(filtered) >= target and new_domain_count >= required_new_domains:
            break

    def rank_key(item: dict[str, str]) -> tuple[Any, ...]:
        item_url = item['url']
        domain = citation_domain(item_url)
        pool_entry = next((p for p in STUDY_SOURCE_POOL if p['url'].lower() == item_url.lower()), None)
        item_topics = set(pool_entry.get('topics', []) if pool_entry else [])
        topical_miss = 0 if (item_topics & topics) else 1
        arxiv_penalty = 1 if (not technical and domain == 'arxiv.org') else 0
        return (
            topical_miss,
            arxiv_penalty,
            usage.get(item_url.lower(), 0),
            hashlib.sha256(f'{seed}|{item_url}'.encode('utf-8')).hexdigest(),
        )

    ranked = sorted(filtered, key=rank_key)

    selected: list[dict[str, str]] = []
    selected_domains: set[str] = set()
    selected_arxiv = 0
    desired = target
    for item in ranked:
        domain = citation_domain(item['url'])
        if not technical and domain == 'arxiv.org' and selected_arxiv >= max_arxiv:
            continue
        selected.append(item)
        if domain:
            selected_domains.add(domain)
        if domain == 'arxiv.org':
            selected_arxiv += 1
        selected_new_domains = {d for d in selected_domains if d and d not in prior_domains}
        if len(selected) >= desired and len(selected_new_domains) >= required_new_domains:
            break

    if len({d for d in selected_domains if d and d not in prior_domains}) < required_new_domains:
        for item in ranked:
            if item in selected:
                continue
            domain = citation_domain(item['url'])
            if domain and domain not in selected_domains and domain not in prior_domains:
                selected.append(item)
                selected_domains.add(domain)
                if domain == 'arxiv.org':
                    selected_arxiv += 1
                if len({d for d in selected_domains if d and d not in prior_domains}) >= required_new_domains:
                    break

    if required_new_domains > 0 and selected:
        chosen: list[dict[str, str]] = []
        chosen_domains: set[str] = set()
        for item in selected:
            domain = citation_domain(item.get('url', ''))
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


def ensure_date(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return datetime.now().strftime('%B %d, %Y').replace(' 0', ' ')


def collect_text_for_count(payload: dict[str, Any]) -> str:
    parts: list[str] = [payload.get('lead', '')]
    for section in payload.get('sections', []):
        for p in section.get('paragraphs', []):
            parts.append(p)
    for bullet in payload.get('bullets', []):
        parts.append(bullet)
    parts.append(payload.get('closing', ''))
    parts.append(payload.get('meta_description', ''))
    return '\n'.join(parts)


def collect_paragraphs(payload: dict[str, Any]) -> list[str]:
    paragraphs: list[str] = []
    for section in payload.get('sections', []):
        for paragraph in section.get('paragraphs', []):
            text = sanitize_text(paragraph)
            if text:
                paragraphs.append(text)
    if sanitize_text(payload.get('closing', '')):
        paragraphs.append(sanitize_text(payload.get('closing', '')))
    return paragraphs


def collect_content_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ('lead', 'excerpt', 'closing', 'meta_description'):
        value = sanitize_text(payload.get(key, ''))
        if value:
            lines.append(value)
    for section in payload.get('sections', []):
        for paragraph in section.get('paragraphs', []):
            value = sanitize_text(paragraph)
            if value:
                lines.append(value)
    for bullet in payload.get('bullets', []):
        value = sanitize_text(bullet)
        if value:
            lines.append(value)
    return lines


def tighten_to_target(payload: dict[str, Any], min_words: int = QUALITY_MIN_WORDS, max_words: int = QUALITY_MAX_WORDS) -> None:
    def current() -> int:
        return word_count(collect_text_for_count(payload))

    payload['sections'] = ensure_section_headings(payload.get('sections', []), payload.get('title', ''))
    title_topic = sanitize_text(payload.get('title', '')) or 'this topic'
    paragraph_seed = collect_paragraphs(payload)
    paragraph_seed_text = paragraph_seed[0] if paragraph_seed else sanitize_text(payload.get('lead', ''))

    def section_expansion(heading: str, index: int) -> str:
        heading_text = sanitize_text(heading) or 'this section'
        seeds = [
            f'In {heading_text.lower()}, link one decision point to one measurable outcome and one owner.',
            f'Add one short example in {heading_text.lower()} showing what changed after applying the recommendation.',
            f'In {heading_text.lower()}, state one risk and one mitigation so teams can act without ambiguity.',
            f'Close {heading_text.lower()} with one next-step action and one review checkpoint date.',
        ]
        if paragraph_seed_text and len(paragraph_seed_text.split()) > 6:
            seeds.append(
                f'Keep the section aligned with the core idea: {simplify_sentence(paragraph_seed_text, max_words=18)}'
            )
        digest = hashlib.sha256(f'{title_topic}|{heading_text}|{index}'.encode('utf-8')).hexdigest()
        pick = int(digest[:8], 16) % len(seeds)
        return sanitize_content_line(seeds[pick])

    expansion_index = 0
    while current() < min_words:
        sections = payload.get('sections', [])
        if not isinstance(sections, list):
            sections = []
        if not sections:
            sections = ensure_sections([], payload.get('lead', ''), payload.get('excerpt', ''), payload.get('closing', ''), payload.get('title', ''))
            payload['sections'] = sections

        changed = False
        existing = {sanitize_text(p).lower() for p in collect_paragraphs(payload)}
        for section in sections:
            heading = sanitize_text(section.get('heading', ''))
            paragraphs = section.setdefault('paragraphs', [])
            if len(paragraphs) >= 6:
                continue
            candidate = section_expansion(heading, expansion_index)
            expansion_index += 1
            if not candidate or candidate.lower() in existing:
                continue
            paragraphs.append(candidate)
            existing.add(candidate.lower())
            changed = True
            if current() >= min_words:
                break

        if changed:
            continue

        heading = '' if DISABLE_BODY_H2 else SECTION_HEADING_DEFAULTS[len(sections) % len(SECTION_HEADING_DEFAULTS)]
        candidate_a = section_expansion(heading, expansion_index)
        candidate_b = section_expansion(heading, expansion_index + 1)
        payload.setdefault('sections', []).append(
            {
                'heading': heading,
                'paragraphs': [
                    candidate_a,
                    candidate_b,
                ],
            }
        )
        expansion_index += 2

    while current() > max_words:
        changed = False

        bullets = payload.get('bullets', [])
        if isinstance(bullets, list) and len(bullets) > 2:
            bullets.pop()
            changed = True
        if changed:
            continue

        section_total = sum(len(section.get('paragraphs', [])) for section in payload.get('sections', []))
        for section in reversed(payload.get('sections', [])):
            paragraphs = section.get('paragraphs', [])
            if len(paragraphs) > 2 and section_total > QUALITY_MIN_PARAGRAPHS:
                paragraphs.pop()
                section_total -= 1
                changed = True
                break
        if changed:
            continue

        closing = sanitize_text(payload.get('closing', ''))
        if closing:
            trimmed = simplify_sentence(closing, max_words=max(10, word_count(closing) - 4))
            trimmed = sanitize_content_line(trimmed)
            if trimmed and trimmed != closing:
                payload['closing'] = trimmed
                changed = True
        if not changed:
            break


def clamp_score(value: int) -> int:
    return max(1, min(5, value))


def split_sentences(text: str) -> list[str]:
    cleaned = sanitize_text(text)
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r'(?<=[.!?])\s+', cleaned) if part.strip()]


def collect_sentences(payload: dict[str, Any]) -> list[str]:
    sentences: list[str] = []
    for item in [payload.get('lead', ''), payload.get('excerpt', ''), payload.get('closing', '')]:
        sentences.extend(split_sentences(str(item)))
    for section in payload.get('sections', []):
        for paragraph in section.get('paragraphs', []):
            sentences.extend(split_sentences(str(paragraph)))
    return sentences



def normalize_voice_sentence(text: str) -> str:
    value = sanitize_text(text)
    if not value:
        return ''
    value = VOICE_FILLER_PREFIX_RE.sub('', value).strip()
    replacements = {
        "in today's fast-paced world": "today",
        'game changer': 'practical shift',
        'leverage ai': 'use AI intentionally',
        'next level': 'higher signal',
        'unlock potential': 'improve execution quality',
        'move the needle': 'change measurable outcomes',
    }
    lowered = value.lower()
    for source, target in replacements.items():
        if source in lowered:
            value = re.sub(re.escape(source), target, value, flags=re.IGNORECASE)
            lowered = value.lower()
    cleaned = sanitize_content_line(value)
    return cleaned or sanitize_text(value)


def apply_shreyas_tone(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ('lead', 'excerpt', 'meta_description', 'closing'):
        payload[key] = normalize_voice_sentence(payload.get(key, ''))

    sections = payload.get('sections', [])
    if isinstance(sections, list):
        for section in sections:
            raw = section.get('paragraphs', [])
            if not isinstance(raw, list):
                section['paragraphs'] = []
                continue
            normalized: list[str] = []
            seen: set[str] = set()
            for paragraph in raw:
                line = normalize_voice_sentence(paragraph)
                key = sanitize_text(line).lower()
                if not line or key in seen:
                    continue
                seen.add(key)
                normalized.append(line)
            section['paragraphs'] = normalized[:6]

    text_l = collect_text_for_count(payload).lower()
    if not re.search(r'\b(you|your)\b', text_l):
        options = [
            'If you run this with your team this week, track one visible behavior shift before the next review.',
            'Try this once with your team this week and compare what changes before the next decision cycle.',
            'Use one live decision this week so you can see whether the behavior shift is real or just theoretical.',
        ]
        idx = int(hashlib.sha256(sanitize_text(payload.get('title', '')).encode('utf-8')).hexdigest()[:8], 16) % len(options)
        addition = normalize_voice_sentence(options[idx])
        if addition:
            closing = sanitize_text(payload.get('closing', ''))
            if addition.lower() not in closing.lower():
                payload['closing'] = sanitize_text(f'{closing} {addition}') if closing else addition

    payload['bullets'] = []
    return payload


def compute_voice_signals(payload: dict[str, Any]) -> dict[str, Any]:
    text = collect_text_for_count(payload)
    text_l = text.lower()
    banned_hits = sum(1 for pattern in VOICE_BANNED_PATTERNS if pattern.search(text_l))
    second_person_count = len(re.findall(r'\b(you|your)\b', text_l))
    first_person_count = len(re.findall(r'\b(i|we|my|our)\b', text_l))
    sentence_list = collect_sentences(payload)
    avg_sentence_words = 0.0
    if sentence_list:
        avg_sentence_words = sum(word_count(s) for s in sentence_list) / len(sentence_list)
    return {
        'banned_phrase_hits': banned_hits,
        'second_person_count': second_person_count,
        'first_person_count': first_person_count,
        'voice_avg_sentence_words': round(avg_sentence_words, 2),
    }


def historical_blog_iteration_count() -> int:
    posts_dir = ROOT / 'posts'
    if not posts_dir.exists():
        return 0
    count = 0
    for path in posts_dir.glob('*.html'):
        if path.name.startswith('_'):
            continue
        count += 1
    return count


def load_improvement_engine() -> dict[str, Any]:
    engine: dict[str, Any] = {}
    if IMPROVEMENT_ENGINE_FILE.exists():
        try:
            raw = json.loads(IMPROVEMENT_ENGINE_FILE.read_text())
            if isinstance(raw, dict):
                engine = raw
        except Exception:
            engine = {}

    baseline_runs = historical_blog_iteration_count()
    current_runs = int(engine.get('runs') or 0)
    if baseline_runs > current_runs:
        engine['runs'] = baseline_runs
        engine.setdefault('bootstrapped_from_posts', baseline_runs)
    return engine


def save_improvement_engine(engine: dict[str, Any]) -> None:
    IMPROVEMENT_ENGINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPROVEMENT_ENGINE_FILE.write_text(json.dumps(engine, indent=2))


def apply_improvement_engine(payload: dict[str, Any], engine: dict[str, Any]) -> list[str]:
    counts = engine.get('dimension_miss_counts', {}) if isinstance(engine.get('dimension_miss_counts', {}), dict) else {}
    ranked = sorted(
        [dim for dim in QUALITY_DIMENSIONS if int(counts.get(dim) or 0) > 0],
        key=lambda dim: int(counts.get(dim) or 0),
        reverse=True,
    )
    picked = ranked[:2]
    if picked:
        apply_quality_rewrite(payload, picked)
    if int(engine.get('voice_miss_count') or 0) > 0:
        payload = apply_shreyas_tone(payload)
    return picked


def update_improvement_engine(
    engine: dict[str, Any],
    payload: dict[str, Any],
    final_report: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    updated = engine if isinstance(engine, dict) else {}
    updated['runs'] = int(updated.get('runs') or 0) + 1
    updated['pass_streak'] = (int(updated.get('pass_streak') or 0) + 1) if status == 'pass' else 0

    counts = updated.get('dimension_miss_counts', {}) if isinstance(updated.get('dimension_miss_counts', {}), dict) else {}
    for dim in QUALITY_DIMENSIONS:
        score = int(final_report.get('scores', {}).get(dim, {}).get('score') or 0)
        if score <= 3:
            counts[dim] = int(counts.get(dim) or 0) + 1
        else:
            counts[dim] = max(0, int(counts.get(dim) or 0) - 1)
    updated['dimension_miss_counts'] = counts

    signals = final_report.get('signals', {}) if isinstance(final_report.get('signals', {}), dict) else {}
    voice_miss = int(updated.get('voice_miss_count') or 0)
    if int(signals.get('banned_phrase_hits') or 0) > 0 or int(signals.get('second_person_count') or 0) == 0:
        voice_miss += 1
    else:
        voice_miss = max(0, voice_miss - 1)
    updated['voice_miss_count'] = voice_miss

    citation_meta = payload.get('_citation_meta', {}) if isinstance(payload.get('_citation_meta', {}), dict) else {}
    confidence = float(citation_meta.get('confidence') or 0.0)
    trust = float(updated.get('citation_trust') or 0.0)
    updated['citation_trust'] = round((trust * 0.8) + (confidence * 0.2), 4)

    updated['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
    return updated


def should_require_optional_citations(payload: dict[str, Any]) -> bool:
    text = collect_text_for_count(payload).lower()
    has_keyword = re.search(r'\b(study|research|report|survey|evidence)\b', text) is not None
    has_according = 'according to' in text
    has_numeric_claim = re.search(r'\b\d+(?:\.\d+)?%?\b', text) is not None
    return (has_keyword or has_according) and has_numeric_claim


def source_quality_score(source: dict[str, Any], seed_tokens: set[str]) -> float:
    title = sanitize_text(source.get('title', '')).lower()
    url = sanitize_text(source.get('url', ''))
    domain = citation_domain(url)
    year = int(source.get('year') or 0)
    current_year = datetime.utcnow().year

    score = 0.0
    if domain in TRUSTED_CITATION_DOMAINS:
        score += 0.45
    elif is_study_url(url):
        score += 0.3

    if year >= current_year - 1:
        score += 0.25
    elif year >= current_year - 3:
        score += 0.18
    elif year > 0:
        score += 0.1

    title_tokens = {tok for tok in re.findall(r'\b[a-z]{4,}\b', title) if tok not in RESEARCH_TOKEN_STOPWORDS}
    overlap = len(title_tokens & seed_tokens)
    if overlap >= 2:
        score += 0.25
    elif overlap == 1:
        score += 0.12

    if url.startswith('http'):
        score += 0.05
    return min(1.0, max(0.0, score))


def select_optional_citations(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get('_research_brief', {}).get('sources', []) if isinstance(payload.get('_research_brief', {}), dict) else []
    seed = sanitize_text(f"{payload.get('title', '')} {' '.join(payload.get('tags', []))}").lower()
    seed_tokens = {tok for tok in re.findall(r'\b[a-z]{4,}\b', seed) if tok not in RESEARCH_TOKEN_STOPWORDS}

    scored: list[tuple[float, dict[str, Any]]] = []
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict):
            continue
        url = sanitize_text(source.get('url', ''))
        title = sanitize_text(source.get('title', ''))
        if not url.startswith('http') or not title:
            continue
        score = source_quality_score(source, seed_tokens)
        if score <= 0.6:
            continue
        scored.append((score, source))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:OPTIONAL_CITATION_MAX]
    confidence = round(sum(item[0] for item in top) / max(1, len(top)), 4)
    requires = should_require_optional_citations(payload)

    citations: list[dict[str, str]] = []
    if requires and confidence >= OPTIONAL_CITATION_MIN_CONFIDENCE:
        used_domains: set[str] = set()
        for score, source in top:
            url = sanitize_text(source.get('url', ''))
            title = sanitize_text(source.get('title', ''))
            domain = citation_domain(url)
            if domain and domain in used_domains:
                continue
            citations.append({'title': title, 'url': url})
            if domain:
                used_domains.add(domain)
            if len(citations) >= OPTIONAL_CITATION_MAX:
                break

    return {
        'required': requires,
        'confidence': confidence,
        'candidate_count': len(scored),
        'selected_count': len(citations),
        'citations': citations,
    }


def quality_report(payload: dict[str, Any]) -> dict[str, Any]:
    text = collect_text_for_count(payload)
    text_l = text.lower()
    words = word_count(text)
    sections = payload.get('sections', []) if isinstance(payload.get('sections', []), list) else []
    headings = [sanitize_text(section.get('heading', '')) for section in sections if sanitize_text(section.get('heading', ''))]
    heading_count = len(headings)
    section_count = len(sections)
    paragraphs = collect_paragraphs(payload)
    paragraph_count = len(paragraphs)
    short_paragraph_count = sum(1 for p in paragraphs if word_count(p) < 14)
    duplicate_paragraph_count = max(0, paragraph_count - len({p.lower() for p in paragraphs}))

    sentences = collect_sentences(payload)
    sentence_count = len(sentences)
    avg_sentence_words = words / sentence_count if sentence_count else 0.0
    long_sentence_count = sum(1 for s in sentences if word_count(s) >= 28)
    duplicate_sentence_count = max(0, len(sentences) - len({s.lower() for s in sentences}))
    content_lines = collect_content_lines(payload)
    instruction_line_count = sum(1 for line in content_lines if is_instructional_line(line))
    fragment_line_count = sum(1 for line in content_lines if is_likely_sentence_fragment(line))
    style_drift_count = sum(1 for line in content_lines if any(pattern.search(line) for pattern in STYLE_DRIFT_PATTERNS))
    lead_words = word_count(payload.get('lead', ''))
    number_hits = len(re.findall(r'\b(?:\d+(?:\.\d+)?%?|20\d{2})\b', text))

    tokens = re.findall(r'\b[a-z][a-z0-9-]{2,}\b', text_l)
    unique_ratio = (len(set(tokens)) / len(tokens)) if tokens else 0.0

    voice = compute_voice_signals(payload)
    citation_meta = payload.get('_citation_meta', {}) if isinstance(payload.get('_citation_meta', {}), dict) else {}
    citation_confidence = float(citation_meta.get('confidence') or 0.0)

    citations = payload.get('citations', [])
    citation_count = len(citations) if isinstance(citations, list) else 0
    citation_policy = parse_citation_policy(payload)
    required_citation_count = int(citation_policy['target_count'])
    required_new_domain_count = int(citation_policy['required_new_domains'])
    prior_domains = set(citation_policy['recent_domains'])
    generic_citation_titles = 0
    citation_domains: set[str] = set()
    arxiv_citation_count = 0
    topic_text = f'{payload.get("title", "")} {payload.get("lead", "")} {" ".join(payload.get("tags", []))}'
    topics = infer_topics(topic_text)
    technical_topic = is_technical_topic(topics)
    topic_relevant_citation_count = 0
    if isinstance(citations, list):
        for item in citations:
            url = sanitize_text(item.get('url', '') if isinstance(item, dict) else '')
            title = sanitize_text(item.get('title', '') if isinstance(item, dict) else '')
            if is_generic_citation_title(title):
                generic_citation_titles += 1
            domain = citation_domain(url)
            if domain:
                citation_domains.add(domain)
                if domain == 'arxiv.org':
                    arxiv_citation_count += 1
            pool_entry = next((p for p in STUDY_SOURCE_POOL if p['url'].lower() == url.lower()), None)
            if pool_entry and (set(pool_entry.get('topics', []) or []) & topics):
                topic_relevant_citation_count += 1
    new_domain_count = len({domain for domain in citation_domains if domain not in prior_domains})
    metric_terms_found = len({tok for tok in tokens if tok in QUALITY_METRIC_TERMS})
    action_terms_found = len({tok for tok in tokens if tok in QUALITY_ACTION_TERMS})
    cliche_hits = sum(1 for pattern in QUALITY_CLICHE_PATTERNS if re.search(pattern, text_l))
    has_cadence = re.search(r'\b(daily|weekly|monthly|sprint|cadence|roadmap)\b', text_l) is not None
    has_sequence = re.search(r'\b(first|next|then|finally|step)\b', text_l) is not None
    has_contrast = re.search(r'\b(unlike|instead|however|while)\b', text_l) is not None
    has_evidence_language = re.search(
        r'\b(baseline|benchmark|source|sources|before|after|experiment|measure|measured)\b',
        text_l,
    ) is not None

    clarity = 3
    if 10 <= avg_sentence_words <= 24:
        clarity += 1
    if long_sentence_count == 0:
        clarity += 1
    if long_sentence_count >= 2:
        clarity -= 1
    if lead_words < 10:
        clarity -= 1
    if short_paragraph_count >= 2:
        clarity -= 1
    if QUALITY_MIN_HEADINGS > 0 and heading_count >= QUALITY_MIN_HEADINGS:
        clarity += 1
    if duplicate_sentence_count:
        clarity -= 1
    if duplicate_paragraph_count:
        clarity -= 1
    if style_drift_count > 0:
        clarity -= 1
    if int(voice.get('banned_phrase_hits') or 0) > 0:
        clarity -= 1
    clarity = clamp_score(clarity)

    specificity = 2
    if number_hits >= 2:
        specificity += 1
    if metric_terms_found >= 2:
        specificity += 1
    if len(payload.get('tags', [])) >= 2:
        specificity += 1
    if re.search(r'\b(within|by|per)\b', text_l) and number_hits >= 1:
        specificity += 1
    if paragraph_count >= QUALITY_MIN_PARAGRAPHS:
        specificity += 1
    if cliche_hits >= 2:
        specificity -= 1
    specificity = clamp_score(specificity)

    evidence = 2
    if number_hits >= 1:
        evidence += 1
    if metric_terms_found >= 2:
        evidence += 1
    if has_evidence_language:
        evidence += 1
    if has_cadence:
        evidence += 1
    if cliche_hits >= 2:
        evidence -= 1
    evidence = clamp_score(evidence)

    originality = 2
    if unique_ratio >= 0.58:
        originality += 1
    if cliche_hits == 0:
        originality += 1
    if has_contrast:
        originality += 1
    if duplicate_paragraph_count == 0 and paragraph_count > 0:
        originality += 1
    if duplicate_sentence_count == 0 and sentence_count > 0:
        originality += 1
    if duplicate_paragraph_count > QUALITY_MAX_DUP_PARAGRAPHS:
        originality -= 1
    if cliche_hits >= 2:
        originality -= 1
    if style_drift_count > 0:
        originality -= 1
    if int(voice.get('banned_phrase_hits') or 0) > 0:
        originality -= 1
    originality = clamp_score(originality)

    actionability = 2
    bullet_count = len(payload.get('bullets', []))
    if bullet_count >= 2:
        actionability += 2
    if action_terms_found >= 3:
        actionability += 1
    if has_cadence:
        actionability += 1
    if has_sequence:
        actionability += 1
    if QUALITY_MIN_HEADINGS > 0 and heading_count >= QUALITY_MIN_HEADINGS:
        actionability += 1
    if paragraph_count >= QUALITY_MIN_PARAGRAPHS:
        actionability += 1
    if int(voice.get('second_person_count') or 0) == 0:
        actionability -= 1
    actionability = clamp_score(actionability)

    score_map = {
        'clarity': clarity,
        'specificity': specificity,
        'evidence': evidence,
        'originality': originality,
        'actionability': actionability,
    }
    total = sum(score_map.values())
    return {
        'scores': {
            dim: {
                'score': score_map[dim],
                'rationale': f'{dim.title()} score based on deterministic writing signals.',
            }
            for dim in QUALITY_DIMENSIONS
        },
        'total': total,
        'max_total': 25,
        'signals': {
            'word_count': words,
            'avg_sentence_words': round(avg_sentence_words, 2),
            'long_sentences': long_sentence_count,
            'duplicate_sentences': duplicate_sentence_count,
            'duplicate_paragraphs': duplicate_paragraph_count,
            'number_hits': number_hits,
            'citation_count': citation_count,
            'required_citation_count': required_citation_count,
            'required_new_domain_count': required_new_domain_count,
            'new_domain_count': new_domain_count,
            'generic_citation_titles': generic_citation_titles,
            'citation_domain_count': len(citation_domains),
            'arxiv_citation_count': arxiv_citation_count,
            'topic_relevant_citation_count': topic_relevant_citation_count,
            'technical_topic': 1 if technical_topic else 0,
            'metric_terms_found': metric_terms_found,
            'action_terms_found': action_terms_found,
            'lexical_diversity': round(unique_ratio, 3),
            'cliche_hits': cliche_hits,
            'bullet_count': bullet_count,
            'section_count': section_count,
            'heading_count': heading_count,
            'paragraph_count': paragraph_count,
            'short_paragraphs': short_paragraph_count,
            'instructional_lines': instruction_line_count,
            'fragment_lines': fragment_line_count,
            'style_drift_lines': style_drift_count,
            'banned_phrase_hits': int(voice.get('banned_phrase_hits') or 0),
            'second_person_count': int(voice.get('second_person_count') or 0),
            'first_person_count': int(voice.get('first_person_count') or 0),
            'voice_avg_sentence_words': float(voice.get('voice_avg_sentence_words') or 0.0),
            'citation_confidence': round(citation_confidence, 4),
        },
    }


def build_quality_critique(report: dict[str, Any], target_total: int) -> list[str]:
    critique: list[str] = []
    ordered = sorted(
        QUALITY_DIMENSIONS,
        key=lambda dim: (report['scores'][dim]['score'], dim),
    )
    for dim in ordered:
        score = int(report['scores'][dim]['score'])
        if score > 3:
            continue
        if dim == 'clarity':
            critique.append('Reduce long sentences and make the opening claim more direct.')
        elif dim == 'specificity':
            critique.append('Add concrete metrics, constraints, or audience-specific details.')
        elif dim == 'evidence':
            critique.append('Support claims with concrete before-after observations and measurable outcomes.')
        elif dim == 'originality':
            critique.append('Replace generic phrasing with a sharper contrast or unique angle.')
        elif dim == 'actionability':
            critique.append('Add explicit next steps, cadence, and execution checkpoints.')

    signals = report.get('signals', {}) if isinstance(report.get('signals', {}), dict) else {}
    if int(signals.get('banned_phrase_hits') or 0) > 0:
        critique.append('Replace generic AI-sounding phrases with direct, plain language in your natural voice.')
    if int(signals.get('second_person_count') or 0) == 0:
        critique.append('Add direct reader address (you/your) so the post sounds conversational and grounded.')

    for hard_failure in report.get('hard_failures', []):
        critique.append(f'Hard requirement: {hard_failure}')

    if report['total'] < target_total:
        critique.append(f'Raise total quality score to at least {target_total}/25 (current {report["total"]}/25).')
    return critique


def hard_quality_failures(report: dict[str, Any]) -> list[str]:
    signals = report.get('signals', {}) if isinstance(report.get('signals', {}), dict) else {}
    failures: list[str] = []
    word_total = int(signals.get('word_count') or 0)
    if word_total < QUALITY_MIN_WORDS:
        failures.append(f'word count {word_total} is below minimum {QUALITY_MIN_WORDS}')
    if word_total > QUALITY_MAX_WORDS:
        failures.append(f'word count {word_total} exceeds maximum {QUALITY_MAX_WORDS}')

    heading_count = int(signals.get('heading_count') or 0)
    if QUALITY_MIN_HEADINGS > 0 and heading_count < QUALITY_MIN_HEADINGS:
        failures.append(f'heading count {heading_count} is below minimum {QUALITY_MIN_HEADINGS}')

    paragraph_count = int(signals.get('paragraph_count') or 0)
    if paragraph_count < QUALITY_MIN_PARAGRAPHS:
        failures.append(f'paragraph count {paragraph_count} is below minimum {QUALITY_MIN_PARAGRAPHS}')

    duplicate_sentences = int(signals.get('duplicate_sentences') or 0)
    if duplicate_sentences > QUALITY_MAX_DUP_SENTENCES:
        failures.append(
            f'duplicate sentence count {duplicate_sentences} exceeds allowed maximum {QUALITY_MAX_DUP_SENTENCES}'
        )

    duplicate_paragraphs = int(signals.get('duplicate_paragraphs') or 0)
    if duplicate_paragraphs > QUALITY_MAX_DUP_PARAGRAPHS:
        failures.append(
            f'duplicate paragraph count {duplicate_paragraphs} exceeds allowed maximum {QUALITY_MAX_DUP_PARAGRAPHS}'
        )

    instruction_lines = int(signals.get('instructional_lines') or 0)
    if instruction_lines > 0:
        failures.append('instruction/prompt text leaked into article body')

    fragment_lines = int(signals.get('fragment_lines') or 0)
    if fragment_lines > 0:
        failures.append('article contains truncated sentence fragments')

    style_drift_lines = int(signals.get('style_drift_lines') or 0)
    if style_drift_lines > 0:
        failures.append('style drift detected from boilerplate/meta writing patterns')

    banned_phrase_hits = int(signals.get('banned_phrase_hits') or 0)
    if banned_phrase_hits > 0:
        failures.append('voice drift detected from generic or robotic phrasing')

    second_person_count = int(signals.get('second_person_count') or 0)
    if second_person_count == 0:
        failures.append('missing conversational direct-address tone (no you/your)')

    return failures


def append_to_last_section(payload: dict[str, Any], sentence: str) -> None:
    sentence = sanitize_content_line(sentence)
    if not sentence:
        return
    sections = payload.get('sections', [])
    if not sections:
        sections.append({'heading': '', 'paragraphs': [sentence]})
        payload['sections'] = sections
        return
    paragraphs = sections[-1].setdefault('paragraphs', [])
    if sentence in paragraphs:
        return
    paragraphs.append(sentence)


def simplify_sentence(text: str, max_words: int = 24) -> str:
    cleaned = sanitize_text(text)
    words = cleaned.split()
    if len(words) <= max_words:
        return sanitize_content_line(cleaned) or cleaned
    short = ' '.join(words[:max_words]).rstrip(',;:')
    if short and short[-1] not in '.!?':
        short += '.'
    return sanitize_content_line(short) or short


def reinforce_clarity(payload: dict[str, Any]) -> None:
    payload['lead'] = simplify_sentence(payload.get('lead', ''), max_words=22)
    payload['closing'] = simplify_sentence(payload.get('closing', ''), max_words=24)
    sections = payload.get('sections', [])
    for section in sections[:1]:
        paragraphs = section.get('paragraphs', [])
        if paragraphs:
            paragraphs[0] = simplify_sentence(paragraphs[0], max_words=24)


def reinforce_specificity(payload: dict[str, Any]) -> None:
    topic = sanitize_text(payload.get('title', 'this topic')).lower()
    options = [
        f'For {topic}, define one observable behavior shift and the exact review moment where the team will evaluate it.',
        f'Anchor {topic} to one recurring decision point so readers can test the guidance without redesigning their whole workflow.',
        f'In {topic}, pair each recommendation with one concrete context where it should be applied first.',
    ]
    pick = int(hashlib.sha256(f'{topic}|specificity'.encode('utf-8')).hexdigest()[:8], 16) % len(options)
    append_to_last_section(payload, options[pick])


def reinforce_evidence(payload: dict[str, Any]) -> None:
    topic = sanitize_text(payload.get('title', 'this topic')).lower()
    options = [
        f'For {topic}, anchor one key claim to an observable before-after change in real team behavior.',
        f'In {topic}, evidence is strongest when the article names one measurable outcome and its review cadence.',
        f'For {topic}, pair each recommendation with one practical signal that readers can verify in their own workflow.',
    ]
    pick = int(hashlib.sha256(f'{topic}|evidence'.encode('utf-8')).hexdigest()[:8], 16) % len(options)
    append_to_last_section(payload, options[pick])


def reinforce_originality(payload: dict[str, Any]) -> None:
    replacements = {
        'game changer': 'practical shift',
        'leverage ai': 'use AI intentionally',
        "in today's fast-paced world": 'in this operating context',
        'next level': 'higher signal',
        'move the needle': 'change measurable outcomes',
        'unlock potential': 'improve execution quality',
    }
    for key in ('lead', 'excerpt', 'closing'):
        value = str(payload.get(key, ''))
        value_l = value.lower()
        for source, target in replacements.items():
            if source in value_l:
                value = re.sub(re.escape(source), target, value, flags=re.IGNORECASE)
                value_l = value.lower()
        payload[key] = sanitize_text(value)

    topic = sanitize_text(payload.get('title', 'this topic')).lower()
    append_to_last_section(
        payload,
        f'Add one field observation from real work so {topic} sounds owned, specific, and not reusable boilerplate.',
    )


def reinforce_actionability(payload: dict[str, Any]) -> None:
    topic = sanitize_text(payload.get('title', 'this topic')).lower()
    options = [
        f'Pick one team ritual this week where {topic} can be tested immediately and reviewed in the next cycle.',
        'Name one owner, one checkpoint, and one expected behavior change before introducing any new learning artifact.',
        'Close with one next action the reader can run in less than a week.',
    ]
    pick = int(hashlib.sha256(f'{topic}|actionability'.encode('utf-8')).hexdigest()[:8], 16) % len(options)
    append_to_last_section(payload, options[pick])
    payload['bullets'] = []


def reinforce_voice(payload: dict[str, Any]) -> None:
    payload = apply_shreyas_tone(payload)
    topic = sanitize_text(payload.get('title', 'this topic')).lower()
    options = [
        f'If you apply {topic} this week, choose one real decision and inspect the behavior change by the next review.',
        f'Use one live workflow this week so you can see whether {topic} actually improves decisions for your team.',
        'Keep the language direct: one concrete decision, one action, one observable outcome by next week.',
    ]
    pick = int(hashlib.sha256(f'{topic}|voice'.encode('utf-8')).hexdigest()[:8], 16) % len(options)
    append_to_last_section(payload, options[pick])


def apply_quality_rewrite(payload: dict[str, Any], dimensions: list[str]) -> None:
    for dim in ordered_unique([d for d in dimensions if d in QUALITY_DIMENSIONS]):
        if dim == 'clarity':
            reinforce_clarity(payload)
        elif dim == 'specificity':
            reinforce_specificity(payload)
        elif dim == 'evidence':
            reinforce_evidence(payload)
        elif dim == 'originality':
            reinforce_originality(payload)
        elif dim == 'actionability':
            reinforce_actionability(payload)
    reinforce_voice(payload)


def load_quality_history() -> dict[str, Any]:
    if not QUALITY_HISTORY_FILE.exists():
        return {}
    try:
        raw = json.loads(QUALITY_HISTORY_FILE.read_text())
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def save_quality_history(history: dict[str, Any]) -> None:
    QUALITY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_HISTORY_FILE.write_text(json.dumps(history, indent=2))


def quality_targets(slug: str, min_total: int, delta: int) -> tuple[int, int, dict[str, Any]]:
    history = load_quality_history()
    by_slug = history.get('by_slug', {})
    entry = by_slug.get(slug, {}) if isinstance(by_slug, dict) else {}
    previous = int(entry.get('last_total') or 0) if isinstance(entry, dict) else 0
    ratchet_cap = min(23, min_total + 3)
    effective_previous = min(previous, ratchet_cap)
    target = max(min_total, effective_previous + (delta if effective_previous > 0 else 0))
    return previous, min(25, target), history


def run_quality_gate(
    payload: dict[str, Any],
    min_total: int = QUALITY_MIN_TOTAL,
    max_passes: int = QUALITY_MAX_PASSES,
    delta: int = QUALITY_DELTA_PER_ITERATION,
) -> dict[str, Any]:
    slug = str(payload.get('slug') or '')
    previous_total, target_total, history = quality_targets(slug, min_total, delta)
    passes: list[dict[str, Any]] = []
    attempts = max(1, max_passes)

    engine = load_improvement_engine()
    engine_dims = apply_improvement_engine(payload, engine)
    payload = apply_shreyas_tone(payload)
    tighten_to_target(payload, QUALITY_MIN_WORDS, QUALITY_MAX_WORDS)

    for index in range(1, attempts + 1):
        payload = apply_shreyas_tone(payload)
        report = quality_report(payload)
        report['pass'] = index
        report['target_total'] = target_total
        report['hard_failures'] = hard_quality_failures(report)
        report['critique'] = build_quality_critique(report, target_total)
        report['shreyas_quality'] = {
            'voice_ok': int(report.get('signals', {}).get('banned_phrase_hits', 0) == 0),
            'direct_address_ok': int(report.get('signals', {}).get('second_person_count', 0) > 0),
        }
        passes.append(report)

        if report['total'] >= target_total and not report['hard_failures']:
            break

        lowest_dims = sorted(
            QUALITY_DIMENSIONS,
            key=lambda dim: (report['scores'][dim]['score'], dim),
        )[:2]

        rewrite_dims = list(lowest_dims)
        signals = report.get('signals', {})
        if int(signals.get('word_count') or 0) < QUALITY_MIN_WORDS or int(signals.get('paragraph_count') or 0) < QUALITY_MIN_PARAGRAPHS:
            rewrite_dims = ordered_unique(['specificity', 'actionability', *rewrite_dims])
        if int(signals.get('heading_count') or 0) < QUALITY_MIN_HEADINGS:
            rewrite_dims = ordered_unique(['clarity', 'actionability', *rewrite_dims])
        if (
            int(signals.get('duplicate_sentences') or 0) > QUALITY_MAX_DUP_SENTENCES
            or int(signals.get('duplicate_paragraphs') or 0) > QUALITY_MAX_DUP_PARAGRAPHS
        ):
            rewrite_dims = ordered_unique(['originality', 'clarity', *rewrite_dims])
        if int(signals.get('banned_phrase_hits') or 0) > 0 or int(signals.get('second_person_count') or 0) == 0:
            rewrite_dims = ordered_unique(['originality', 'clarity', 'actionability', *rewrite_dims])

        apply_quality_rewrite(payload, rewrite_dims[:3])
        tighten_to_target(payload, QUALITY_MIN_WORDS, QUALITY_MAX_WORDS)
        payload = apply_shreyas_tone(payload)

    final = passes[-1]
    gate = {
        'status': 'pass' if final['total'] >= target_total and not final.get('hard_failures') else 'fail',
        'slug': slug,
        'previous_total': previous_total,
        'target_total': target_total,
        'final_total': final['total'],
        'passes': passes,
        'improvement_engine_applied': engine_dims,
    }

    QUALITY_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_FILE.write_text(json.dumps(gate, indent=2))

    engine = update_improvement_engine(engine, payload, final, gate['status'])
    save_improvement_engine(engine)

    if gate['status'] != 'pass':
        reasons = list(final.get('hard_failures', [])[:3])
        reasons.extend([item for item in final.get('critique', []) if not str(item).startswith('Hard requirement: ')][:2])
        critique = '; '.join(reasons) or 'quality gate requirements not met'
        raise ValueError(f'Quality gate failed for "{slug}": {critique}')

    by_slug = history.get('by_slug')
    if not isinstance(by_slug, dict):
        by_slug = {}
    current = by_slug.get(slug, {})
    runs = int(current.get('runs') or 0) + 1 if isinstance(current, dict) else 1
    by_slug[slug] = {
        'last_total': gate['final_total'],
        'last_scores': {dim: final['scores'][dim]['score'] for dim in QUALITY_DIMENSIONS},
        'last_citation_count': len(payload.get('citations', []) if isinstance(payload.get('citations', []), list) else []),
        'runs': runs,
        'updatedAt': datetime.utcnow().isoformat() + 'Z',
    }
    history['by_slug'] = by_slug
    history['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
    save_quality_history(history)
    return gate


def run_shreyas_quality_check(
    payload: dict[str, Any],
    min_total: int = QUALITY_MIN_TOTAL,
    max_passes: int = QUALITY_MAX_PASSES,
    delta: int = QUALITY_DELTA_PER_ITERATION,
) -> dict[str, Any]:
    return run_quality_gate(payload, min_total=min_total, max_passes=max_passes, delta=delta)


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def load_image_history() -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    try:
        raw = json.loads(HISTORY_FILE.read_text())
        if isinstance(raw, dict) and isinstance(raw.get('recent_ids'), list):
            return [str(v) for v in raw['recent_ids'] if str(v).strip()]
    except Exception:
        return []
    return []


def save_image_history(recent_ids: list[str]) -> None:
    payload = {'recent_ids': recent_ids[:RECENT_IMAGE_WINDOW], 'updatedAt': datetime.utcnow().isoformat() + 'Z'}
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(payload, indent=2))


def infer_themes(title: str, lead: str, tags: list[str]) -> list[str]:
    values = [v.lower() for v in tags]
    values.extend(re.findall(r'\b[a-z0-9]+\b', f'{title} {lead}'.lower()))
    themes: list[str] = []
    for value in values:
        theme = UNSPLASH_KEYWORD_THEME.get(value)
        if theme:
            themes.append(theme)
    if not themes:
        themes.append('base')
    return ordered_unique(themes)


def stable_rank(seed: str, value: str) -> str:
    return hashlib.sha256(f'{seed}|{value}'.encode('utf-8')).hexdigest()


def build_candidate_ids(title: str, lead: str, tags: list[str]) -> list[str]:
    themes = infer_themes(title, lead, tags)
    ids: list[str] = []
    for theme in themes:
        ids.extend(UNSPLASH_THEME_IDS.get(theme, []))
    ids.extend(UNSPLASH_THEME_IDS['base'])
    ids = ordered_unique(ids)

    seed = f"{title.lower()}|{lead.lower()}|{','.join(sorted(tags))}|{datetime.utcnow().strftime('%Y-%m-%d')}"
    ids.sort(key=lambda x: stable_rank(seed, x))

    recent = load_image_history()
    fresh = [i for i in ids if i not in recent]
    stale = [i for i in ids if i in recent]
    return fresh + stale


def unsplash_url(photo_id: str) -> str:
    return f'https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1400&h=900&fm=jpg&q=78'


def url_ok(url: str) -> bool:
    try:
        req = Request(url, method='HEAD')
        with urlopen(req, timeout=8) as resp:
            code = getattr(resp, 'status', 200)
            if 200 <= code < 400:
                return True
    except Exception:
        pass

    try:
        with urlopen(url, timeout=8) as resp:
            code = getattr(resp, 'status', 200)
            return 200 <= code < 400
    except Exception:
        return False


def choose_image(title: str, lead: str, tags: list[str], slug: str) -> dict[str, Any]:
    for photo_id in build_candidate_ids(title, lead, tags):
        url = unsplash_url(photo_id)
        if not url_ok(url):
            continue

        recent = load_image_history()
        updated = [photo_id] + [x for x in recent if x != photo_id]
        save_image_history(updated)

        return {
            'url': url,
            'filename': f'{slug}-{photo_id[:10]}.jpg',
            'alt': title,
            'credit': 'Photo by Unsplash.',
            'lock_image_url': True,
        }

    warn('Could not validate fresh Unsplash candidate; publish_post.py will fall back to default image if needed')
    return {
        'alt': title,
        'credit': 'Photo by Unsplash.',
        'lock_image_url': False,
    }


def normalize_publish_title(raw_title: Any, raw_description: Any) -> str:
    title = sanitize_text(raw_title or '')
    title = re.sub(r'\s*\[[^\]]+\]\s*', ' ', title).strip()
    title = re.sub(r'\bpublish:?\s*$', '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'\bpublis\s*$', '', title, flags=re.IGNORECASE).strip()
    title = normalize_display_title(sanitize_text(title))

    def invalid_title(candidate: str) -> bool:
        value = sanitize_text(candidate)
        value_l = value.lower()
        if not value:
            return True
        if value_l in {'untitled', 'untitled note', 'untitled post', 'new post', 'blog post'}:
            return True
        if len(value_l) < 8:
            return True
        if re.match(r'^(publish|write|draft|create)\s*:?\s*$', value_l):
            return True
        if re.match(r'^(improve|fix|update|rewrite)\b', value_l) and len(value_l.split()) <= 4:
            return True
        return (
            'you are an execution worker' in value_l
            or 'return json only' in value_l
            or value_l.startswith('write and publish a blog post')
            or value_l.startswith('write a blog post')
            or value_l.startswith('write one blog')
            or value_l.startswith('create the final publish-ready blog article')
            or value_l.startswith('create final publish-ready blog article')
            or value_l.startswith('autonomous seo blog sprint')
            or value_l.startswith('autonomous writing sprint')
            or 'dictation #' in value_l
            or 'adhoc-' in value_l
            or 'raw context snippet' in value_l
            or 'summary context' in value_l
            or re.search(r'\bquality score\s*\d+\s*\/\s*\d+\b', value_l) is not None
            or value_l.startswith('[mon ')
            or value_l.startswith('[tue ')
            or value_l.startswith('[wed ')
            or value_l.startswith('[thu ')
            or value_l.startswith('[fri ')
            or value_l.startswith('[sat ')
            or value_l.startswith('[sun ')
        )

    if not invalid_title(title):
        return title

    description = str(raw_description or '')
    match = re.search(r'\bTitle:\s*(.+?)\s+Priority:\s*', description, flags=re.IGNORECASE | re.DOTALL)
    if match:
        recovered = normalize_display_title(sanitize_text(match.group(1)))
        if recovered and not invalid_title(recovered):
            warn(f'Recovered publish title from embedded task field: {recovered[:120]}')
            return recovered

    publish_match = re.search(r'\bpublish\s*:\s*(.+)$', description, flags=re.IGNORECASE | re.MULTILINE)
    if publish_match:
        recovered = normalize_display_title(sanitize_text(publish_match.group(1)))
        if recovered and not invalid_title(recovered):
            warn(f'Recovered publish title from description publish field: {recovered[:120]}')
            return recovered

    die(f'Refusing to publish invalid title: {title or "empty title"}')


def sanitize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    title = normalize_publish_title(raw.get('title', ''), raw.get('description', ''))
    slug = sanitize_text(raw.get('slug', '')) or slugify(title)
    citation_policy = parse_citation_policy(raw)

    lead = sanitize_content_line(raw.get('lead', '') or raw.get('excerpt', '') or title)
    excerpt = sanitize_content_line(raw.get('excerpt', '') or lead)
    meta_description = sanitize_content_line(raw.get('meta_description', '') or excerpt)
    closing = sanitize_content_line(raw.get('closing', '') or lead)

    if not lead:
        lead = sanitize_content_line(
            f'{title} improves when teams attach learning changes to one real decision they revisit every week.'
        )
    if not excerpt:
        excerpt = sanitize_content_line(
            f'{title} is most useful when it clarifies ownership, trade-offs, and follow-through in day-to-day execution.'
        )
    if not meta_description:
        meta_description = sanitize_content_line(
            f'A concise field note on {title.lower()} for teams that want practical behavior change, not generic advice.'
        )
    if not closing:
        closing = sanitize_content_line(
            f'Pick one decision ritual this week, test it once, and carry forward only what clearly improves outcomes.'
        )

    sections = ensure_sections(raw.get('sections', []), lead, excerpt, closing, title)

    bullets_raw = raw.get('bullets', [])
    bullets: list[str] = []
    if isinstance(bullets_raw, list):
        bullets = [sanitize_content_line(b) for b in bullets_raw if sanitize_content_line(b)]
    # Bullets are intentionally disabled for public blog output.
    bullets = []

    tags = normalize_tags(raw.get('tags', []), title, lead)
    citations: list[dict[str, str]] = []

    lead_core = core_keywords(lead)
    closing_core = core_keywords(closing)
    if lead_core and closing_core.isdisjoint(lead_core):
        token = sorted(lead_core)[0]
        closing = f'{closing} This comes back to {token}.'.strip()

    payload: dict[str, Any] = {
        'title': title,
        'slug': slug,
        'date': ensure_date(raw.get('date')),
        'tags': tags,
        'citations': citations,
        '_citation_policy': {
            'target_count': int(citation_policy['target_count']),
            'required_new_domains': int(citation_policy['required_new_domains']),
            'recent_domains': sorted(set(citation_policy['recent_domains'])),
        },
        'lead': lead,
        'excerpt': excerpt,
        'meta_description': meta_description,
        'sections': sections,
        'bullets': bullets[:4],
        'closing': closing,
    }

    payload = apply_live_research(payload)
    payload = apply_shreyas_tone(payload)

    citation_decision = select_optional_citations(payload)
    payload['citations'] = citation_decision.get('citations', []) if isinstance(citation_decision.get('citations', []), list) else []
    payload['_citation_meta'] = {
        'required': bool(citation_decision.get('required', False)),
        'confidence': float(citation_decision.get('confidence', 0.0) or 0.0),
        'candidate_count': int(citation_decision.get('candidate_count', 0) or 0),
        'selected_count': int(citation_decision.get('selected_count', 0) or 0),
    }
    if payload['citations']:
        warn(f"Attached {len(payload['citations'])} optional citation(s) with confidence {payload['_citation_meta']['confidence']:.2f}")

    tighten_to_target(payload, QUALITY_MIN_WORDS, QUALITY_MAX_WORDS)
    payload = apply_shreyas_tone(payload)
    payload['image'] = choose_image(title, lead, tags, slug)
    return payload


def stage_files(slug: str) -> list[str]:
    files = [
        f'posts/{slug}.html',
        'writing.html',
        'sitemap.xml',
        'image-sitemap.xml',
        'rss.xml',
    ]

    post_path = ROOT / 'posts' / f'{slug}.html'
    if post_path.exists():
        html = post_path.read_text()
        match = re.search(r'<img src="\.\./assets/images/blog/([^"]+)"', html)
        if match:
            img = match.group(1).split('?', 1)[0]
            files.append(f'assets/images/blog/{img}')

    run(['git', 'add', *files])
    return files


def has_staged_changes() -> bool:
    proc = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT)
    return proc.returncode != 0


def prepare_publish_branch() -> tuple[str, str | None]:
    # Always publish from a clean branch rooted at latest origin/main.
    cleanup_repo_state()
    stash_ref = None
    if has_worktree_changes():
        warn('Working tree had local changes; stashing before publish run')
        stash_ref = stash_local_changes()

    branch = f"publish/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    run(['git', 'fetch', 'origin', 'main'])
    run(['git', 'checkout', '-B', branch, 'origin/main'])
    return branch, stash_ref


def commit_and_push(message: str) -> str:
    if not has_staged_changes():
        return 'no_changes'

    run(['git', 'commit', '-m', message])

    last_error = ''
    for attempt in range(1, 4):
        push = subprocess.run(['git', 'push', 'origin', 'HEAD:main'], cwd=ROOT, text=True, capture_output=True)
        if push.returncode == 0:
            return 'pushed'

        last_error = (push.stderr or push.stdout or '').strip()
        warn(f'Push attempt {attempt} failed; trying rebase and retry')
        cleanup_repo_state()

        fetch = subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=ROOT, text=True, capture_output=True)
        if fetch.returncode != 0:
            last_error = (fetch.stderr or fetch.stdout or last_error).strip()
            time.sleep(attempt * 2)
            continue

        rebase = subprocess.run(['git', 'rebase', 'origin/main'], cwd=ROOT, text=True, capture_output=True)
        if rebase.returncode != 0:
            subprocess.run(['git', 'rebase', '--abort'], cwd=ROOT, text=True, capture_output=True)
            last_error = (rebase.stderr or rebase.stdout or last_error).strip()

        time.sleep(attempt * 2)

    raise RuntimeError(f'Push failed after retries: {last_error}')


def get_head_sha() -> str:
    proc = run(['git', 'rev-parse', '--short', 'HEAD'], check=False)
    return (proc.stdout or '').strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to raw JSON payload')
    parser.add_argument('--force', action='store_true', help='Force overwrite')
    parser.add_argument('--max-retries', type=int, default=1, help='Max publish retries (default: 1)')
    parser.add_argument(
        '--quality-min-total',
        type=int,
        default=QUALITY_MIN_TOTAL,
        help=f'Minimum quality score target out of 25 (default: {QUALITY_MIN_TOTAL})',
    )
    parser.add_argument(
        '--quality-passes',
        type=int,
        default=QUALITY_MAX_PASSES,
        help=f'Max rewrite passes for quality gate (default: {QUALITY_MAX_PASSES})',
    )
    parser.add_argument(
        '--quality-delta',
        type=int,
        default=QUALITY_DELTA_PER_ITERATION,
        help=f'Required score improvement vs prior slug run (default: {QUALITY_DELTA_PER_ITERATION})',
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        die(f'Input file not found: {input_path}', 2)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_handle = LOCK_FILE.open('w')
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        die('Another publish operation is in progress', 75)

    starting_branch = (run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], check=False).stdout or '').strip() or 'main'
    publish_branch = ''
    stashed_ref = None
    try:
        publish_branch, stashed_ref = prepare_publish_branch()

        raw = json.loads(input_path.read_text())
        payload = sanitize_payload(raw)
        try:
            quality_gate = run_shreyas_quality_check(
                payload,
                min_total=max(1, min(25, int(args.quality_min_total))),
                max_passes=max(1, min(8, int(args.quality_passes))),
                delta=max(0, min(5, int(args.quality_delta))),
            )
        except ValueError as exc:
            die(str(exc))

        payload['quality_gate'] = {
            'final_total': quality_gate['final_total'],
            'target_total': quality_gate['target_total'],
            'previous_total': quality_gate['previous_total'],
            'passes': len(quality_gate.get('passes', [])),
        }
        SANITIZED_PAYLOAD.write_text(json.dumps(payload, indent=2))
        RESEARCH_REPORT_FILE.write_text(json.dumps(payload.get('_research_brief', {}), indent=2))

        cmd = ['python3', str(PUBLISH_SCRIPT), '--input', str(SANITIZED_PAYLOAD), '--no-git']
        if args.force:
            cmd.append('--force')

        attempts = 0
        publish_out = ''
        while True:
            attempts += 1
            proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            publish_out = (proc.stdout or '') + ('\n' + proc.stderr if proc.stderr else '')
            if proc.returncode == 0:
                break

            if attempts > max(1, args.max_retries):
                die(f'publish_post.py failed after {attempts} attempt(s):\n{publish_out}')

            warn('publish_post.py failed; retrying once after short backoff')
            time.sleep(2)

        run(['node', str(FEED_SCRIPT)])

        title = payload['title']
        slug = payload['slug']
        stage_files(slug)

        commit_msg = f'Publish blog post: {title}'
        if len(commit_msg) > 100:
            commit_msg = commit_msg[:97] + '...'

        push_status = commit_and_push(commit_msg)
        sha = get_head_sha()

        final_pass = quality_gate.get('passes', [])[-1] if quality_gate.get('passes', []) else {}
        final_signals = final_pass.get('signals', {}) if isinstance(final_pass.get('signals', {}), dict) else {}
        citation_meta = payload.get('_citation_meta', {}) if isinstance(payload.get('_citation_meta', {}), dict) else {}
        result = {
            'status': 'ok',
            'title': title,
            'slug': slug,
            'url': f'https://shreyaskorad.in/posts/{slug}.html',
            'commit': sha,
            'push': push_status,
            'branch': publish_branch,
            'sanitized_payload': str(SANITIZED_PAYLOAD),
            'quality_report': str(QUALITY_REPORT_FILE),
            'research_report': str(RESEARCH_REPORT_FILE),
            'quality_total': quality_gate['final_total'],
            'quality_target': quality_gate['target_total'],
            'quality_previous': quality_gate['previous_total'],
            'improvement_engine_applied': quality_gate.get('improvement_engine_applied', []),
            'voice_banned_phrase_hits': int(final_signals.get('banned_phrase_hits') or 0),
            'voice_second_person_count': int(final_signals.get('second_person_count') or 0),
            'citation_selected': int(citation_meta.get('selected_count') or 0),
            'citation_confidence': float(citation_meta.get('confidence') or 0.0),
        }
        print(json.dumps(result, indent=2))
    finally:
        if starting_branch and publish_branch and starting_branch != publish_branch:
            subprocess.run(['git', 'checkout', starting_branch], cwd=ROOT, text=True, capture_output=True)
        if stashed_ref:
            restore_stash(stashed_ref)


if __name__ == '__main__':
    main()
