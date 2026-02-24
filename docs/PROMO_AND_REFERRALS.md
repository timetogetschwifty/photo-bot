# Promo Codes & Referral Links

## Promo Codes

### What we have

Two types of promo codes, both created from the admin panel (`/admin`):

| Type | Button | Credits | Max uses | Expiry |
|------|--------|---------|----------|--------|
| Gift | 🎁 Подарочный промокод | 10 / 25 / 50 / 100 | 1 (one person) | None |
| Bulk | 🎟 Массовый промокод | 10 / 25 / 50 / 100 | 5 / 10 / 20 / 50 / 100 | 3 / 7 / 14 / 30 days |

Code format: `PROMO-XXXX` (random uppercase letters + digits).

### How it works

1. Admin creates a code via `/admin`
2. Code is stored in `promo_codes` table: `code, credits, max_uses, times_used, expires_at, created_at`
3. User taps "🎁 Промокод" and types the code
4. Bot checks validity, adds credits, records redemption in `promo_redemptions` table

### Conditions for a code to be valid

All of the following must pass:

- Code exists in the database
- User has not redeemed this code before
- `times_used < max_uses` (if `max_uses` is set)
- Current time is before `expires_at` (if `expires_at` is set)

### Abuse protection

| Protection | How it works |
|------------|--------------|
| One use per user per code | `promo_redemptions` has a `PRIMARY KEY (user_id, code)` — duplicate insert fails |
| Global use cap | `times_used >= max_uses` check before redemption |
| Time limit | `expires_at` compared to UTC now before redemption |

**Gaps / no protection against:**
- Admin creating unlimited codes manually
- Sharing a bulk promo code publicly before it's used up (by design — that's the point)

---

## Referral Links

### What we have

Every user has a personal referral link:
```
https://t.me/<BOT_USERNAME>?start=ref_<telegram_id>
```

Shown in the "👥 Пригласить друга" screen.

Reward: **+3 credits** to the referrer, but the trigger depends on how many referrals the referrer has already earned:

| Referrer's credited referrals so far | Trigger for the next bonus |
|--------------------------------------|---------------------------|
| 0 – 9 (earning credits 1–30) | Referred user's **first generation** |
| 10+ (earning credits 31+) | Referred user's **first payment** |

### How it works

1. User shares their link
2. New user clicks link → Telegram opens bot with `/start ref_123456`
3. On `/start`, `referred_by = 123456` is saved to the new user's record (only at account creation)
4. When the new user successfully generates their first image, `credit_referral_on_generation()` runs:
   - Checks `referred_by` is set and `referral_credited = 0`
   - Counts how many referral bonuses the referrer has already received
   - If **< 10**: sets `referral_credited = 1`, returns referrer ID → bot adds +3 credits
   - If **≥ 10**: does nothing (deferred to first payment)
5. When the referred user makes their first payment, `credit_referral_on_payment()` runs:
   - Same checks as above
   - If **≥ 10** credited referrals on the referrer's side: sets `referral_credited = 1`, returns referrer ID → bot adds +3 credits
   - If **< 10**: does nothing (was/will be handled at generation)

### Conditions for referral bonus to be credited

- Referred user must be **new** (existing users clicking a ref link are ignored)
- Bonus has not been credited before (`referral_credited = 0`)
- For referrals 1–10: referred user must complete at least one successful generation
- For referrals 11+: referred user must make at least one payment

### Abuse protection

| Protection | How it works |
|------------|--------------|
| Can't refer yourself | `if referred_by == user.id: referred_by = None` in `/start` handler |
| One bonus per referred user | `referral_credited` flag set to `1` after first credit — never credited again |
| Referral only set at signup | `get_or_create_user` only passes `referred_by` to `create_user`; existing users are never updated |
| First 10 bonuses require real usage | Triggered on first **successful generation**, not on signup |
| Bonuses 11+ require paying users | Triggered only after referred user makes their **first payment** — fake accounts farming free credits yield nothing past the first 30 |

**Gaps / no protection against:**
- First 10 referrals can still be farmed with throwaway accounts (each earns 3 free credits then generates once)
- Referred user getting 3 free credits from signup and never generating/paying (referrer gets nothing — fine by design)
