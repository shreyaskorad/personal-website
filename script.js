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
        navLinks.querySelectorAll('a').forEach(link => {
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

    const articles = Array.from(document.querySelectorAll('.article-card'));
    const searchInput = document.querySelector('#article-search');
    const filterButtons = Array.from(document.querySelectorAll('.filter-link'));
    const emptyState = document.querySelector('#no-results');
    let activeTag = 'all';

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
        return raw.split(',').map(tag => tag.trim().toLowerCase()).filter(Boolean);
    };

    const applyFilters = () => {
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        let visibleCount = 0;
        
        articles.forEach(article => {
            const tags = getTags(article);
            const matchesTag = activeTag === 'all' || tags.includes(activeTag);
            const title = getArticleText(article, 'title', 'h3');
            const excerpt = getArticleText(article, 'excerpt', 'p');
            const matchesQuery = !query || title.includes(query) || excerpt.includes(query);
            const show = matchesTag && matchesQuery;
            article.hidden = !show;
            if (show) visibleCount++;
        });

        if (emptyState) {
            emptyState.hidden = visibleCount > 0;
        }
    };

    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            activeTag = button.dataset.tag || 'all';
            applyFilters();
        });
    });

    applyFilters();
});

// Subtle scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
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
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
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
