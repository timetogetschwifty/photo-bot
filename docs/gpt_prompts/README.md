# GPT Prompt Setup Guide — v3.3

## Files

| File | Paste into | What it does |
|------|-----------|--------------|
| `stage_0_system_prompt.md` | Trend Scanner GPT | Scans trends, outputs trend signals |
| `stage_1_system_prompt.md` | Idea Generator GPT | Takes trends, outputs 10 transformation ideas |
| `stage_1.5_system_prompt.md` | Idea Developer GPT | Takes your raw concept, outputs 1 structured idea |
| `stage_2_system_prompt.md` | Production Prompt Engineer GPT | Takes structured idea, outputs production-ready prompt |

## How to use

1. Open each file
2. Select all text (Cmd+A)
3. Copy (Cmd+C)
4. Paste into the GPT's system prompt / custom instructions field

## Pipeline flow

```
Stage 0 (trends) ──> Stage 1 (10 ideas) ──> Stage 2 (production prompt)
                                      OR
            Your raw idea ──> Stage 1.5 (1 idea) ──> Stage 2 (production prompt)
```

## How to pass data between stages

**Stage 0 → Stage 1:**
Copy the trend signals from Stage 0's output. Paste them into your Stage 1 message where it says `[Paste Stage 0 trend signals here]`.

**Stage 1 or 1.5 → Stage 2:**
Copy the full idea output (all 6 fields). Paste it as your message to the Stage 2 GPT.

**Skipping Stage 0:**
If you don't use Stage 0, just describe the current trends/season yourself in your Stage 1 message.

**Using Stage 1.5 instead of Stage 1:**
Send your raw idea as a message to Stage 1.5 GPT. It will structure it into the same format Stage 1 outputs. Then pass that output to Stage 2.
