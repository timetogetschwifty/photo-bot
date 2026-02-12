# Post-Deployment Workflow Guide

**For deployment configuration (environment variables, what's deployed, etc.), see:** [RAILWAY_CONFIG.md](RAILWAY_CONFIG.md)

---

## 🎯 How Updates Work

**Short answer:** YES! Railway automatically deploys when you push to GitHub.

```
Your Mac                GitHub              Railway              Live Bot
   │                      │                    │                    │
   ├─ Make changes        │                    │                    │
   ├─ git push ──────────→│                    │                    │
   │                      ├─ Receives push     │                    │
   │                      ├─ Webhook ─────────→│                    │
   │                      │                    ├─ Detects change    │
   │                      │                    ├─ Builds new version│
   │                      │                    ├─ Tests build       │
   │                      │                    ├─ Deploys (2-3 min) │
   │                      │                    └───────────────────→│
   │                      │                    │              ✅ Updated!
```

**Zero downtime:** Old version keeps running until new one is ready, then switches automatically.

---

## 📝 Common Tasks - Step by Step

### Task 1: Add New Effect (Most Common)

**Example: Adding "Pirate" effect**

#### Step 1: Create Prompt File (Local)

```bash
cd "/Users/tray/Documents/Useful/Projects/Photo bot"

# Create new prompt
nano prompts/pirate.txt
```

**Add content:**
```
===PROMPT===
Transform this photo into a swashbuckling pirate captain portrait from the
Golden Age of Piracy (1650-1730). Preserve exact facial features, identity,
and expression. Replace modern clothing with weathered leather tricorn hat,
long dark coat with brass buttons, white billowing shirt, and leather bandolier.
Add dramatic ocean backdrop with ship's deck, stormy seas, and sunset sky.
Render in cinematic adventure film style with rich colors, dramatic lighting,
and authentic historical details. Include subtle pirate elements like compass,
rope, or ship's wheel. Maintain realistic proportions and natural appearance.
===END PROMPT===
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

#### Step 2: Add Preview Image

```bash
# Add preview image (you need to have pirate.png ready)
cp ~/Downloads/pirate.png images/pirate.png

# Verify it's there
ls -la images/pirate.png
```

#### Step 3: Update effects.yaml

```bash
nano effects.yaml
```

**Add new effect** (find the right spot and add):

```yaml
pirate:
  enabled: true
  order: 10
  label: "🏴‍☠️ Pirate Captain"
  tips: "Transform into a fearsome pirate captain from the Golden Age"
  category: "historical"
```

**Note:** Files are auto-resolved by effect ID:
- Prompt: `prompts/pirate.txt` (required)
- Image: `images/pirate.jpg` or `.png` (optional)

**Save:** `Ctrl+X`, then `Y`, then `Enter`

#### Step 4: Test Locally (Optional but Recommended)

```bash
# Activate virtual environment
source .venv/bin/activate

# Test the prompt with test_prompt.py
# First, update testing/prompt.txt with your new prompt
cp prompts/pirate.txt testing/prompt.txt

# Run test
python test_prompt.py

# Verify it generates good image
# (opens automatically if on macOS)
```

#### Step 5: Commit Changes

```bash
# Check what changed
git status

# Should show:
#   modified: effects.yaml
#   new file: prompts/pirate.txt
#   new file: images/pirate.png

# Stage all changes
git add effects.yaml prompts/pirate.txt images/pirate.png

# Commit with descriptive message
git commit -m "Add Pirate effect: swashbuckling captain transformation"

# Check commit was created
git log -1
```

#### Step 6: Push to GitHub

```bash
# Push to main branch
git push origin main

# Should see:
#   Counting objects: ...
#   Writing objects: 100% ...
#   To https://github.com/timetogetschwifty/photo-bot.git
```

#### Step 7: Railway Auto-Deploys (Automatic!)

**What happens automatically:**

```
00:00 - GitHub receives your push
00:05 - GitHub webhook notifies Railway
00:10 - Railway starts building new version
        ├─ Clones latest code from GitHub
        ├─ Installs dependencies (if requirements.txt changed)
        └─ Builds new container
02:30 - Build completes successfully
02:35 - Railway starts new version
        ├─ Old bot still running (no downtime!)
        ├─ New bot starts up
        └─ Health check passes
03:00 - Railway switches traffic to new version
        ├─ Old bot stops
        └─ New bot handling all requests
03:05 - ✅ Deployment complete!
```

**Total time:** 2-4 minutes

#### Step 8: Verify on Railway Dashboard

1. **Open Railway dashboard:** https://railway.app
2. **Click your project:** "photo-bot"
3. **Click "Deployments" tab**
4. **You should see:**
   ```
   🟢 main   |  Add Pirate effect...  |  3 minutes ago  |  Active
   🟢 main   |  Previous deployment   |  2 hours ago    |  Inactive
   ```

#### Step 9: Check Logs

```
Click "Logs" tab:

Should see:
  Building...
  ✓ Build successful
  Starting...
  Bot started successfully!
  Polling for updates...
```

#### Step 10: Test on Telegram

1. **Open Telegram**
2. **Send photo to your bot**
3. **New "Pirate 🏴‍☠️" button should appear!**
4. **Click it**
5. **Wait 30-60 seconds**
6. **Receive pirate transformation!** 🏴‍☠️

**Total time from start to live:** ~5-10 minutes

---

### Task 2: Update Existing Prompt

**Example: Improving "King" effect prompt**

#### Quick Method:

```bash
cd "/Users/tray/Documents/Useful/Projects/Photo bot"

# Edit prompt directly
nano prompts/king.txt

# Make your changes
# Save: Ctrl+X, Y, Enter

# Test locally (optional)
cp prompts/king.txt testing/prompt.txt
source .venv/bin/activate
python test_prompt.py

# Commit and push
git add prompts/king.txt
git commit -m "Improve King effect: add more regal details"
git push origin main

# Railway auto-deploys in 2-3 minutes
# Test on Telegram
```

**That's it!** 30 seconds of work, 3 minutes deployment.

---

### Task 3: Update effects.yaml (Change Names/Descriptions)

**Example: Rename "King" to "Royal King"**

```bash
# Edit effects.yaml
nano effects.yaml

# Find:
king:
  name: "King 👑"
  description: "Transform into a majestic royal king"

# Change to:
king:
  name: "Royal King 👑"
  description: "Transform into a regal monarch with crown and throne"

# Save and commit
git add effects.yaml
git commit -m "Update King effect name and description"
git push origin main

# Railway auto-deploys
# Changes appear immediately in Telegram bot
```

---

### Task 4: Update Bot Code (photo_bot.py)

**Example: Add new feature or fix bug**

```bash
cd "/Users/tray/Documents/Useful/Projects/Photo bot"

# Edit bot code
nano photo_bot.py

# Make your changes (add feature, fix bug, etc.)

# Test locally first (important!)
source .venv/bin/activate
python photo_bot.py
# Test with Telegram (bot runs locally)
# Ctrl+C to stop

# If working, commit and push
git add photo_bot.py
git commit -m "Fix: Handle missing image gracefully"
git push origin main

# Railway deploys in 2-3 minutes
```

**⚠️ Important:** Always test bot code changes locally first!

---

### Task 5: Add New Python Package

**Example: Adding a new library**

```bash
cd "/Users/tray/Documents/Useful/Projects/Photo bot"
source .venv/bin/activate

# Install new package
pip install requests  # example

# Update requirements.txt (CRITICAL!)
pip freeze > requirements.txt

# Commit BOTH code and requirements
git add your_file.py requirements.txt
git commit -m "Add feature X using requests library"
git push origin main

# Railway will install new package during build
```

**⚠️ Don't forget requirements.txt!** Railway needs it to install packages.

---

### Task 6: Update Environment Variable

**Example: New Gemini API key**

#### Method: Via Railway Dashboard (Recommended)

```
1. Go to Railway dashboard
2. Click your project
3. Click "Variables" tab
4. Find GEMINI_API_KEY
5. Click "Edit" (pencil icon)
6. Paste new value
7. Click "Save"

✅ Bot automatically restarts with new key!
   No git commit needed!
   Takes 30 seconds total!
```

**Note:** Variables are stored in Railway, not in code. Never commit secrets to GitHub!

---

### Task 7: Rollback Bad Deployment

**If new version breaks:**

#### Option A: Rollback via Railway Dashboard (Fast)

```
1. Railway dashboard → Deployments
2. Find last working deployment (green ✓)
3. Click ⋮ (three dots)
4. Click "Redeploy"
5. Old version goes live in 1-2 minutes
```

#### Option B: Rollback via Git (More control)

```bash
# See recent commits
git log --oneline -5

# Revert to previous commit
git revert HEAD

# Or revert specific commit
git revert abc123

# Push
git push origin main

# Railway deploys the reverted version
```

---

### Task 8: Check What's Live

**See exactly what code is running:**

```bash
# See latest commit on GitHub
git log origin/main -1

# Should match what's deployed on Railway
```

**On Railway:**
1. Deployments tab
2. "Active" deployment shows commit hash
3. Click commit hash → goes to GitHub
4. See exact code that's running

---

## 🔄 Complete Workflow Example

Let's walk through **adding 3 new effects** at once:

### Step-by-Step

```bash
# 1. Navigate to project
cd "/Users/tray/Documents/Useful/Projects/Photo bot"

# 2. Create all prompt files
echo "===PROMPT===
Pirate prompt here...
===END PROMPT===" > prompts/pirate.txt

echo "===PROMPT===
Ninja prompt here...
===END PROMPT===" > prompts/ninja.txt

echo "===PROMPT===
Astronaut prompt here...
===END PROMPT===" > prompts/astronaut.txt

# 3. Add preview images
cp ~/Downloads/pirate.png images/
cp ~/Downloads/ninja.png images/
cp ~/Downloads/astronaut.png images/

# 4. Update effects.yaml (open editor)
nano effects.yaml

# Add all three effects:
# pirate:
#   enabled: true
#   label: "🏴‍☠️ Pirate Captain"
#   ...
# ninja:
#   enabled: true
#   label: "🥷 Ninja Warrior"
#   ...
# astronaut:
#   enabled: true
#   label: "🚀 Astronaut"
#   ...

# 5. Test one locally (optional)
source .venv/bin/activate
cp prompts/pirate.txt testing/prompt.txt
python test_prompt.py

# 6. Stage all changes
git add effects.yaml prompts/*.txt images/*.png

# 7. Commit
git commit -m "Add 3 new effects: Pirate, Ninja, Astronaut"

# 8. Push
git push origin main

# 9. Watch Railway deploy (3 minutes)

# 10. Test on Telegram - all 3 effects appear!
```

**Result:** 3 new effects deployed in ~5 minutes of work!

---

## 📊 Deployment Timeline

### Typical Deployment Times

| Change Type | Build Time | Deploy Time | Total |
|-------------|------------|-------------|-------|
| **Prompt only** | 30 sec | 30 sec | ~1 min |
| **YAML + prompts** | 30 sec | 30 sec | ~1 min |
| **Code change** | 1 min | 1 min | ~2 min |
| **New package** | 3 min | 1 min | ~4 min |
| **First deploy** | 5 min | 2 min | ~7 min |

**Why so fast?**
- Railway caches dependencies
- Incremental builds
- Only rebuilds what changed

---

## 🔍 Monitoring Your Deployments

### Watch Deployment Status

**Option 1: Railway Dashboard (Visual)**
```
1. Open Railway dashboard
2. Click your project
3. "Deployments" tab shows status:
   ├─ 🔄 Building (in progress)
   ├─ 🟢 Active (deployed successfully)
   └─ 🔴 Failed (something wrong)
```

**Option 2: Real-time Logs**
```
1. Click "Logs" tab
2. See real-time output:
   Building...
   Installing dependencies...
   Starting bot...
   Bot started successfully!
```

**Option 3: Email Notifications (Optional)**
```
1. Account Settings → Notifications
2. Enable "Deployment failed"
3. Get email when something breaks
```

---

## ⚠️ Common Mistakes to Avoid

### ❌ Mistake 1: Forgetting to Update requirements.txt

```bash
# You installed package locally
pip install new-package

# Added code using it
# Committed and pushed

# Railway deployment fails! ❌
# Error: ModuleNotFoundError: No module named 'new-package'

# FIX:
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

### ❌ Mistake 2: Committing .env File

```bash
# NEVER do this:
git add .env  # ❌ Contains secrets!
git commit -m "Add env file"  # ❌ DANGER!

# Secrets will be public on GitHub!

# FIX:
# Remove from git
git rm --cached .env
git commit -m "Remove .env from git"
git push

# Add to .gitignore (already there)
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Ensure .env is ignored"
git push

# Rotate your API keys immediately!
```

### ❌ Mistake 3: Not Testing Locally

```bash
# Bad workflow:
# Make changes → Commit → Push
# Wait 3 minutes for Railway deploy
# Find bug in Telegram
# Fix → Commit → Push
# Wait 3 minutes again...
# Repeat 5 times = 15 minutes wasted!

# Good workflow:
# Make changes
# Test locally (30 seconds)
# Fix any issues
# Then commit and push once
# Saves 14.5 minutes!
```

### ❌ Mistake 4: Unclear Commit Messages

```bash
# Bad:
git commit -m "update"  # ❌ What changed?
git commit -m "fix"     # ❌ What was fixed?
git commit -m "stuff"   # ❌ Useless!

# Good:
git commit -m "Add Pirate effect with ocean background"  # ✅
git commit -m "Fix: Handle empty photo gracefully"       # ✅
git commit -m "Improve King prompt: add more details"    # ✅

# Why? When you need to rollback, you'll know exactly what each version does!
```

### ❌ Mistake 5: Pushing to Wrong Branch

```bash
# You're working on development branch
git checkout development
# Make changes
git commit -m "Experimental feature"
git push origin development

# Railway doesn't deploy! ❌
# Why? Railway watches 'main' branch only

# FIX:
# Merge to main when ready
git checkout main
git merge development
git push origin main

# Now Railway deploys ✅
```

---

## 🎯 Best Practices

### ✅ Do This:

1. **Test locally before pushing**
   ```bash
   python test_prompt.py  # Test prompts
   python photo_bot.py    # Test bot
   ```

2. **Commit messages explain WHY**
   ```bash
   git commit -m "Improve King effect: users wanted more gold details"
   ```

3. **One feature per commit**
   ```bash
   git commit -m "Add Pirate effect"  # ✅ Clear
   # Not: "Add pirate, fix bug, update readme"  # ❌ Confusing
   ```

4. **Check Railway logs after deploy**
   ```
   Verify: "Bot started successfully!"
   ```

5. **Test on Telegram immediately**
   ```
   Send /start
   Test new feature
   ```

6. **Monitor costs weekly**
   ```
   Railway → Billing → Check usage
   ```

---

## 📱 Quick Reference: Common Commands

### Daily Development

```bash
# Navigate to project
cd "/Users/tray/Documents/Useful/Projects/Photo bot"

# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Your message"

# Push (triggers deploy)
git push origin main

# View history
git log --oneline -5

# Test locally
source .venv/bin/activate
python test_prompt.py
```

### Checking Deployment

```bash
# Railway Dashboard (browser):
# https://railway.app → Your project

# Check what's deployed:
git log origin/main -1

# View commit on GitHub:
# https://github.com/timetogetschwifty/photo-bot/commits/main
```

---

## 🚀 Development Cycle

**Typical day of development:**

```
Morning:
├─ 09:00 - Check Railway logs (any errors overnight?)
├─ 09:05 - Check Telegram bot (working fine?)
└─ 09:10 - Plan new effects to add

Work:
├─ 10:00 - Create new prompt
├─ 10:15 - Test with test_prompt.py
├─ 10:30 - Tweak prompt based on results
├─ 10:45 - Final test
├─ 11:00 - Update effects.yaml
├─ 11:05 - Commit and push
└─ 11:10 - Railway auto-deploys (grab coffee ☕)

Test:
├─ 11:15 - Check Railway logs (deployed successfully?)
├─ 11:20 - Test on Telegram (works great!)
└─ 11:25 - Share with friends for feedback

Afternoon:
├─ 14:00 - Review user feedback
├─ 14:15 - Improve prompts based on feedback
├─ 14:30 - Commit and push improvements
└─ 14:35 - Railway auto-deploys (done!)

Evening:
├─ 18:00 - Check daily usage stats
├─ 18:05 - Monitor costs (still good?)
└─ 18:10 - Done for the day! ✅
```

---

## ❓ FAQ

### Q: Do I need to restart Railway manually after pushing?
**A:** No! Railway automatically detects pushes and deploys. Zero manual intervention.

### Q: Can I push multiple times in a row?
**A:** Yes, but Railway queues deployments. Each push triggers new build. Previous build gets cancelled.

### Q: How long does Railway keep old deployments?
**A:** All deployments are kept. You can rollback to any previous version anytime.

### Q: What if I push by accident?
**A:** Just revert the commit and push again:
```bash
git revert HEAD
git push origin main
```

### Q: Can I test changes without deploying?
**A:** Yes! Create a branch:
```bash
git checkout -b test-feature
# Make changes
git commit -m "Test new feature"
git push origin test-feature
# Railway doesn't deploy (not main branch)
# Test locally, then merge to main when ready
```

### Q: How do I know what version is live?
**A:** Railway Deployments tab shows commit hash. Click it to see code on GitHub.

### Q: Can I schedule deployments?
**A:** No automatic scheduling, but you can push at specific time to trigger deploy.

### Q: What happens if build fails?
**A:** Old version keeps running! No downtime. Fix the issue and push again.

---

## 🎓 Practice Exercise

**Let's add a "Detective" effect:**

1. Create prompt: `prompts/detective.txt`
2. Add image: `images/detective.png`
3. Update `effects.yaml`:
   ```yaml
   detective:
     name: "Detective 🕵️"
     description: "Become a noir detective in foggy streets"
     prompt_file: "detective.txt"
     image_file: "detective.png"
     category: "professional"
   ```
4. Test locally with `test_prompt.py`
5. Commit: `git commit -m "Add Detective effect"`
6. Push: `git push origin main`
7. Wait 3 minutes
8. Test on Telegram!

**Estimated time:** 10 minutes from start to live 🎉

---

## ✅ Summary

**The workflow is simple:**

```
Local Changes → Git Push → Railway Auto-Deploy → Live in 3 Minutes
```

**Key points:**
- ✅ Railway watches your GitHub repo
- ✅ Every push to `main` triggers deployment
- ✅ No manual steps needed
- ✅ Old version runs until new one is ready
- ✅ Zero downtime deployments
- ✅ Can rollback anytime
- ✅ Takes 2-4 minutes typically

**That's it!** Simple and automatic 🚀
