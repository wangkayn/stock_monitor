# Stock Monitor

AI-powered stock news monitoring with Telegram bot interface. Aggregates news from multiple free sources, analyzes with AI, and delivers summaries via Telegram.

AI 驱动的股票新闻监控系统，通过 Telegram Bot 推送新闻摘要和突发新闻提醒。

## Features

- **Multi-source news aggregation** - Yahoo Finance, Google News, Seeking Alpha, MarketWatch (free RSS), Finnhub API
- **AI-powered analysis** - Works with any OpenAI-compatible API (DeepSeek, OpenAI, Groq, Ollama, etc.)
- **Telegram bot** - `/add`, `/remove`, `/list`, `/summary` commands with inline buttons
- **Two-level summary** - Compact overview list + click for detailed analysis
- **Daily auto-push** - Summary before US market open (7:30 AM ET)
- **Breaking news alerts** - Hourly check for urgent high-impact news
- **Bilingual** - Chinese or English output (`LANGUAGE=zh` or `LANGUAGE=en`)
- **Caching** - `/summary` returns cached results instantly, zero extra API cost

## Quick Start

```bash
# Clone
git clone https://github.com/your-username/stock-monitor.git
cd stock-monitor

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys (see Configuration below)

# Create required directories
mkdir -p data logs

# Run
python main.py
```

## Configuration

Copy `.env.example` to `.env` and fill in:

### Required

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Create via [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `AI_API_KEY` | API key for your AI provider |
| `AI_BASE_URL` | API endpoint (see AI Providers below) |
| `AI_MODEL` | Model name |

### AI Providers

Any OpenAI-compatible API works. Recommended options:

| Provider | BASE_URL | MODEL | Cost |
|----------|----------|-------|------|
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-chat` | ~$0.001/summary |
| OpenAI | _(leave empty)_ | `gpt-4o-mini` | ~$0.01/summary |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-70b-versatile` | Free tier |
| Ollama | `http://localhost:11434/v1` | `llama3` | Free (local) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGUAGE` | `zh` | Output language: `zh` (Chinese) or `en` (English) |
| `FINNHUB_API_KEY` | - | [Finnhub](https://finnhub.io) API key (free, recommended) |
| `CHECK_INTERVAL_MINUTES` | `60` | News fetch interval |
| `DAILY_SUMMARY_TIME` | `07:30` | Daily push time (ET) |

## Bot Commands

| Command | Description |
|---------|-------------|
| `/add TICKER` | Add stock (e.g., `/add AAPL`) |
| `/remove TICKER` | Remove stock |
| `/list` | View watchlist with Yahoo Finance links |
| `/summary` | Get cached summary (click for details) |
| `/help` | Show help |

## How It Works

```
Startup → Initial fetch → Cache
                ↓
Every 60 min → Fetch news (RSS+API) → AI analyze → Update cache → Check breaking news
                ↓
07:30 daily → Fetch + Analyze → Auto-push to Telegram
                ↓
/summary → Return cached result instantly (no API call)
```

1. **News Sources**: Free RSS feeds (Yahoo Finance, Google News, Seeking Alpha, MarketWatch) + API sources (Finnhub)
2. **AI Analysis**: Sends top 10 articles to AI for sentiment analysis, key developments, risk factors
3. **Two-level Output**: Compact list with brief per ticker → click inline button for detailed analysis
4. **Breaking News**: If latest news is urgent + high impact, sends alert immediately

## Running as a Service

```bash
# Start in background
./start.sh

# Stop
./stop.sh

# View logs
tail -f logs/stock_monitor.log
```

## News Sources

**Free (no API key needed):**
- Yahoo Finance RSS
- Google News RSS
- Seeking Alpha RSS
- MarketWatch RSS

**API (free tier available):**
- Finnhub (60 calls/min)
- NewsAPI (100 req/day, often rate-limited)

## Project Structure

```
main.py                     # Entry point, scheduler, caching logic
src/
  ai_analyzer.py            # AI analysis (OpenAI-compatible API)
  news_fetcher.py           # News aggregation (RSS + API)
  social_fetcher.py         # Social media fetcher (Reddit/Twitter)
  stock_manager.py          # Watchlist management (data/stocks.json)
  chat/
    __init__.py              # Chat adapter factory
    base.py                  # Abstract ChatAdapter base class
    telegram_adapter.py      # Telegram implementation
  locale/
    __init__.py              # i18n loader
    zh.py                    # Chinese strings
    en.py                    # English strings
```

## License

MIT
