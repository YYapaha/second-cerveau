---
name: brainstorming
description: Use when transforming creative ideas into detailed designs before implementation work - ensures design review and approval before any implementation starts
---

# Brainstorming: Turning Ideas Into Designs

## Overview

This skill enforces a critical gate: **no implementation work proceeds until a design receives user approval.**

"This applies to EVERY project regardless of perceived simplicity."

**Announce at start:** "I'm using the brainstorming skill to develop this design."

## The Process

1. **Explore project context** - Read existing architecture, codebase, and any prior related work
2. **Offer visual companion** - If the design has visual elements, offer to show mockups in the browser
3. **Ask clarifying questions one at a time** - Never batch them. Multiple-choice options preferred when feasible
4. **Propose 2-3 alternative approaches** - Show trade-offs. Recommend a direction. Get user feedback
5. **Present design sections for approval** - Break the full design into reviewable pieces. Get approval before continuing
6. **Write design documentation** - Create detailed spec that covers scope, architecture, data model, APIs, and open questions
7. **Self-review the spec** - Check for placeholders, contradictions, and missing pieces
8. **Get user review of written spec** - Ask the user to review the complete written specification
9. **Transition to implementation** - After approval, shift to implementation planning (writing-plans skill) or direct implementation

## When to Use

- Responding to feature requests
- Starting new projects
- Making architectural decisions
- Building anything complex enough to benefit from planning

## When NOT to Use

- During live debugging when the problem is already well-understood
- Clarifying questions where users have already decided

## Key Guidelines

**Don't rush approval** - Incomplete designs lead to rework. Get explicit approval before proceeding.

**Decompose complex projects** - Projects spanning multiple independent subsystems should break into smaller sub-projects, each addressed separately.

**Write the spec** - Save all approved designs to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit to version control.

**Visible conversation** - Ask questions in the terminal. Show multiple-choice options. Get feedback before assuming you understand.

## Common Mistakes

- Skipping the approval step and starting implementation immediately
- Asking too many questions at once (ask one, wait for response, then next)
- Proposing only one design direction ("here's what I think")
- Not saving the approved design to a file

## Red Flags

Never:
- Start implementation before design approval
- Assume "this is simple" means skip design
- Batch clarifying questions
- Offer only one approach without alternatives
