# Create Test Bot - Step by Step

## 📱 Step 1: Create Test Bot on Telegram (3 minutes)

1. **Open Telegram** (phone or desktop)

2. **Search for:** `@BotFather`

3. **Send:** `/newbot`

4. **BotFather asks:** "Alright, a new bot. How are we going to call it?"
   - **Reply:** `Photo Bot TEST`

5. **BotFather asks:** "Now, let's choose a username for your bot."
   - **Reply:** `your_username_photo_bot_test`
   - (Must end with `_bot` or `Bot`)

6. **BotFather responds:** "Done! ..."
   - **Copy the token:** `1234567890:ABCdef_GHIjkl_MNOpqr`
   - Save it somewhere!

## 💻 Step 2: Create .env.test File (2 minutes)

```bash
cd "/Users/tray/Documents/Useful/Projects/Photo bot"

# Create test environment file
nano .env.test
```

**Paste this** (replace with your tokens):

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdef_GHIjkl_MNOpqr
GEMINI_API_KEY=your_gemini_key_from_.env_file
```

**Save:** `Ctrl+X`, then `Y`, then `Enter`

## ✅ Step 3: Test It Works

```bash
# Load test environment
source .venv/bin/activate
export $(cat .env.test | xargs)

# Run bot
python photo_bot.py

# Should see:
# Bot started successfully!
```

**Open Telegram:**
- Search: `@your_username_photo_bot_test`
- Send: `/start`
- Bot responds: "Welcome..." ✅

**Stop bot:** `Ctrl+C`

## 🎉 Done!

Now you have:
- ✅ Production bot (@yourphotobot) - for real users
- ✅ Test bot (@yourphotobot_test) - for development

## 🔧 Using Test Bot

**Every time you want to test:**

```bash
cd "/Users/tray/Documents/Useful/Projects/Photo bot"
source .venv/bin/activate

# Run with test token
export $(cat .env.test | xargs)
python photo_bot.py

# Test in Telegram with test bot
# Ctrl+C when done
```

**Production bot stays live on Railway!** ✅
