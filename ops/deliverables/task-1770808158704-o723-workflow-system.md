# Workflow System Plan

Task: task-1770808158704-o723
Generated: 2026-02-12T13:04:41.512Z

## Objective
Capture every ask, execute one task at a time, and keep quality rising without dropping context.

## Current Constraint
[Wed 2026-02-11 14:21 GMT+5:30] Create a serialized SEO blog operating playbook for this task. Return ONLY markdown. No JSON. No process commentary. This is an execution system deliverable, not a single blog post. Assume model concurrency is limited; enforce one-by-one sub-agent execution. Length: 1000-1600 words. Task title: Autonomous SEO blog sprint: LXD operating model for teams with weekly execution rhythm Task description: Increase organic traffic by running one full serialized SEO blog cycle in L&D, gamification, data, LXD, and AI. Start with topic discovery (3 candidates, pick best), then complete keyword/SERP analysis, writing, optimization, publishing, and measurement handoff. Produce publish QA evidence including live URL, sitemap, RSS, and status checks. Persist team_notes so future runs learn from this run and avoid repeated mistakes. Completion summary: Start with Topic Scout: identify 3 candidate topics and select best Recorded next steps: Start with Topic Scout: identify 3 candidate topics and select best Site URL: https://shreyaskorad.github.io/personal-website Repo hint: /Users/shreyas/Documents/New project/.tmp/personal-website-ops Posts path: posts Writing index: writing.html Publish script: scripts/publish_post.py Style rules file: blog-writing-rules.md Primary topic spaces: L&D, gamification, data, LXD, AI Agent roster (must be serialized in this order): 1. Topic Scout - Identify high-upside topics tied to L&D, gamification, data, LXD, and AI. Output: Prioritized topic slate with thesis, audience intent, and ranking opportunity. 2. Keyword and SERP Analyst - Map keyword clusters, search intent, and competitor coverage gaps. Output: Primary keyword, supporting entities, SERP gap notes, and internal-link targets. 3. Brief Architect - Convert strategy into a clear brief and outline with unique angle. Output: Approved brief with section plan, CTA, and evidence requirements. 4. Research Analyst - Gather credible source material and practical examples. Output: Source-backed notes, claims table, and references for each major section. 5. Writer - Draft publishable post aligned with site voice and audience needs. Output: Complete draft post in site format. 6. SEO Optimizer - Optimize metadata, structure, and on-page relevance signals. Output: Title/meta/slug recommendations, heading checks, schema suggestions. 7. Editor - Improve clarity, authority, and readability while preserving intent. Output: Final edited copy with quality notes and resolved issues. 8. Refresh Planner - Define update cadence to protect rankings and freshness. Output: Post-publication refresh plan with triggers and review cadence. 9. Publishing QA - Publish and verify the post is live and correctly indexed. Output: Publish proof with URL, timestamp, and pass/fail checklist. Required format: # <SEO Blog System Title> ## Objective and success metrics ## Serialized agent roster ## Workflow (intake to publish) ## Quality gates and acceptance criteria ## Publishing QA checklist ## Automation cadence and backlog rules ## Failure handling and fallback logic ## Weekly operating rhythm

## System Architecture
1. Intake lane: WhatsApp, dictation, and Codex messages append to inbox.
2. Queue lane: taskflow normalizes to one canonical queue with sequence + priority.
3. Execution lane: exactly one in-progress task (WIP=1).
4. Review lane: task must carry delivery summary before completion.
5. Observability lane: dashboard snapshots + activity logs + failure state.

## Execution Rules
- Auto-advance starts the next queued task only when no review gate exists.
- Execute-active runs handler logic with retries and cooldown.
- After 3 execution failures, task is blocked with explicit reason.
- Completed tasks are timestamped with delivery notes.

## Operator Controls
- Reorder queue: node .tasks/taskflow.js sequence <task-id> <n>
- Raise/lower priority: node .tasks/taskflow.js priority <task-id> <level>
- Force start: node .tasks/taskflow.js start <task-id>
- Inspect state: node .tasks/taskflow.js brief

## Next Step
Keep the intake loop running every 5 minutes and review blocked tasks once per day.
