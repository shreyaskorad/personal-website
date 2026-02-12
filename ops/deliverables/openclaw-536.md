# Deliverable: Design learning prompts that improve decisions during real project pressure

- Task ID: openclaw-536
- Status: completed
- Created: 2026-02-12T08:37:47Z
- Updated: 2026-02-12T08:38:22Z

## Summary
No summary provided.

## Deliverable Output
_Last OpenClaw deliverable attempt failed; automatic retry is queued._ (last attempt: 2026-02-12T08:39:47Z)

## Last Error
OpenClaw returned no usable markdown deliverable.

## Draft Deliverable (Fallback)
# Deliverable Draft: Design Learning Prompts That Improve Decisions During Real Project Pressure SEO blog operating system

## Objective and success metrics
Build a predictable SEO content system for Shreyas Korad - Writing (https://shreyaskorad.github.io/personal-website) focused on L&D, gamification, data, LXD, AI. Primary metrics: ranking growth, qualified traffic, and publish cadence reliability.

## Serialized agent roster
1. Topic Scout - Identify high-upside topics tied to L&D, gamification, data, LXD, and AI.
2. Keyword and SERP Analyst - Map keyword clusters, search intent, and competitor coverage gaps.
3. Brief Architect - Convert strategy into a clear brief and outline with unique angle.
4. Research Analyst - Gather credible source material and practical examples.
5. Writer - Draft publishable post aligned with site voice and audience needs.
6. Reader intent optimizer - Keep title, framing, and examples aligned to practical reader intent.
7. Editor - Improve clarity, authority, and readability while preserving intent.
8. Refresh Planner - Define update cadence to protect rankings and freshness.
9. Publishing QA - Publish and verify the post is live and correctly indexed.

## Workflow (intake to publish)
1. Topic Scout identifies opportunities and ranks by business relevance.
2. Keyword and SERP Analyst builds intent map and competitor gaps.
3. Brief Architect converts strategy into outline and argument arc.
4. Research Analyst gathers verified source notes and claims.
5. Writer drafts publishable post in site format.
6. SEO Optimizer improves title/meta/headings/internal links/schema.
7. Editor finalizes voice, clarity, and readability.
8. Refresh Planner defines update and republish triggers.
9. Publishing QA uploads and validates end-to-end publish health.

## Quality gates and acceptance criteria
- Gate 1: topic and keyword fit for target audience intent.
- Gate 2: evidence-backed draft with no fabricated claims.
- Gate 3: on-page SEO checks pass before publish.
- Gate 4: publishing QA confirms live URL and indexability.

## Publishing QA checklist
- Create/update post under `posts` and verify listing in `writing.html`.
- Validate slug, canonical, meta title/description, and schema fields.
- Verify HTTP 200 on final URL and correct render on desktop/mobile.
- Confirm sitemap and RSS include the new post after publish.
- Use `scripts/publish_post.py` when available for deterministic publishing.

## Failure handling and fallback logic
- If publish fails, do not mark task complete; create fix task with blocker evidence.
- If SERP APIs/sources fail, retry sequentially with alternatives and direct sources.
- Keep execution serialized to avoid free-tier concurrency/rate-limit failures.

## Notes
Write one publish-ready article in your authentic focus areas: L&D, gamification, LXD, data-informed learning, and practical AI use in learning. Exclude SEO/process meta content. Avoid duplicated themes and avoid previously published near-duplicate titles. Keep it practical: decision quality, evidence linked to business metrics, and real implementation examples. Follow strict style rules: 150-200 words, no bullets, no em dash, no blockquotes. Do not use precise numeric claims unless cited with a verifiable source link. Avoid repeating the same core point across paragraphs; maintain natural narrative flow.

## Next Step
Choose: `proceed` (give direction) or `close` (finalize).
