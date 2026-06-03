---
name: test-driven-development
description: Use when implementing any feature or bugfix - write failing test first, then minimal code, then refactor
---

# Test-Driven Development

## Overview

TDD improves code quality by inverting the traditional order: tests come first, implementation second.

**Announce at start:** "I'm using the test-driven-development skill to implement this feature."

## Core Principle (Non-Negotiable)

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

If you write code before watching a test fail, delete it and start over.

## The Three-Phase Cycle

### Phase 1: RED

1. Write a test that describes what the code should do
2. Run the test
3. Confirm it FAILS
4. Confirm it fails for the RIGHT reason

**Stop when:** Test is failing for exactly the reason you expect.

### Phase 2: GREEN

1. Write minimal implementation to pass the test
2. Run the test
3. Confirm it PASSES
4. Don't add features beyond what the test requires

**Avoid:**
- Over-engineering
- Adding features "while you're at it"
- Future-proofing

### Phase 3: REFACTOR

1. Identify code that could be cleaner
2. Refactor (rename variables, extract functions, simplify logic)
3. Run all tests after each change
4. If a test breaks, revert the refactor

## The Iron Law

```
Write test → Watch it fail → Write code → Watch it pass → Refactor → Repeat
```

Skip any step = start over.

## Verification Checklist

- [ ] Every new function has a corresponding test
- [ ] Each test failed initially for expected reasons
- [ ] Minimal code was written per test
- [ ] All tests pass with clean output
- [ ] Code is clean (refactored after tests pass)

## Red Flags

Never:
- Write code before test
- Write tests after implementation
- Skip the "watch test fail" step
- Write multiple tests before seeing any fail
