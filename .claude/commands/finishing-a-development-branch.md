---
name: finishing-a-development-branch
description: Use after completing implementation work - verify tests pass then present options to merge, push, keep, or discard
---

# Finishing a Development Branch

## Overview

Complete development work with a structured, safe workflow.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

```
Tests passing? → No → STOP, fix tests
                ↓ Yes
Detect environment (repo type, worktree)
                ↓
Present menu options
                ↓
Execute user's choice
                ↓
Cleanup
```

## Step 1: Verify Tests Pass

Run your project's test command. Tests MUST pass before offering any options.

**If tests fail:** Stop immediately. Report which tests failed and why. Ask before continuing.

**If tests pass:** Continue to Step 2.

## Step 2: Detect Environment

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

## Step 3: Present Menu Options

1. **Merge back to base branch locally**
2. **Push and create a Pull Request**
3. **Keep the branch as-is for later**
4. **Discard this work** (requires confirmation)

## Red Flags

Never:
- Offer options with failing tests
- Skip environment detection
- Discard without requiring confirmation
- Proceed before test verification
