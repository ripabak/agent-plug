---
name: implement-issues
description: 'Implement existing issues based on priority and dependencies, while reconciling status with issues-checklist.md and updating both sides.'
---

Implement existing issues in execution order and keep local tracking aligned.

Always require `issues-checklist.md` to compare local progress with current issue status.

Primary workflow:
1. Validate required files exist:
   - `issues-checklist.md` (required)
   - `project-plan.md` (recommended)
   - `implementation-plan.md` and/or `prd.md` (if available)
2. Select issues to implement by:
   - Priority
   - Dependencies
   - Readiness to execute
3. Implement issues one-by-one.
   - Parallel work is allowed only for independent issues.
4. After each issue is implemented:
   - Update `issues-checklist.md` immediately with implementation state and references

If `issues-checklist.md` is missing or does not contain enough detail to proceed, ask the user for clarification first.
