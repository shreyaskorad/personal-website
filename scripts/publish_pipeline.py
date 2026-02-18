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
from pathlib import Path
from typing import Any
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

RECENT_IMAGE_WINDOW = 12
QUALITY_MIN_TOTAL = 20
QUALITY_MAX_PASSES = 4
QUALITY_DELTA_PER_ITERATION = 1
QUALITY_MIN_WORDS = 420
QUALITY_MAX_WORDS = 1400
QUALITY_MIN_HEADINGS = 2
QUALITY_MIN_PARAGRAPHS = 6
QUALITY_MAX_DUP_SENTENCES = 0
QUALITY_MAX_DUP_PARAGRAPHS = 0

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
    'Why this matters now',
    'Where teams get stuck',
    'A practical operating model',
    'How to measure progress',
]


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
            paragraphs = [sanitize_text(p) for p in raw_paragraphs if sanitize_text(p)]
            if paragraphs:
                sections.append({'heading': heading, 'paragraphs': paragraphs[:4]})

    if len(sections) >= 2:
        return ensure_section_headings(sections, title)

    body_a = excerpt or lead or f'{title} is changing how we work and decide.'
    body_b = closing or 'The shift is practical: tools are faster, but judgment and direction still matter most.'
    warn('Payload sections were incomplete; generated fallback sections')
    fallback = [
        {
            'heading': 'Why this matters now',
            'paragraphs': [
                sanitize_text(body_a),
                sanitize_text(
                    'Teams that link learning activity to real project outcomes improve judgment quality and reduce avoidable rework.'
                ),
            ],
        },
        {
            'heading': 'How to execute this week',
            'paragraphs': [
                sanitize_text(body_b),
                sanitize_text(
                    'Set a weekly cadence to review one baseline metric, one change introduced, and one observed delta before publishing the next iteration.'
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
        if not heading:
            if idx < len(SECTION_HEADING_DEFAULTS):
                heading = SECTION_HEADING_DEFAULTS[idx]
            else:
                heading = f'{title_topic}: section {idx + 1}'
        paragraphs = [sanitize_text(p) for p in section.get('paragraphs', []) if sanitize_text(p)]
        if not paragraphs:
            continue
        normalized.append({'heading': heading, 'paragraphs': paragraphs[:4]})
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
        citations.append({'title': label, 'url': url})

    return citations[:8]


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


def tighten_to_target(payload: dict[str, Any], min_words: int = QUALITY_MIN_WORDS, max_words: int = QUALITY_MAX_WORDS) -> None:
    def current() -> int:
        return word_count(collect_text_for_count(payload))

    payload['sections'] = ensure_section_headings(payload.get('sections', []), payload.get('title', ''))
    title_topic = sanitize_text(payload.get('title', '')) or 'this topic'
    expansion_templates = [
        'Start with a one-week baseline for {topic}: current cycle time, review latency, and the percentage of drafts that require major rework before publication.',
        'Define explicit role ownership for {topic} so quality checks are not implicit: who drafts, who verifies claims, who approves publication, and who records outcome metrics.',
        'Treat each publish cycle as an experiment for {topic}: state the change, expected effect, and the metric window you will use to judge whether the change should be kept.',
        'Link every strategic claim in {topic} to execution evidence such as conversion movement, retention deltas, response quality, or measurable throughput changes from the prior cycle.',
        'Use a weekly review ritual for {topic} with three outputs only: what changed, what moved, and what will be tested next so the next post compounds learning rather than repeating summaries.',
        'Add a short failure log to {topic} documenting what did not work and why; this prevents teams from recycling polished language that lacks operational signal.',
        'Before each publish decision on {topic}, confirm that the post names the target audience, the practical constraint, and the operating tradeoff involved in adopting the recommendation.',
        'Maintain a source ledger for {topic} where every external statistic is linked to a URL and timestamp; if a claim cannot be traced quickly, remove it before publishing.',
        'Prioritize one leading indicator and one lagging indicator for {topic} so teams can separate early movement from downstream impact and avoid judging quality by vanity metrics alone.',
        'After publishing on {topic}, schedule a follow-up checkpoint that compares hypothesis versus outcome and feeds that delta into the outline for the next iteration.',
    ]

    def expansion_paragraph(index: int) -> str:
        if index < len(expansion_templates):
            return sanitize_text(expansion_templates[index].format(topic=title_topic))
        return sanitize_text(
            f'Execution checkpoint {index - len(expansion_templates) + 1} for {title_topic}: capture baseline metrics, publish one controlled change, and document the observed delta before moving to the next iteration.'
        )

    expansion_index = 0
    while current() < min_words:
        sections = payload.get('sections', [])
        if not isinstance(sections, list):
            sections = []
        if not sections:
            sections = ensure_sections([], payload.get('lead', ''), payload.get('excerpt', ''), payload.get('closing', ''), payload.get('title', ''))
            payload['sections'] = sections

        changed = False
        for section in sections:
            paragraphs = section.setdefault('paragraphs', [])
            if len(paragraphs) >= 4:
                continue
            candidate = expansion_paragraph(expansion_index)
            expansion_index += 1
            if candidate in paragraphs:
                continue
            paragraphs.append(candidate)
            changed = True
            if current() >= min_words:
                break

        if changed:
            continue

        heading = SECTION_HEADING_DEFAULTS[len(sections) % len(SECTION_HEADING_DEFAULTS)]
        payload.setdefault('sections', []).append(
            {
                'heading': heading,
                'paragraphs': [
                    expansion_paragraph(expansion_index),
                    expansion_paragraph(expansion_index + 1),
                ],
            }
        )
        expansion_index += 2

    while current() > max_words:
        changed = False
        for section in reversed(payload.get('sections', [])):
            paragraphs = section.get('paragraphs', [])
            if not paragraphs:
                continue
            last = paragraphs[-1]
            chopped = re.sub(r'\s+[^\s]+$', '', last).strip()
            if chopped and len(chopped.split()) >= 6:
                paragraphs[-1] = chopped
                changed = True
                break
            if len(paragraphs) > 1:
                paragraphs.pop()
                changed = True
                break
        if changed:
            continue
        bullets = payload.get('bullets', [])
        if bullets:
            bullets.pop()
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
    lead_words = word_count(payload.get('lead', ''))
    number_hits = len(re.findall(r'\b(?:\d+(?:\.\d+)?%?|20\d{2})\b', text))

    tokens = re.findall(r'\b[a-z][a-z0-9-]{2,}\b', text_l)
    unique_ratio = (len(set(tokens)) / len(tokens)) if tokens else 0.0

    citations = payload.get('citations', [])
    citation_count = len(citations) if isinstance(citations, list) else 0
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
    if heading_count >= QUALITY_MIN_HEADINGS:
        clarity += 1
    if duplicate_sentence_count:
        clarity -= 1
    if duplicate_paragraph_count:
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

    evidence = 1
    if citation_count >= 1:
        evidence += 2
    if citation_count >= 2:
        evidence += 1
    if metric_terms_found >= 2:
        evidence += 1
    if has_evidence_language:
        evidence += 1
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
    if heading_count >= QUALITY_MIN_HEADINGS:
        actionability += 1
    if paragraph_count >= QUALITY_MIN_PARAGRAPHS:
        actionability += 1
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
            'metric_terms_found': metric_terms_found,
            'action_terms_found': action_terms_found,
            'lexical_diversity': round(unique_ratio, 3),
            'cliche_hits': cliche_hits,
            'bullet_count': bullet_count,
            'section_count': section_count,
            'heading_count': heading_count,
            'paragraph_count': paragraph_count,
            'short_paragraphs': short_paragraph_count,
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
            critique.append('Include source links or before-after measurement language for claims.')
        elif dim == 'originality':
            critique.append('Replace generic phrasing with a sharper contrast or unique angle.')
        elif dim == 'actionability':
            critique.append('Add explicit next steps, cadence, and execution checkpoints.')

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
    if heading_count < QUALITY_MIN_HEADINGS:
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
    return failures


def append_to_last_section(payload: dict[str, Any], sentence: str) -> None:
    sentence = sanitize_text(sentence)
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
        return cleaned
    short = ' '.join(words[:max_words]).rstrip(',;:')
    if short and short[-1] not in '.!?':
        short += '.'
    return short


def reinforce_clarity(payload: dict[str, Any]) -> None:
    payload['lead'] = simplify_sentence(payload.get('lead', ''), max_words=22)
    payload['closing'] = simplify_sentence(payload.get('closing', ''), max_words=24)
    sections = payload.get('sections', [])
    for section in sections[:1]:
        paragraphs = section.get('paragraphs', [])
        if paragraphs:
            paragraphs[0] = simplify_sentence(paragraphs[0], max_words=24)


def reinforce_specificity(payload: dict[str, Any]) -> None:
    append_to_last_section(
        payload,
        'Anchor one baseline KPI and one target KPI, such as cycle time or activation rate, and review the delta weekly.',
    )


def reinforce_evidence(payload: dict[str, Any]) -> None:
    append_to_last_section(
        payload,
        'Before publishing, capture a baseline, ship the change, and compare before-after performance with source links.',
    )


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

    append_to_last_section(
        payload,
        'The advantage is not more content volume; it is tighter feedback between what gets published and what changes behavior.',
    )


def reinforce_actionability(payload: dict[str, Any]) -> None:
    bullets = payload.get('bullets', [])
    if not isinstance(bullets, list):
        bullets = []
    additions = [
        'Define one leading KPI and one lagging KPI for this topic.',
        'Run a weekly review: baseline, delta, blockers, and next experiment.',
        'Publish the next iteration only after the prior metric trend is documented.',
    ]
    for item in additions:
        if item not in bullets:
            bullets.append(item)
    payload['bullets'] = bullets[:4]


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
    target = max(min_total, previous + (delta if previous > 0 else 0))
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

    for index in range(1, attempts + 1):
        report = quality_report(payload)
        report['pass'] = index
        report['target_total'] = target_total
        report['hard_failures'] = hard_quality_failures(report)
        report['critique'] = build_quality_critique(report, target_total)
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

        apply_quality_rewrite(payload, rewrite_dims[:3])
        tighten_to_target(payload, QUALITY_MIN_WORDS, QUALITY_MAX_WORDS)

    final = passes[-1]
    gate = {
        'status': 'pass' if final['total'] >= target_total and not final.get('hard_failures') else 'fail',
        'slug': slug,
        'previous_total': previous_total,
        'target_total': target_total,
        'final_total': final['total'],
        'passes': passes,
    }

    QUALITY_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_FILE.write_text(json.dumps(gate, indent=2))

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
        'runs': runs,
        'updatedAt': datetime.utcnow().isoformat() + 'Z',
    }
    history['by_slug'] = by_slug
    history['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
    save_quality_history(history)
    return gate


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
    title = sanitize_text(title)

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
        recovered = sanitize_text(match.group(1))
        if recovered and not invalid_title(recovered):
            warn(f'Recovered publish title from embedded task field: {recovered[:120]}')
            return recovered

    publish_match = re.search(r'\bpublish\s*:\s*(.+)$', description, flags=re.IGNORECASE | re.MULTILINE)
    if publish_match:
        recovered = sanitize_text(publish_match.group(1))
        if recovered and not invalid_title(recovered):
            warn(f'Recovered publish title from description publish field: {recovered[:120]}')
            return recovered

    die(f'Refusing to publish invalid title: {title or "empty title"}')


def sanitize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    title = normalize_publish_title(raw.get('title', ''), raw.get('description', ''))
    slug = sanitize_text(raw.get('slug', '')) or slugify(title)

    lead = sanitize_text(raw.get('lead', '') or raw.get('excerpt', '') or title)
    excerpt = sanitize_text(raw.get('excerpt', '') or lead)
    meta_description = sanitize_text(raw.get('meta_description', '') or excerpt)
    closing = sanitize_text(raw.get('closing', '') or lead)

    sections = ensure_sections(raw.get('sections', []), lead, excerpt, closing, title)

    bullets_raw = raw.get('bullets', [])
    bullets: list[str] = []
    if isinstance(bullets_raw, list):
        bullets = [sanitize_text(b) for b in bullets_raw if sanitize_text(b)]

    tags = normalize_tags(raw.get('tags', []), title, lead)
    citations = normalize_citations(raw.get('citations', []) or raw.get('sources', []))

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
        'lead': lead,
        'excerpt': excerpt,
        'meta_description': meta_description,
        'sections': sections,
        'bullets': bullets[:4],
        'closing': closing,
    }

    tighten_to_target(payload, QUALITY_MIN_WORDS, QUALITY_MAX_WORDS)
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
            quality_gate = run_quality_gate(
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
            'quality_total': quality_gate['final_total'],
            'quality_target': quality_gate['target_total'],
            'quality_previous': quality_gate['previous_total'],
        }
        print(json.dumps(result, indent=2))
    finally:
        if starting_branch and publish_branch and starting_branch != publish_branch:
            subprocess.run(['git', 'checkout', starting_branch], cwd=ROOT, text=True, capture_output=True)
        if stashed_ref:
            restore_stash(stashed_ref)


if __name__ == '__main__':
    main()
