---
name: systematic-debugging
description: Use when code is broken and you don't know why - investigate root causes before fixing, never apply symptom patches
---

# Systematic Debugging

## Overview

Find root causes before implementing fixes. Enforces a four-phase approach that prevents band-aids and technical debt.

**Announce at start:** "I'm using the systematic-debugging skill to find the root cause."

## Core Mandate

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

## The Four-Phase Approach

### Phase 1: Root Cause Investigation

**Goal:** Find WHAT FIRST went wrong, not where the error manifests.

1. Read error messages completely
2. Reproduce the issue consistently
3. Review recent changes (git log, git diff)
4. Trace data flow through system layers
5. Instrument code with logging

**Stop when:** You can explain what initial condition triggered the problem.

### Phase 2: Pattern Analysis

**Goal:** Confirm the root cause by finding evidence of the pattern.

1. Find working examples (similar code that succeeds)
2. Find broken examples (similar code that fails)
3. Compare implementations side-by-side
4. Identify differences

### Phase 3: Hypothesis Testing

**Goal:** Verify the root cause with targeted, minimal tests.

1. Form a specific theory ("data is null at line X" not "something is wrong")
2. Design minimal test to verify theory
3. Run test, observe result
4. If theory is wrong, go back to Phase 1

### Phase 4: Implementation

**Goal:** Fix the root cause, not the symptom.

1. Create failing test case that proves the bug
2. Apply single fix addressing root cause
3. Verify test passes
4. Run full test suite to check for regressions

## Critical Warning Signs — STOP and use this skill when:

- Time pressure makes "quick fix" tempting
- You've tried 3+ different fixes and nothing worked
- You understand the symptom but not the cause

**The formula:** 3 failed attempts = architectural problem, not implementation bug.

## Red Flags

Never:
- Skip Phase 1 investigation
- Jump straight to "fix" without root cause
- Apply multiple patches simultaneously
- Ignore the "3 failed attempts" reset signal
