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

Reward: **+3 credits** to the referrer when the invited user completes their **first generation**.

### How it works

1. User shares their link
2. New user clicks link → Telegram opens bot with `/start ref_123456`
3. On `/start`, `referred_by = 123456` is saved to the new user's record (only at account creation)
4. When the new user successfully generates their first image, `mark_referral_credited()` runs:
   - Checks `referred_by` is set and `referral_credited = 0`
   - Sets `referral_credited = 1` (permanent flag)
   - Returns the referrer's ID → bot adds +3 credits to referrer

### Conditions for referral bonus to be credited

- Referred user must be **new** (existing users clicking a ref link are ignored)
- Referred user must complete at least one successful generation
- Bonus has not been credited before (`referral_credited = 0`)

### Abuse protection

| Protection | How it works |
|------------|--------------|
| Can't refer yourself | `if referred_by == user.id: referred_by = None` in `/start` handler |
| One bonus per referred user | `referral_credited` flag set to `1` after first credit — never credited again |
| Referral only set at signup | `get_or_create_user` only passes `referred_by` to `create_user`; existing users are never updated |
| Bonus requires real usage | Triggered on first **successful generation**, not on signup |

**Gaps / no protection against:**
- A user creating many fake accounts to farm referral credits (no rate limit or device/IP check — Telegram doesn't expose this)
- Referred user getting 3 free credits from signup and never generating (referrer gets nothing — this is fine by design)
