const normalizeTag = (tag) => {
    if (!tag) {
        return '';
    }

    return tag
        .replace(/\u00a0/g, ' ')
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
    const filterContainer = document.querySelector('.article-filters');
    const emptyState = document.querySelector('#no-results');
    const queryParams = new URLSearchParams(window.location.search);
    let activeTag = normalizeTag(queryParams.get('tag')) || 'all';

    const getArticleText = (article, attr, selector) => {
        const fromData = article.dataset[attr];
        if (fromData) {
            return fromData.toLowerCase();
        }
        const el = article.querySelector(selector);
        return el ? el.textContent.toLowerCase() : '';
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

    const applyFilters = (options = { syncUrl: true }) => {
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        let visibleCount = 0;

        articles.forEach((article) => {
            const tags = getTags(article);
            const matchesTag = activeTag === 'all' || tags.includes(activeTag);
            const title = getArticleText(article, 'title', 'h3');
            const excerpt = getArticleText(article, 'excerpt', 'p');
            const tagText = tags.join(' ');
            const matchesQuery = !query || title.includes(query) || excerpt.includes(query) || tagText.includes(query);
            const show = matchesTag && matchesQuery;
            article.hidden = !show;
            if (show) {
                visibleCount += 1;
            }
        });

        if (emptyState) {
            emptyState.hidden = visibleCount > 0;
            if (!emptyState.hidden) {
                const conditions = [];
                if (activeTag !== 'all') {
                    conditions.push(`tag \"${formatTagLabel(activeTag)}\"`);
                }
                if (query) {
                    conditions.push(`search \"${query}\"`);
                }

                emptyState.textContent = conditions.length
                    ? `No articles found for ${conditions.join(' + ')}.`
                    : 'No articles found.';
            }
        }

        setActiveFilterButton();
        updateTagChipStates();

        if (options.syncUrl) {
            syncUrlState();
        }
    };

    const setActiveTag = (tag, options = { syncUrl: true }) => {
        const nextTag = normalizeTag(tag);
        const candidate = nextTag && (nextTag === 'all' || tagCounts.has(nextTag)) ? nextTag : 'all';
        activeTag = candidate;
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
            setActiveTag(tag);
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
        articles.forEach((article) => {
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
                chip.textContent = formatTagLabel(tag);
                chip.setAttribute('role', 'button');
                chip.setAttribute('tabindex', '0');
                chip.setAttribute('aria-label', `Filter by ${formatTagLabel(tag)}`);
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
        const sorted = [...articles].sort((a, b) => {
            const aDate = a.dataset.date ? new Date(a.dataset.date).getTime() : 0;
            const bDate = b.dataset.date ? new Date(b.dataset.date).getTime() : 0;
            return bDate - aDate;
        });
        sorted.forEach((article) => articleList.appendChild(article));

        articleList.addEventListener('click', (event) => {
            const chip = event.target.closest('.tag-filter');
            if (!chip) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            setActiveTag(chip.dataset.tag || 'all');
        });

        articleList.addEventListener('keydown', (event) => {
            const chip = event.target.closest('.tag-filter');
            if (!chip || (event.key !== 'Enter' && event.key !== ' ')) {
                return;
            }

            event.preventDefault();
            setActiveTag(chip.dataset.tag || 'all');
        });
    }

    const initialQuery = queryParams.get('q');
    if (searchInput && initialQuery) {
        searchInput.value = initialQuery;
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            applyFilters();
        });
    }

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
