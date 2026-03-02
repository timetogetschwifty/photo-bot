# Spec Audit Template

Use this when you want to verify that the current code matches the UI spec.
Paste this prompt into a new Claude Code session. **Read-only — no edits.**

---

## Audit Prompt

```
Spec audit — read only, no code edits.

1. Read docs/UI_FLOW_v3.md fully.
2. Read photo_bot.py and any handler/helper files referenced in it.
3. For each named screen below, find the corresponding handler or code block
   and check all four of the following — quote both sides when there is a mismatch:

   a) BUTTON LABELS — exact wording of every reply-keyboard and inline-keyboard
      button. Flag any difference, including synonyms (e.g. spec: "Пригласить друга",
      code: "Позвать друга" → DIVERGENT).

   b) MESSAGE TEXT / COPY — exact strings sent to the user (bot.send_message,
      bot.edit_message_text, captions, etc.). Flag any wording difference or
      missing placeholder (e.g. spec: "⚡ Осталось зарядов: {remaining}",
      code omits the line → DIVERGENT).

   c) NAVIGATION — where each button leads. Flag wrong targets or missing back actions.

   d) EDGE CASES — error states, no-credits guard, wrong-input handling.
      Flag any edge case present in spec but absent in code, or handled differently.

Screens to audit:
  MAIN_MENU, BROWSING, EFFECT_DETAIL, WAITING_LUCKY_PROMPT,
  NO_CREDITS, WRONG_INPUT, PROCESSING, RESULT, ERROR,
  STORE, WAITING_PAYMENT, PAYMENT_SUCCESS,
  PROMO_INPUT, PROMO_SUCCESS, REFERRAL, ABOUT

4. Report findings in three sections:

   MISSING    — spec defines it, no matching code found
   DIVERGENT  — code differs from spec; always quote spec line vs. code line
   CONFIRMED  — matches spec on all four checks above

5. Do not suggest fixes. Do not edit any file. Report only.
```

---

## When to Run

- After any session that touched UI, handlers, or state transitions
- Before starting a new feature that touches an existing screen
- When a bug is reported that sounds like a navigation or copy issue

## Output

Save the result as `docs/SPEC_AUDIT_RESULT.md` with the date in the header.
Compare against the previous audit result to see what regressed or was fixed.
