name: US100 Signal Bot

on:
  schedule:
    - cron: '*/5 * * * *'   # every 5 minutes
  workflow_dispatch:         # manual trigger button in GitHub

jobs:
  run-signal:
    runs-on: ubuntu-latest
    timeout-minutes: 4

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run signal bot
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python signal_bot.py
```

---

## Step 5 — Push the files to GitHub

If you don't have Git on your laptop, you can create all three files directly in the GitHub website using the "Add file → Create new file" button. Paste the content, commit each one.

---

## Step 6 — Test it manually

Go to your repo → **Actions tab** → click `US100 Signal Bot` → click **Run workflow** → Run workflow. Check the logs — if everything is green, your bot is live. It will now run automatically every 5 minutes forever, even when your laptop is off.

---

## What the Telegram alert looks like
```
▲ US100 LONG SIGNAL
━━━━━━━━━━━━━━━━━━
Entry:   19,842.5
SL:      19,809.3  (1.1x ATR)
TP1:     19,893.8  (1:1.5 RR)
TP2:     19,970.2  (1:2.5 RR)
━━━━━━━━━━━━━━━━━━
VWAP: 19,830.1  |  RSI: 52.4  |  ATR: 30.2
Strategy: VWAP Momentum Pullback
Timeframe: 5-min · NQ Futures
