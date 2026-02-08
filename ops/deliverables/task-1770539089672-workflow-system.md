# Workflow System Plan

Task: task-1770539089672
Generated: 2026-02-08T13:00:54.716Z

## Objective
Capture every ask, execute one task at a time, and keep quality rising without dropping context.

## Current Constraint
DICTATION #61 Summary: I need to figure way out I lineup tasks for the AI systems in a way where no ask is lost and every thought is captured. Raw dictation: I need to figure way out I lineup tasks for the for the AI systems in a way where not ask is lost. Every thought is captured and the sequence of production and shipping that is faster in the quality increases over a period of time.

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
