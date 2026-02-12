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
LOCK_FILE = ROOT / '.publish.lock'
HISTORY_FILE = Path('/Users/shreyas-clawd/.openclaw/state/publish-image-history.json')
SANITIZED_PAYLOAD = ROOT / '.publish-payload.sanitized.json'

RECENT_IMAGE_WINDOW = 12

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
                sections.append({'heading': heading, 'paragraphs': paragraphs[:3]})

    if len(sections) >= 2:
        return sections

    body_a = excerpt or lead or f'{title} is changing how we work and decide.'
    body_b = closing or 'The shift is practical: tools are faster, but judgment and direction still matter most.'
    warn('Payload sections were incomplete; generated fallback sections')
    return [
        {'heading': '', 'paragraphs': [sanitize_text(body_a)]},
        {'heading': '', 'paragraphs': [sanitize_text(body_b)]},
    ]


def normalize_tags(raw_tags: Any, title: str, lead: str) -> list[str]:
    tags: list[str] = []
    if isinstance(raw_tags, list):
        tags = [sanitize_text(t).lower().replace(' ', '-') for t in raw_tags if sanitize_text(t)]
    if not tags:
        tags = [t for t in list(core_keywords(f'{title} {lead}'))[:3]]
    if not tags:
        tags = ['writing', 'insights']
    return tags[:3]


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


def tighten_to_target(payload: dict[str, Any], min_words: int = 150, max_words: int = 200) -> None:
    def current() -> int:
        return word_count(collect_text_for_count(payload))

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

    while current() < min_words:
        payload['closing'] = (
            f"{payload.get('closing','').strip()} The real advantage comes from pairing clearer intent with faster execution."
        ).strip()
        if current() >= min_words:
            break


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


def sanitize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    title = sanitize_text(raw.get('title', '')) or 'Untitled note'
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
        'lead': lead,
        'excerpt': excerpt,
        'meta_description': meta_description,
        'sections': sections,
        'bullets': bullets[:4],
        'closing': closing,
    }

    tighten_to_target(payload)
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


def prepare_publish_branch() -> str:
    # Always publish from a clean branch rooted at latest origin/main.
    branch = f"publish/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    run(['git', 'fetch', 'origin', 'main'])
    run(['git', 'checkout', '-B', branch, 'origin/main'])
    return branch


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
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        die(f'Input file not found: {input_path}', 2)

    lock_handle = LOCK_FILE.open('w')
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        die('Another publish operation is in progress', 75)

    publish_branch = prepare_publish_branch()

    raw = json.loads(input_path.read_text())
    payload = sanitize_payload(raw)
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
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
