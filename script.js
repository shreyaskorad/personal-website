const normalizeTag = (tag) => {
    if (!tag) {
        return '';
    }

    return tag
        .replace(/&amp;/gi, '&')
        .replace(/\u00a0/g, ' ')
        .replace(/[_/]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
};

const formatTagLabel = (tag) => {
    const normalized = normalizeTag(tag);
    if (!normalized) {
        return '';
    }

    const acronyms = new Map([
        ['ai', 'AI'],
        ['lxd', 'LxD'],
        ['l&d', 'L&D'],
        ['ld', 'L&D'],
        ['ux', 'UX'],
        ['ui', 'UI'],
        ['seo', 'SEO']
    ]);

    if (acronyms.has(normalized)) {
        return acronyms.get(normalized);
    }

    return normalized
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
};

const normalizeSearchText = (text) => {
    if (!text) {
        return '';
    }

    return String(text)
        .toLowerCase()
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9&+\s-]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
};

const tokenizeSearchQuery = (query) => {
    const normalized = normalizeSearchText(query);
    if (!normalized) {
        return [];
    }
    const tokens = normalized.split(' ').filter((token) => token.length > 1);
    return Array.from(new Set(tokens));
};

const escapeHtml = (value) => String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const highlightText = (rawText, rawTerms) => {
    const text = String(rawText || '');
    const terms = Array.from(new Set((rawTerms || []).map((t) => t.trim()).filter((t) => t.length > 1)));
    if (!terms.length) {
        return escapeHtml(text);
    }

    const pattern = new RegExp(`(${terms.map((term) => escapeRegExp(term)).join('|')})`, 'ig');
    const parts = text.split(pattern);
    return parts.map((part) => {
        const lower = part.toLowerCase();
        const isMatch = terms.some((term) => lower === term.toLowerCase());
        const escaped = escapeHtml(part);
        return isMatch ? `<mark class="search-hit">${escaped}</mark>` : escaped;
    }).join('');
};

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            navToggle.classList.toggle('active');
        });

        // Close menu when clicking a link
        navLinks.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
                navLinks.classList.remove('active');
                navToggle.classList.remove('active');
            }
        });
    }
});

// Writing page interactions
document.addEventListener('DOMContentLoaded', () => {
    const writingPage = document.querySelector('.writing-page');
    if (!writingPage) {
        return;
    }

    const articleList = document.querySelector('#article-list');
    const articles = Array.from(document.querySelectorAll('.article-card'));
    const searchInput = document.querySelector('#article-search');
    const searchClear = document.querySelector('#article-search-clear');
    const searchStatus = document.querySelector('#search-status');
    const activeControls = document.querySelector('#active-controls');
    const activeTagChip = document.querySelector('#active-tag-chip');
    const activeQueryChip = document.querySelector('#active-query-chip');
    const clearFiltersButton = document.querySelector('#clear-filters');
    const rssCopyButton = document.querySelector('#rss-copy');
    const filterContainer = document.querySelector('.article-filters');
    const emptyState = document.querySelector('#no-results');
    const queryParams = new URLSearchParams(window.location.search);
    let activeTag = normalizeTag(queryParams.get('tag')) || 'all';
    const articleIndex = new Map();
    const byDateDesc = (a, b) => {
        const aDate = a.dataset.date ? new Date(a.dataset.date).getTime() : 0;
        const bDate = b.dataset.date ? new Date(b.dataset.date).getTime() : 0;
        return bDate - aDate;
    };
    const orderedByDate = [...articles].sort(byDateDesc);

    const getArticleText = (article, attr, selector) => {
        const fromData = article.dataset[attr];
        if (fromData) {
            return fromData;
        }
        const el = article.querySelector(selector);
        return el ? (el.textContent || '') : '';
    };

    const getTags = (article) => {
        const raw = article.dataset.tags || '';
        const tags = raw
            .split(',')
            .map((tag) => normalizeTag(tag))
            .filter(Boolean);
        return Array.from(new Set(tags));
    };

    const buildTagCounts = () => {
        const counts = new Map();

        articles.forEach((article) => {
            getTags(article).forEach((tag) => {
                counts.set(tag, (counts.get(tag) || 0) + 1);
            });
        });

        return counts;
    };

    const tagCounts = buildTagCounts();

    if (activeTag !== 'all' && !tagCounts.has(activeTag)) {
        activeTag = 'all';
    }

    const sortedTags = Array.from(tagCounts.entries())
        .sort((a, b) => {
            if (b[1] !== a[1]) {
                return b[1] - a[1];
            }
            return a[0].localeCompare(b[0]);
        })
        .map(([tag]) => tag);

    const buildArticleIndex = () => {
        orderedByDate.forEach((article) => {
            const titleRaw = getArticleText(article, 'title', 'h3').trim();
            const excerptRaw = getArticleText(article, 'excerpt', '.article-body p').trim();
            const tags = getTags(article);
            articleIndex.set(article, {
                titleRaw,
                excerptRaw,
                titleNorm: normalizeSearchText(titleRaw),
                excerptNorm: normalizeSearchText(excerptRaw),
                tags,
                tagNorm: normalizeSearchText(tags.join(' '))
            });
        });
    };
    buildArticleIndex();

    const syncUrlState = () => {
        const url = new URL(window.location.href);
        const query = searchInput ? searchInput.value.trim() : '';

        if (activeTag && activeTag !== 'all') {
            url.searchParams.set('tag', activeTag);
        } else {
            url.searchParams.delete('tag');
        }

        if (query) {
            url.searchParams.set('q', query);
        } else {
            url.searchParams.delete('q');
        }

        const nextUrl = `${url.pathname}${url.search}${url.hash}`;
        window.history.replaceState({}, '', nextUrl);
    };

    const updateTagChipStates = () => {
        document.querySelectorAll('.article-tags .tag-filter').forEach((chip) => {
            chip.classList.toggle('active', normalizeTag(chip.dataset.tag) === activeTag);
        });
    };

    const setActiveFilterButton = () => {
        document.querySelectorAll('.filter-link').forEach((button) => {
            const isActive = normalizeTag(button.dataset.tag) === activeTag;
            button.classList.toggle('active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    };

    const updateSearchStatus = (visibleCount, query, activeSearchTag) => {
        if (!searchStatus) {
            return;
        }

        const hasQuery = Boolean(query);
        const hasTag = activeSearchTag !== 'all';
        if (!hasQuery && !hasTag) {
            searchStatus.textContent = '';
            return;
        }

        const parts = [];
        if (hasTag) {
            parts.push(`tag: ${formatTagLabel(activeSearchTag)}`);
        }
        if (hasQuery) {
            parts.push(`query: "${query}"`);
        }

        const suffix = visibleCount === 1 ? 'result' : 'results';
        searchStatus.textContent = `${visibleCount} ${suffix} (${parts.join(' · ')})`;
    };

    const updateActiveControls = (query, activeSearchTag) => {
        if (!activeControls || !activeTagChip || !activeQueryChip || !clearFiltersButton) {
            return;
        }

        const hasTag = activeSearchTag !== 'all';
        const hasQuery = Boolean(query);

        if (hasTag) {
            activeTagChip.hidden = false;
            activeTagChip.textContent = `Tag: ${formatTagLabel(activeSearchTag)}`;
        } else {
            activeTagChip.hidden = true;
            activeTagChip.textContent = '';
        }

        if (hasQuery) {
            activeQueryChip.hidden = false;
            activeQueryChip.textContent = `Query: ${query}`;
        } else {
            activeQueryChip.hidden = true;
            activeQueryChip.textContent = '';
        }

        activeControls.hidden = !(hasTag || hasQuery);
    };

    const updateSearchHighlights = (queryTerms) => {
        orderedByDate.forEach((article) => {
            const index = articleIndex.get(article);
            if (!index) {
                return;
            }

            const titleEl = article.querySelector('h3');
            if (titleEl) {
                titleEl.innerHTML = highlightText(index.titleRaw, queryTerms);
            }

            const excerptEl = article.querySelector('.article-body p');
            if (excerptEl) {
                excerptEl.innerHTML = highlightText(index.excerptRaw, queryTerms);
            }

            article.querySelectorAll('.article-tags .tag-filter').forEach((chip) => {
                const label = chip.dataset.label || chip.textContent || '';
                chip.innerHTML = highlightText(label, queryTerms);
            });
        });
    };

    const rankArticleForQuery = (index, queryNormalized, queryTokens) => {
        if (!queryNormalized) {
            return { matches: true, score: 0 };
        }

        const tokens = queryTokens.length ? queryTokens : [queryNormalized];
        let score = 0;

        for (const token of tokens) {
            let tokenMatched = false;

            if (index.titleNorm.includes(token)) {
                tokenMatched = true;
                score += 14;
                if (index.titleNorm.startsWith(token)) {
                    score += 4;
                }
            }
            if (index.excerptNorm.includes(token)) {
                tokenMatched = true;
                score += 7;
            }
            if (index.tagNorm.includes(token)) {
                tokenMatched = true;
                score += 5;
            }

            if (!tokenMatched) {
                return { matches: false, score: 0 };
            }
        }

        if (tokens.length > 1) {
            if (index.titleNorm.includes(queryNormalized)) {
                score += 8;
            } else if (index.excerptNorm.includes(queryNormalized) || index.tagNorm.includes(queryNormalized)) {
                score += 4;
            }
        }

        return { matches: true, score };
    };

    const applyFilters = (options = { syncUrl: true }) => {
        const query = searchInput ? searchInput.value.trim() : '';
        const queryNormalized = normalizeSearchText(query);
        const queryTokens = tokenizeSearchQuery(query);
        const highlightTerms = queryTokens.length ? queryTokens : (queryNormalized ? [queryNormalized] : []);
        let visibleCount = 0;
        const visibleMatches = [];
        const visibleSet = new Set();

        orderedByDate.forEach((article) => {
            const index = articleIndex.get(article);
            if (!index) {
                return;
            }
            const tags = index.tags;
            const matchesTag = activeTag === 'all' || tags.includes(activeTag);
            const ranked = rankArticleForQuery(index, queryNormalized, queryTokens);
            const matchesQuery = ranked.matches;
            const show = matchesTag && matchesQuery;
            article.hidden = !show;
            if (show) {
                visibleCount += 1;
                visibleSet.add(article);
                visibleMatches.push({ article, score: ranked.score });
            }
        });

        if (articleList) {
            if (queryNormalized) {
                const orderedVisible = visibleMatches
                    .sort((a, b) => b.score - a.score || byDateDesc(a.article, b.article))
                    .map((item) => item.article);
                const hiddenByDate = orderedByDate.filter((article) => !visibleSet.has(article));
                [...orderedVisible, ...hiddenByDate].forEach((article) => articleList.appendChild(article));
            } else {
                orderedByDate.forEach((article) => articleList.appendChild(article));
            }
        }

        if (emptyState) {
            emptyState.hidden = visibleCount > 0;
            if (!emptyState.hidden) {
                const conditions = [];
                if (activeTag !== 'all') {
                    conditions.push(`tag \"${formatTagLabel(activeTag)}\"`);
                }
                if (queryNormalized) {
                    conditions.push(`search \"${query}\"`);
                }

                emptyState.textContent = conditions.length
                    ? `No articles found for ${conditions.join(' + ')}.`
                    : 'No articles found.';
            }
        }

        updateSearchHighlights(highlightTerms);
        updateSearchStatus(visibleCount, query, activeTag);
        updateActiveControls(query, activeTag);

        if (searchClear && searchInput) {
            searchClear.hidden = searchInput.value.trim().length === 0;
        }

        setActiveFilterButton();
        updateTagChipStates();

        if (options.syncUrl) {
            syncUrlState();
        }
    };

    const setActiveTag = (tag, options = { syncUrl: true, clearQuery: false }) => {
        const nextTag = normalizeTag(tag);
        const candidate = nextTag && (nextTag === 'all' || tagCounts.has(nextTag)) ? nextTag : 'all';
        if (options.clearQuery && searchInput && searchInput.value.trim()) {
            searchInput.value = '';
        }
        activeTag = candidate;
        renderFilterButtons();
        applyFilters(options);
    };

    const createFilterButton = (tag, count, isAll = false) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'filter-link';
        button.dataset.tag = tag;
        button.setAttribute('aria-pressed', 'false');

        const label = document.createElement('span');
        label.className = 'filter-label';
        label.textContent = isAll ? 'All' : formatTagLabel(tag);

        const countBubble = document.createElement('span');
        countBubble.className = 'filter-count';
        countBubble.textContent = String(count);

        button.append(label, countBubble);
        button.addEventListener('click', () => {
            setActiveTag(tag, { syncUrl: true, clearQuery: true });
        });

        return button;
    };

    const renderFilterButtons = () => {
        if (!filterContainer) {
            return;
        }

        filterContainer.innerHTML = '';

        const maxVisibleTags = 12;
        const visibleTags = sortedTags.slice(0, maxVisibleTags);
        if (activeTag !== 'all' && !visibleTags.includes(activeTag)) {
            visibleTags.unshift(activeTag);
        }

        filterContainer.appendChild(createFilterButton('all', articles.length, true));
        visibleTags.forEach((tag) => {
            filterContainer.appendChild(createFilterButton(tag, tagCounts.get(tag) || 0));
        });
    };

    const renderTags = () => {
        orderedByDate.forEach((article) => {
            const tags = getTags(article);
            if (!tags.length) {
                return;
            }

            const body = article.querySelector('.article-body') || article;
            const existing = body.querySelector('.article-tags');
            if (existing) {
                existing.remove();
            }

            const tagContainer = document.createElement('div');
            tagContainer.className = 'article-tags';

            tags.forEach((tag) => {
                const chip = document.createElement('span');
                chip.className = 'tag tag-filter';
                chip.dataset.tag = tag;
                chip.dataset.label = formatTagLabel(tag);
                chip.textContent = chip.dataset.label;
                chip.setAttribute('role', 'button');
                chip.setAttribute('tabindex', '0');
                chip.setAttribute('aria-label', `Filter by ${formatTagLabel(tag)}`);
                const activateChip = (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setActiveTag(tag, { syncUrl: true, clearQuery: true });
                };
                chip.addEventListener('click', activateChip);
                chip.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        activateChip(event);
                    }
                });
                tagContainer.appendChild(chip);
            });

            const title = body.querySelector('h3');
            if (title) {
                title.insertAdjacentElement('afterend', tagContainer);
            } else {
                body.appendChild(tagContainer);
            }
        });
    };

    if (articleList) {
        orderedByDate.forEach((article) => articleList.appendChild(article));

        articleList.addEventListener('click', (event) => {
            const chip = event.target.closest('.tag-filter');
            if (!chip) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            setActiveTag(chip.dataset.tag || 'all', { syncUrl: true, clearQuery: true });
        });

        articleList.addEventListener('keydown', (event) => {
            const chip = event.target.closest('.tag-filter');
            if (!chip || (event.key !== 'Enter' && event.key !== ' ')) {
                return;
            }

            event.preventDefault();
            setActiveTag(chip.dataset.tag || 'all', { syncUrl: true, clearQuery: true });
        });
    }

    const initialQuery = queryParams.get('q');
    if (searchInput && initialQuery) {
        searchInput.value = initialQuery;
    }

    if (searchInput) {
        let searchDebounce;
        searchInput.addEventListener('input', () => {
            window.clearTimeout(searchDebounce);
            searchDebounce = window.setTimeout(() => {
                applyFilters();
            }, 90);
        });

        searchInput.addEventListener('keydown', (event) => {
            if (event.key !== 'Escape') {
                return;
            }
            if (!searchInput.value.trim()) {
                return;
            }
            event.preventDefault();
            searchInput.value = '';
            applyFilters();
        });
    }

    if (searchClear && searchInput) {
        searchClear.hidden = !searchInput.value.trim();
        searchClear.addEventListener('click', () => {
            searchInput.value = '';
            applyFilters();
            searchInput.focus();
        });
    }

    if (clearFiltersButton) {
        clearFiltersButton.addEventListener('click', () => {
            if (searchInput) {
                searchInput.value = '';
            }
            setActiveTag('all');
            if (searchInput) {
                searchInput.focus();
            }
        });
    }

    if (rssCopyButton) {
        rssCopyButton.addEventListener('click', async () => {
            const rssUrl = new URL('rss.xml', window.location.href).toString();
            const originalText = rssCopyButton.textContent || 'Copy RSS';
            const copyViaTextarea = () => {
                const temp = document.createElement('textarea');
                temp.value = rssUrl;
                temp.setAttribute('readonly', '');
                temp.style.position = 'fixed';
                temp.style.opacity = '0';
                document.body.appendChild(temp);
                temp.focus();
                temp.select();
                let ok = false;
                try {
                    ok = document.execCommand('copy');
                } catch (err) {
                    ok = false;
                }
                document.body.removeChild(temp);
                return ok;
            };

            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(rssUrl);
                    rssCopyButton.textContent = 'Copied';
                } else if (copyViaTextarea()) {
                    rssCopyButton.textContent = 'Copied';
                } else {
                    rssCopyButton.textContent = 'Copy failed';
                }
            } catch (err) {
                rssCopyButton.textContent = copyViaTextarea() ? 'Copied' : 'Copy failed';
            }
            window.setTimeout(() => {
                rssCopyButton.textContent = originalText;
            }, 1400);
        });
    }

    document.addEventListener('keydown', (event) => {
        if (!searchInput) {
            return;
        }
        if (event.key !== '/') {
            return;
        }
        const target = event.target;
        const isTypingContext = target instanceof HTMLElement
            && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
        if (isTypingContext) {
            return;
        }
        event.preventDefault();
        searchInput.focus();
        searchInput.select();
    });

    renderTags();
    renderFilterButtons();
    setActiveTag(activeTag, { syncUrl: false });
});

// Convert post tags into links back to filtered writing page
document.addEventListener('DOMContentLoaded', () => {
    const postMeta = document.querySelector('.post .post-meta');
    if (!postMeta) {
        return;
    }

    const parts = (postMeta.textContent || '')
        .split('·')
        .map((part) => part.trim())
        .filter(Boolean);

    if (parts.length < 3) {
        return;
    }

    const datePart = parts[0];
    const readTimePart = parts[1];
    const rawTagPart = parts.slice(2).join(' · ');
    const tags = rawTagPart
        .split(',')
        .map((tag) => normalizeTag(tag))
        .filter(Boolean);

    if (!tags.length) {
        return;
    }

    postMeta.innerHTML = '';

    const appendText = (text) => {
        postMeta.appendChild(document.createTextNode(text));
    };

    appendText(datePart);
    appendText(' · ');
    appendText(readTimePart);
    appendText(' · ');

    tags.forEach((tag, index) => {
        if (index > 0) {
            appendText(', ');
        }

        const link = document.createElement('a');
        link.className = 'post-tag-link';
        link.href = `../writing.html?tag=${encodeURIComponent(tag)}`;
        link.textContent = formatTagLabel(tag);
        link.setAttribute('aria-label', `View posts tagged ${formatTagLabel(tag)}`);
        postMeta.appendChild(link);
    });
});

// Subtle scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Apply to animatable elements after DOM loads
document.addEventListener('DOMContentLoaded', () => {
    const animatables = document.querySelectorAll(
        '.value-card, .service-item, .diagram-item, .case-study, .article-card, .fade-up, .philosophy-card, .approach-step, .project-type'
    );

    animatables.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(16px)';
        el.style.transition = `opacity 0.5s ease ${index * 0.05}s, transform 0.5s ease ${index * 0.05}s`;
        observer.observe(el);
    });
});

// Add visible state
document.head.insertAdjacentHTML('beforeend', `
    <style>
        .visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    </style>
`);

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Analytics events + consent banner
document.addEventListener('DOMContentLoaded', () => {
    const trackEvent = (name, params = {}) => {
        if (typeof window.gtag !== 'function') {
            return;
        }
        window.gtag('event', name, params);
    };

    const trackLinkClick = (selector, eventName, getParams) => {
        document.querySelectorAll(selector).forEach((link) => {
            link.addEventListener('click', () => {
                const params = typeof getParams === 'function' ? getParams(link) : {};
                trackEvent(eventName, params);
            });
        });
    };

    trackLinkClick('.btn', 'cta_click', (link) => ({
        label: (link.textContent || '').trim(),
        href: link.getAttribute('href') || ''
    }));

    trackLinkClick('.article-card', 'article_click', (link) => ({
        title: link.dataset.title || (link.querySelector('h3')?.textContent || '').trim(),
        href: link.getAttribute('href') || ''
    }));

    trackLinkClick('a[href^="mailto:"]', 'contact_mailto', (link) => ({
        label: (link.textContent || '').trim(),
        href: link.getAttribute('href') || ''
    }));

    trackLinkClick('a[href*="linkedin.com"]', 'outbound_link', (link) => ({
        label: (link.textContent || '').trim(),
        href: link.getAttribute('href') || ''
    }));

    const contactForm = document.querySelector('#contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', () => {
            trackEvent('generate_lead', { source: 'contact_form' });
        });
    }

    const consentKey = 'sk_consent_accepted';
    if (!localStorage.getItem(consentKey)) {
        const banner = document.createElement('div');
        banner.className = 'consent-banner';
        banner.innerHTML = `
            <div class="consent-content">
                <p>We use analytics to understand site usage. No cookies are stored.</p>
                <button class="consent-accept" type="button">Okay</button>
            </div>
        `;
        document.body.appendChild(banner);

        const acceptButton = banner.querySelector('.consent-accept');
        if (acceptButton) {
            acceptButton.addEventListener('click', () => {
                localStorage.setItem(consentKey, 'true');
                banner.remove();
            });
        }
    }
});
