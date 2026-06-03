---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists
---

# Using Git Worktrees

## Overview

Ensure work happens in an isolated workspace. Prefer platform's native worktree tools. Fall back to manual git worktrees only when no native tool is available.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

**If `GIT_DIR != GIT_COMMON` (and not a submodule):** Already in a linked worktree. Skip to Step 3.

**If `GIT_DIR == GIT_COMMON`:** In a normal repo. Ask consent before creating worktree.

## Step 1: Create Isolated Workspace

**1a. Native tools first** — Use `EnterWorktree`, `/worktree`, or `--worktree` flag if available.

**1b. Git fallback** — Only if no native tool:

```bash
# Safety: verify directory is ignored
git check-ignore -q .worktrees 2>/dev/null

# Create worktree
git worktree add ".worktrees/$BRANCH_NAME" -b "$BRANCH_NAME"
cd ".worktrees/$BRANCH_NAME"
```

## Step 3: Project Setup

```bash
if [ -f package.json ]; then npm install; fi
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi
```

## Step 4: Verify Clean Baseline

Run tests. If they fail, report and ask whether to proceed.

## Red Flags

Never:
- Create a worktree when Step 0 detects existing isolation
- Use `git worktree add` when you have a native worktree tool
- Create worktree without verifying it's ignored (project-local)
- Skip baseline test verification
