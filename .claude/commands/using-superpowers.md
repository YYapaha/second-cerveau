---
name: using-superpowers
description: Use before responding to any request - check if a superpowers skill applies and invoke it
---

# Using Superpowers

## Overview

This skill establishes the protocol for invoking other skills before responding to user requests.

**The rule:** "If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill."

## Skill Invocation Priority

**Upon receiving a request:**

1. **Scan for applicable skills immediately** - Before clarifying, asking questions, or exploring
2. **Invoke skills in order** - Brainstorming/debugging first, then implementation-specific skills
3. **Honor user instructions** - Explicit user directives override skill requirements

## Instruction Hierarchy

1. **User's direct instructions** (highest priority)
2. **Superpowers skills** (override defaults)
3. **System defaults** (lowest priority)

## Red Flag Rationalizations

**Stop and invoke skills when you think:**

- "This is simple, I don't need a skill"
- "Let me gather info first, then check skills"
- "I remember what that skill said"
- "This is different from what the skill covers"

## Skill Types

**Rigid Skills** (require exact adherence):
- TDD, Systematic debugging, Verification before completion, Brainstorming

**Flexible Skills** (adapt principles contextually):
- Code review, Writing plans, Subagent-driven development

## The Bottom Line

Skill invocation is the gating function. If you're not invoking skills, you're not using superpowers.
