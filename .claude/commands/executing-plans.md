---
name: executing-plans
description: Use when implementing a written plan - follow task steps sequentially with verification checkpoints and blockers
---

# Executing Plans

## Overview

This skill guides implementation of written plans with structured review checkpoints.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

**Phase 1: Load & Review**
1. Read the entire plan critically
2. Raise concerns BEFORE starting (see Critical Stopping Points below)
3. Create TodoWrite list from the plan's tasks

**Phase 2: Execute**
For each task in order:
1. Mark task "in progress" in TodoWrite
2. Follow task steps precisely
3. Run any specified verifications
4. Mark task "done" after verification passes

**Phase 3: Complete**
After all tasks pass:
1. Use finishing-a-development-branch skill to verify and present options

## Critical Stopping Points

**Stop immediately and ask for clarification when:**
- Blockers like missing dependencies or test failures
- Unclear instructions or plan gaps
- Repeated verification failures (same step fails 2+ times)

"Don't force through blockers" — ask instead of guessing.

## Important Constraints

- Never start on main/master branches without explicit consent
- Always use git-worktrees for isolated workspaces
- If subagent support is available, use subagent-driven-development instead (higher quality)

## Red Flags

Never:
- Proceed past blockers without asking
- Skip plan verification steps
- Start on production branches without explicit consent
- Modify task steps without user approval
- Continue if same step fails multiple times
