# Railway Deployment Configuration

## Current Deployment

- **Platform**: Railway
- **Region**: US West (Oregon, USA)
- **Plan**: Hobby ($5/month)
- **Repository**: github.com/timetogetschwifty/photo-bot
- **Branch**: main
- **Auto-deploy**: Enabled (on push to main)

## Environment Variables (Required)

Set these in Railway Dashboard → Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `123456789:ABCdef...` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `YOOMONEY_PROVIDER_TOKEN` | YooMoney payment provider token | `381764678:TEST:...` (TEST) or `381764678:LIVE:...` (production) |
| `ADMIN_ID` | Telegram user ID of admin | `280191018` |
| `BOT_USERNAME` | Bot username WITHOUT @ (for referral links https://t.me/{value}) | `top_ai_photo_bot` |
| `SUPPORT_USERNAME` | Support Telegram username WITHOUT @ | `your_support_account` |
| `DB_PATH` | **Required** - Path to database file on Railway volume | `/data/photo_bot.db` |

## Files Deployed to Railway

Railway deploys everything from the repository except files in `.gitignore`:

### Deployed Files
- `photo_bot.py` - Main bot application
- `database.py` - Database operations
- `effects.yaml` - Effect configuration
- `requirements.txt` - Python dependencies
- `prompts/*.txt` - Effect prompt templates
- `images/*.jpg` - Example images
- `Procfile` - Railway process configuration

### NOT Deployed (in .gitignore)
- `.env` - Local environment variables
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python files
- `.DS_Store` - macOS system files
- `photo_bot.db` - Local SQLite database

## Database

- **Type**: SQLite
- **File**: `photo_bot.db` (created automatically on Railway)
- **Persistence**: Railway volume mounted at `/data`
- **Location**: `/data/photo_bot.db` in container
- **Environment Variable**: `DB_PATH=/data/photo_bot.db` (required)

### Volume Configuration

**Required:** Attach a volume to your Railway service

1. Go to Railway Dashboard → **Settings** → **Volumes**
2. Click "**Attach volume to service**"
3. Set **Volume mount path**: `/data`
4. Save changes

The database file will be created automatically on first run and persists across all deployments and restarts.

### Local Development

Locally, the database falls back to `Photo bot/photo_bot.db` (same directory as the script)

## How to Update the Bot

Railway auto-deploys when you push to GitHub main branch.

**For detailed workflow instructions, see:** [POST_DEPLOYMENT_WORKFLOW.md](POST_DEPLOYMENT_WORKFLOW.md)

**Quick reference:**
- **Code changes**: `git add` → `git commit` → `git push origin main` → auto-deploys in 2-3 min
- **Environment variables**: Update in Railway Dashboard → Variables → Apply Changes (no git needed)

## Payment Configuration

### Current: YooMoney (TEST mode)

- Token: `381764678:TEST:xxxxx` (redacted for security)
- Mode: Test payments only (no real money)
- Status: ✅ Working

### For Production:

1. Get production token from YooMoney merchant dashboard
2. Update Railway variable: `YOOMONEY_PROVIDER_TOKEN`
3. Format: `123456:LIVE:xxxxx`

### Future: Telegram Stars (Planned)

- Will add dual payment system
- YooMoney (Rubles) + Telegram Stars (international)
- See ROADMAP.md for details

## Current Bot Stats

- **Bot**: @top_ai_photo_bot
- **Model**: Gemini 3 Pro Image Preview
- **Status**: ✅ Live (TEST payment mode)
- **Last Deploy**: 2026-02-12

## Troubleshooting

### Environment Variable Not Loading

1. Railway Dashboard → Variables
2. Delete the variable
3. Re-add it
4. Click "Apply Changes" or restart deployment

### Bot Not Responding

Check logs for:
```
Application started
Bot started successfully!
```

### Payment Not Working

Check logs for:
```
DEBUG: YooMoney token loaded: True
DEBUG: YooMoney token length: 21
```

If False, environment variable not loaded correctly.

## Database Access for Analysis

### Download Database from Railway

Use Railway CLI to download the database for local analysis:

```bash
# Install Railway CLI (one-time)
npm i -g @railway/cli

# Login and link to project
railway login
railway link

# Download database file
railway run cat /data/photo_bot.db > photo_bot_backup.db
```

Now you can analyze `photo_bot_backup.db` locally with SQL tools, Python, or Excel.

### Built-in Analytics

The bot has a `/admin` command that shows:
- Total users and generations
- Revenue statistics (total + per-package breakdown)
- Effect popularity (generations per effect)

**Note:** User segments analysis requires running SQL queries or export scripts. See [DATA_ANALYSIS.md](DATA_ANALYSIS.md) and [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md)

---

## Monitoring

### Health Checks

- Check bot responds to `/start` command
- Check menu displays correctly
- Check effect loading works
- Check payment flow (TEST mode)

### Logs

```
Railway Dashboard → Deployments → View Logs
```

Look for:
- `ERROR` entries
- Payment errors
- API failures
- Database errors

## Costs

- **Current**: $5/month (Hobby plan)
- **Usage**: Should stay within free tier for low traffic
- **Estimate**: Suitable for hundreds of users

## Next Steps

- [ ] Get production YooMoney token
- [ ] Implement Telegram Stars payment
- [ ] Set up staging environment for testing (optional)
- [ ] Monitor usage and costs
