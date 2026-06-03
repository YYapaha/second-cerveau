---
name: dispatching-parallel-agents
description: Use when you have three or more independent failures in different files or subsystems - dispatch agents to investigate each concurrently
---

# Dispatching Parallel Agents

## Overview

Delegate multiple independent tasks to specialized agents working concurrently rather than sequentially.

**Announce at start:** "I'm using the dispatching-parallel-agents skill to investigate these failures in parallel."

## Core Principle

When failures are independent (different test files, different subsystems, different bugs), assign "one agent per domain" to investigate simultaneously.

```
Multiple unrelated failures
    ↓
Group by domain/subsystem
    ↓
Create focused tasks (one per agent)
    ↓
Dispatch all agents in parallel
    ↓
Review & integrate results
    ↓
Verify no conflicts
```

## When to Use

**Use parallel dispatch when:**
- Three or more test files fail with distinct root causes
- Each problem can be understood independently
- No shared state exists between investigations
- Failures are in different subsystems or domains

**Avoid when:**
- Failures are interconnected (one fix cascades to others)
- Full system understanding is required
- Shared state means agents would interfere with each other
- Only 1-2 independent failures (sequential is simpler)

## The Process

**Step 1: Identify domains**
Group failures by affected subsystem. Each group becomes one task.

**Step 2: Create focused tasks**
Each agent receives:
- Clear scope (exactly which tests/files/subsystem)
- Specific goals (fix race condition in abort logic, fix batch completion, etc.)
- Constraints (don't touch state management, don't refactor)

**Step 3: Dispatch concurrently**
All agents start work in parallel (not sequentially).

**Step 4: Review & integrate**
- Collect all agent results
- Verify fixes don't conflict
- Run full test suite to confirm no regressions

## Red Flags

Never:
- Start parallel dispatch without identifying independent domains
- Dispatch more agents than independent failures
- Assume agents will coordinate without explicit instruction
- Skip the integration verification step
- Use for interconnected or cascading failures
