# Data Analysis v2 — Core Metrics

**Last updated:** 2026-02-22

---

## Core Metrics (Weekly)

| # | Metric | Question it answers | Formula | Why it matters | Actions |
|---|--------|---------------------|---------|----------------|---------|
| 1 | New Users (7d) | How many new users did we get this week? | users created in last 7 days | Top-of-funnel growth | Low → check acquisition channels |
| 2 | Activation Rate (24h) | How many users who signed up this week generated a photo within their first 24h? | new users with >=1 generation within 24h / new users | First generation quality | Low → simplify onboarding, stronger nudge |
| 3 | Returning Active Users (7d) | How many existing users came back this week? | users signed up >7 days ago with >=1 generation in last 7 days | Retention-driven engagement | Low → re-engagement push, improve effects |
| 4 | Week-1 Activity Rate (cohort) | Did last week's new users engage in their first week? | users signed up 14-7 days ago with >=1 generation in days 1-7 / that cohort | Early stickiness | Low → review day 2-3 nudges |
| 5 | Avg Generations per Active User (7d) | How deeply are active users engaging — one photo or many? | total generations (7d) / returning active users (7d) | Engagement depth | Low → improve effect quality, add variety |
| 6 | Week-1 Payment Rate (cohort) | How many of last week's new users paid within their first 7 days? | users signed up 14-7 days ago with >=1 payment in days 1-7 / that cohort | New user → payment conversion | Low → review paywall timing, pricing, upsell |
| 7 | RPAU-7d | How much revenue does each active user generate this week? | weekly revenue / returning active users (7d) | Revenue efficiency per engaged user | Low → upsell actives, promo experiment |
| 8 | Revenue (7d) | How much did we earn this week in total? | sum of all purchases in last 7 days | Raw business output | Low → check if #6 and #7 are also dropping |

---

## Effects Analysis (Weekly)

| # | Metric | Question it answers | Formula | Why it matters | Actions |
|---|--------|---------------------|---------|----------------|---------|
| E1 | Top Effects by Volume + WoW Trend | Which effects are people actually using, and is that growing or shrinking? | generation count per effect ranked + % change vs prior 7d | What users use and whether it's growing or declining | Declining → investigate quality or visibility |
| E2 | Effect Failure Rate | Which effects are breaking or producing bad results? | failed generations / total generations per effect | Quality and reliability signal | High → fix or hide broken effects |
| E3 | Effect → Payment Rate | Which effects lead users to pay? | paying users who used effect X / all users who used effect X | Which effects drive monetization | High-converting → surface earlier in funnel |
| E4 | First Effect (new users) | What do new users try first — and is it a strong first impression? | most used effect on first-ever generation | What new users try first | Weak effect here → swap with a stronger one |
| E5 | Effect Repeat Rate | Do users come back to this effect or try it once and move on? | total generations of effect X / unique users who used effect X | Depth of engagement per effect | Low → effect is one-time curiosity, improve or cut |
| E6 | Effect Retention Signal | Does using this effect make users come back next week? | users who used effect X in week N with >=1 generation in week N+1 / users who used effect X in week N | Which effects create habit | Low → effect is a dead end, not building return behavior |
