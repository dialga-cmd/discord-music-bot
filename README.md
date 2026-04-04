# Discord Music Bot - GitHub Actions

This bot runs on a schedule using GitHub Actions (completely free).

## Setup Instructions

### 1. Create GitHub Repository
- Go to https://github.com/new
- Create repo named `discord-music-bot`
- Make it **Public**
- Click "Create repository"

### 2. Add Your Files
Upload these files to your repo root:
- `main.py`
- `requirements.txt`
- `audio_final.opus`
- `.github/workflows/bot.yml`

### 3. Add Secrets to GitHub
Go to your repo → Settings → Secrets and variables → Actions

Click "New repository secret" and add:

**DISCORD_TOKEN**
- Value: Your bot token from Discord Developer Portal

**VOICE_CHANNEL_ID**
- Value: Your voice channel ID (right-click channel in Discord with Developer Mode on)

### 4. Configure Schedule (Optional)
Edit `.github/workflows/bot.yml`:

```yaml
schedule:
  # Change the cron time to when you want it to run
  - cron: '30 12 * * *'  # Daily at 12:30 PM UTC (6:00 PM IST)
```

**Common Cron Times:**
```
'0 12 * * *'   = 12:00 PM UTC (5:30 PM IST)
'30 12 * * *'  = 12:30 PM UTC (6:00 PM IST)
'0 13 * * *'   = 1:00 PM UTC (6:30 PM IST)
'0 14 * * *'   = 2:00 PM UTC (7:30 PM IST)
'0 15 * * *'   = 3:00 PM UTC (8:30 PM IST)
'0 16 * * *'   = 4:00 PM UTC (9:30 PM IST)
'0 17 * * *'   = 5:00 PM UTC (10:30 PM IST)
```

### 5. Configure Duration
Edit `.github/workflows/bot.yml`:

```yaml
DURATION_MINUTES: 60  # Change this to how long you want it to play
```

### 6. Test It
- Go to your repo → Actions tab
- Click "Run Discord Bot" workflow
- Click "Run workflow" button
- Watch it run in real-time in the logs

## How It Works

- GitHub Actions runs your bot on the schedule you set
- Bot connects to Discord and plays music for the duration you specify
- After duration expires, bot automatically disconnects
- No need to keep your computer on
- Completely free (GitHub gives free compute time)

## Logs

To see what your bot did:
1. Go to repo → Actions tab
2. Click the most recent workflow run
3. Click "run-bot" job to see logs

## Notes

- The bot runs for the duration you set (default: 60 minutes)
- After that, it automatically disconnects
- Schedule uses UTC time, not IST
- To convert IST to UTC: subtract 5.5 hours
  - 6 PM IST = 12:30 PM UTC
  - 7 PM IST = 1:30 PM UTC
  - 8 PM IST = 2:30 PM UTC
