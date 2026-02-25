# UI Flow — Photo Bot (v2)

Reference for every screen, every button, and where it leads.
This version adds missing real-world paths from `photo_bot.py`.

## What Was Added In v2
1. Added deep-link path: `/start browse` opens browsing directly.
2. Clarified that main menu is now shown consistently in reply-keyboard mode
   (normal `/start`, inline `back_to_main` / `restart`, and stale callback recovery).
3. Marked `BROWSING root` and `[Category]` images as optional (`🖼️*`), not always required.
4. Clarified payment cancel button text in UI is `⬅️ Назад`.
5. Added note that reply-keyboard shortcuts are active across user-facing states.

```
LEGEND
  🖼️  = image required    🖼️* = image optional (text-only if missing)
  📝  = text              ⌨️  = inline keyboard    ⚠️ = edge case / error

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/start
├── (default) MAIN MENU  [🖼️* 📝 reply-KB]
│   ├── ✨ Создать магию
│   │   └── BROWSING root  [🖼️* 📝 ⌨️]
│   │       ├── [Category]  [🖼️* 📝 ⌨️]
│   │       │   ├── [Effect]
│   │       │   │   ├── ⚠️ credits < 1 → NO CREDITS  [📝 ⌨️]
│   │       │   │   │       ├── 💳 Купить заряды → STORE
│   │       │   │   │       ├── 👥 Пригласить друга → REFERRAL
│   │       │   │   │       └── ⬅️ Назад → [Category]
│   │       │   │   └── credits ≥ 1 → WAITING_PHOTO  [🖼️* 📝 ⌨️]
│   │       │   │           ├── ⬅️ Назад → [Category]
│   │       │   │           ├── [non-photo] → PROMPT  [📝 ⌨️]  (stays WAITING_PHOTO)
│   │       │   │           │       └── ⬅️ Назад → [Category]
│   │       │   │           └── [send photo] → ⏳ processing
│   │       │   │                   ├── ✅ result photo  [🖼️ 📝]  ← NEVER deleted, no buttons
│   │       │   │                   │       └── nav msg  [📝 ⌨️]
│   │       │   │                   │               └── ⬅️ Назад → BROWSING
│   │       │   │                   ├── ⚠️ no image → ERROR  [📝 ⌨️]
│   │       │   │                   │       ├── 🔄 Попробовать снова → WAITING_PHOTO
│   │       │   │                   │       └── ⬅️ Назад → [Category]
│   │       │   │                   └── ⚠️ exception → ERROR  [📝 ⌨️]  (same buttons)
│   │       │   └── ⬅️ Назад → BROWSING root
│   │       ├── [Effect]  (top-level, same flow as above but ⬅️ → BROWSING root)
│   │       └── ⬅️ Назад → MAIN MENU
│   │
│   ├── 💳 Пополнить запасы
│   │   └── STORE  [📝 ⌨️]
│   │       ├── 10 зарядов — 99 ₽  ─┐
│   │       ├── 25 зарядов — 229 ₽  ├─► WAITING_PAYMENT  [📝 native invoice]
│   │       ├── 50 зарядов — 399 ₽  │       ├── [pay] → SUCCESS  [📝 ⌨️]
│   │       ├── 100 зарядов — 699 ₽─┘       │             └── ⬅️ Назад → MAIN MENU
│   │       └── ⬅️ Назад → MAIN MENU        └── ⬅️ Назад (cancel) → STORE
│   │                                          (deletes invoice + cancel msg)
│   │
│   ├── 🎁 Промокод
│   │   └── PROMO_INPUT  [📝 ⌨️]
│   │       ├── [type code] ✅ valid   → SUCCESS  [📝 ⌨️]
│   │       │                             └── ⬅️ Назад → MAIN MENU
│   │       ├── [type code] ❌ invalid → ERROR  [📝 ⌨️]
│   │       │                             ├── 🔄 Попробовать другой → PROMO_INPUT
│   │       │                             └── ⬅️ Назад → MAIN MENU
│   │       └── ⬅️ Назад → MAIN MENU
│   │
│   ├── 👥 Пригласить друга
│   │   └── REFERRAL  [📝 ⌨️]
│   │       └── ⬅️ Назад → MAIN MENU
│   │
│   └── ℹ️ О проекте
│       └── ABOUT  [📝 ⌨️]
│           ├── ✉️ Написать в поддержку → t.me/support  (external, only if configured)
│           └── ⬅️ Назад → MAIN MENU
│
└── (deep link) /start browse
    └── BROWSING root directly  [📝 ⌨️]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADMIN  (/admin, ADMIN_ID only)

└── ADMIN_MENU  [📝 ⌨️]
    ├── 📊 Статистика → ADMIN_STATS  [📝 ⌨️]
    │       └── ⬅️ Назад → ADMIN_MENU
    ├── 📈 Weekly Report → sends weekly metrics message  [📝 ⌨️]
    │       └── ⬅️ Назад → ADMIN_MENU
    ├── 🗂 Raw Data → sends Excel file (users/generations/purchases)  [📝 ⌨️]
    │       └── ⬅️ Назад → ADMIN_MENU
    ├── 🎁 Создать промокод → ADMIN_PROMO  [📝 ⌨️]
    │       ├── 10 зарядов ─┐
    │       ├── 25 зарядов  ├─► PROMO CREATED  [📝 ⌨️]
    │       ├── 50 зарядов  │       ├── 🎁 Создать ещё → ADMIN_PROMO
    │       ├── 100 зарядов ┘       └── ⬅️ Назад → ADMIN_MENU
    │       └── ⬅️ Назад → ADMIN_MENU
    ├── 🎟 Массовый промокод → ADMIN_BULK_PROMO  [📝 ⌨️]
    │       ├── Select credits ─► Select quantity ─► BULK PROMO CREATED  [📝 ⌨️]
    │       │       ├── 🎟 Создать ещё → ADMIN_BULK_PROMO
    │       │       └── ⬅️ Назад → ADMIN_MENU
    │       └── ⬅️ Назад → ADMIN_MENU
    └── 🏠 Выход → MAIN MENU

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EDGE CASES  (automatic, user never triggers these on purpose)

⚠️ User sends photo but bot lost track of which effect was selected:
    [📝 ⌨️]  └── 🔄 Начать заново → MAIN MENU

⚠️ User taps an old button after bot was redeployed/restarted:
    spinner dismissed automatically → MAIN MENU  [🖼️* 📝 reply-KB]
    (result photos with ✅ caption are never deleted in this process)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


