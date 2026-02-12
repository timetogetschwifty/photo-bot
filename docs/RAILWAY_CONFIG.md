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
| `BOT_USERNAME` | Bot username (for referral links) | `@top_ai_photo_bot` |
| `SUPPORT_USERNAME` | Support contact (shown in "О проекте") | `dude@dude.com` |

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
- `bot.db` - Local SQLite database

## Database

- **Type**: SQLite
- **File**: `bot.db` (created automatically on Railway)
- **Persistence**: Railway volume (persists across deployments)
- **Location**: `/app/bot.db` in container

## How to Update the Bot

Railway auto-deploys when you push to GitHub main branch.

**For detailed workflow instructions, see:** [POST_DEPLOYMENT_WORKFLOW.md](POST_DEPLOYMENT_WORKFLOW.md)

**Quick reference:**
- **Code changes**: `git add` → `git commit` → `git push origin main` → auto-deploys in 2-3 min
- **Environment variables**: Update in Railway Dashboard → Variables → Apply Changes (no git needed)

## Payment Configuration

### Current: YooMoney (TEST mode)

- Token: `381764678:TEST:164315`
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
