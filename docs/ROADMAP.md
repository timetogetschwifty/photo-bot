# Roadmap

**Last updated:** 2026-02-13

## Pending Fixes
- [ ] Update `SUPPORT_USERNAME` in `.env` — currently set to email, should be Telegram username

## Content Tasks
- [ ] Add ~50 effects to `effects.yaml` + `prompts/` (currently have 16)
- [ ] Add example images to `images/` folder (one per effect)
- [ ] Add welcome screen image (big picture on /start)

## Future Features
- [ ] Telegram Stars as additional payment method
- [ ] Track inactive users and notify them about new effects (e.g. "We added 10 new effects!")

## Engagement Features

### ✅ Completed
- [x] **N1: Welcome Reminder** — Code ready, sends reminder to users who signed up but never generated (24h after signup)
- [x] **N3: Credits Exhausted** — Live in production, upsell message when free users run out of credits
- [x] Notification infrastructure (notification_log table, notifications.py module, job scripts)

### 🔄 In Progress / Next Steps
- [ ] **N2: Credits Running Low** — Warn when 1 credit remaining (prepare for upsell)
- [ ] **N6: Referral Reminder** — Prompt users to share after 3rd generation
- [ ] **N4: Win-Back Offer** — Re-engage churned users (30+ days inactive) with free credits
- [ ] **N10: Admin Daily Digest** — Daily stats report via Telegram
- [ ] Set up N1 daily cron job (currently manual)

### 📋 Future Notifications (Phase 3)
- [ ] **N5: New Effects Available** — Announce new content weekly
- [ ] **N7: First Purchase Thank You** — Build loyalty after first purchase
- [ ] **N8: Power User VIP** — Reward users with 25+ generations
- [ ] **N9: Abandoned Payment** — Recover incomplete purchases
