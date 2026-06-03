---
name: requesting-code-review
description: Use after completing tasks in subagent-driven-development, before merging to main, or when development feels stuck - dispatch code reviewer
---

# Requesting Code Review

## Overview

Request code reviews at key checkpoints using a specialized reviewer subagent.

**Announce at start:** "I'm using the requesting-code-review skill to get a review of this work."

## When to Request Review

**Mandatory:**
- After each task in subagent-driven-development
- Before merging to main
- After completing major features

**Optional but recommended:**
- When development feels stuck
- Before refactoring work
- Following complex bug fixes

## The Process

**Step 1: Get commit hashes**
```bash
git log --oneline -<N>
```

**Step 2: Dispatch the reviewer**
Provide:
- Brief description of what you built
- The plan or requirements it addresses
- Starting commit SHA (before your work)
- Ending commit SHA (current HEAD)

**Step 3: Receive feedback**
The reviewer returns:
- Strengths: what went well
- Issues: categorized as Critical, Important, Minor
- Assessment: merge readiness

**Step 4: Process feedback**
Use the receiving-code-review skill to respond appropriately.

## Issue Severity Levels

**Critical Issues** - Fix immediately, merge blocked
**Important Issues** - Must resolve before merging
**Minor Issues** - Document for future, doesn't block merge

## Red Flags

Never:
- Merge without review
- Skip reviews for seemingly trivial changes
- Proceed past unfixed critical/important issues
- Request review on incomplete work
