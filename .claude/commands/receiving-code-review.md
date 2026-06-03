---
name: receiving-code-review
description: Use when processing code review feedback - verify technical correctness before implementing, ask questions on unclear feedback
---

# Code Review Reception

## Overview

A systematic approach to receiving code review feedback that prioritizes technical verification over performative agreement.

**Announce at start:** "I'm using the receiving-code-review skill to process this feedback."

## Core Principle

"Verify before implementing. Ask before assuming. Technical correctness over social comfort."

## The Five-Step Response Pattern

**Step 1: Read feedback completely**
Don't implement partway. Read everything first.

**Step 2: Restate requirements in your own words**
"So you're saying [restating in my words] — is that right?"

**Step 3: Check against actual codebase**
Verify the suggestion applies to this specific codebase before assuming it's correct.

**Step 4: Evaluate technical soundness**
- Is this technically correct?
- Would this change violate YAGNI?
- Does this conflict with architectural decisions?

**Step 5: Respond with technical substance**
- **Implement:** Restate the requirement you're addressing and show your implementation
- **Respectfully object:** Explain the technical reasoning for the current approach

Never respond with performative language like "You're absolutely right!" or "Great feedback!"

## Anti-Patterns to Avoid

❌ "You're absolutely right!"
❌ "Great feedback!"
❌ Implementing halfway through reading feedback
❌ Assuming feedback is always correct

✅ "So you're asking me to [restate]. Here's my concern..."
✅ "Let me verify this won't break [existing feature]"

## Red Flags

Never:
- Start implementing without understanding the full feedback
- Agree with unclear feedback to be polite
- Skip technical verification
- Accept suggestions without checking for breaking changes
