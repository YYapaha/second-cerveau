---
name: subagent-driven-development
description: Use when executing implementation plans with multiple independent tasks in current session - dispatch fresh subagent per task with spec compliance then code quality review
---

# Subagent-Driven Development

## Overview

Execute implementation plans through specialized subagent delegation within a single session.

**Announce at start:** "I'm using the subagent-driven-development skill to execute this plan."

## Core Methodology

```
Load plan with full context
    ↓
Per task:
  ├─ Dispatch implementer subagent
  ├─ Spec compliance review (verify against requirements)
  ├─ Code quality review (verify clean implementation)
  └─ Handle implementer status
    ├─ DONE ✅ → next task
    ├─ DONE_WITH_CONCERNS ⚠️ → address concerns → next task
    ├─ NEEDS_CONTEXT 🤔 → gather context → re-dispatch
    └─ BLOCKED 🚫 → escalate → don't retry with same params
    ↓
Dispatch final code reviewer for entire implementation
    ↓
Complete
```

## Critical Principles

**Continuous execution** - Do not pause between tasks. Execute all tasks without stopping.

**Two-stage review order** - Spec compliance review BEFORE code quality review. Never reverse.

**Never ignore escalations** - BLOCKED means something requires change. Don't retry identically.

**Fresh subagent per task** - Each task gets a dedicated subagent with just its task instructions.

## Per-Task Workflow

```
1. Dispatch implementer
2. Dispatch spec compliance reviewer
3. If issues found → implementer fixes → re-review
4. When spec passes: dispatch code quality reviewer
5. If issues found → implementer fixes → re-review
6. When both pass → move to next task
```

## Status Indicators

- **DONE** ✅ - Move to next task
- **DONE_WITH_CONCERNS** ⚠️ - Address concerns then next task
- **NEEDS_CONTEXT** 🤔 - Gather context, re-dispatch with clarification
- **BLOCKED** 🚫 - Escalate to human, don't retry with same params

## Red Flags

Never:
- Start on production branches without consent
- Skip either review stage
- Dispatch multiple implementers in parallel (defeats the review cycle)
- Reverse the review order (code quality before spec compliance)
- Retry BLOCKED tasks with identical parameters
