"""
News Fetcher - Fetches financial news from multiple sources
新闻获取器 - 从多个来源获取金融新闻

Sources:
- API-based: Finnhub, NewsAPI, Alpha Vantage (require API keys)
- Free RSS: Yahoo Finance, Google News, Seeking Alpha, MarketWatch
"""

import logging
import time
import requests
import feedparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
from time import mktime

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """News article data structure"""
    title: str
    url: str
    source: str
    published_date: datetime
    summary: str = ""
    sentiment: str = "neutral"  # positive, negative, neutral
    ticker: str = ""

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'published_date': self.published_date.isoformat(),
            'summary': self.summary,
            'sentiment': self.sentiment,
            'ticker': self.ticker
        }


class NewsFetcher:
    """Fetches financial news from multiple sources"""

    def __init__(self, newsapi_key: str = None, finnhub_key: str = None,
                 alphavantage_key: str = None):
        self.newsapi_key = newsapi_key
        self.finnhub_key = finnhub_key
        self.alphavantage_key = alphavantage_key

        # Create a session with retry for SSL resilience
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1,
                      status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        self.session.mount('http://', HTTPAdapter(max_retries=retry))

    # ── Free RSS Sources (no API key needed) ──

    def fetch_yahoo_finance(self, ticker: str) -> List[NewsItem]:
        """Fetch from Yahoo Finance RSS"""
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            feed = feedparser.parse(url)

            news_items = []
            for entry in feed.entries[:15]:
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))

                news_items.append(NewsItem(
                    title=entry.get('title', ''),
                    url=entry.get('link', ''),
                    source='Yahoo Finance',
                    published_date=pub_date,
                    summary=entry.get('summary', ''),
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from Yahoo Finance for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Yahoo Finance RSS failed for {ticker}: {e}")
            return []

    def fetch_google_news(self, ticker: str) -> List[NewsItem]:
        """Fetch from Google News RSS"""
        try:
            url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            news_items = []
            for entry in feed.entries[:15]:
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))

                # Google News title often contains source: "Title - Source"
                title = entry.get('title', '')
                source_name = 'Google News'
                if ' - ' in title:
                    parts = title.rsplit(' - ', 1)
                    title = parts[0]
                    source_name = parts[1] if len(parts) > 1 else source_name

                news_items.append(NewsItem(
                    title=title,
                    url=entry.get('link', ''),
                    source=source_name,
                    published_date=pub_date,
                    summary=entry.get('summary', '')[:300],
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from Google News for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Google News RSS failed for {ticker}: {e}")
            return []

    def fetch_seeking_alpha(self, ticker: str) -> List[NewsItem]:
        """Fetch from Seeking Alpha RSS"""
        try:
            url = f"https://seekingalpha.com/api/sa/combined/{ticker}.xml"
            feed = feedparser.parse(url)

            news_items = []
            for entry in feed.entries[:10]:
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))

                news_items.append(NewsItem(
                    title=entry.get('title', ''),
                    url=entry.get('link', ''),
                    source='Seeking Alpha',
                    published_date=pub_date,
                    summary=entry.get('summary', '')[:300],
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from Seeking Alpha for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Seeking Alpha RSS failed for {ticker}: {e}")
            return []

    def fetch_marketwatch(self, ticker: str) -> List[NewsItem]:
        """Fetch from MarketWatch RSS"""
        try:
            url = "https://feeds.marketwatch.com/marketwatch/topstories/"
            feed = feedparser.parse(url)

            ticker_upper = ticker.upper()
            news_items = []
            for entry in feed.entries:
                # Filter for ticker-related articles
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".upper()
                if ticker_upper not in text and f"${ticker_upper}" not in text:
                    continue

                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))

                news_items.append(NewsItem(
                    title=entry.get('title', ''),
                    url=entry.get('link', ''),
                    source='MarketWatch',
                    published_date=pub_date,
                    summary=entry.get('summary', '')[:300],
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from MarketWatch for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"MarketWatch RSS failed for {ticker}: {e}")
            return []

    # ── API-based Sources (require API keys) ──

    def fetch_newsapi(self, ticker: str, company_name: str = "") -> List[NewsItem]:
        """Fetch from NewsAPI"""
        if not self.newsapi_key:
            return []

        try:
            query = company_name if company_name else ticker
            url = "https://newsapi.org/v2/everything"

            params = {
                'q': f'"{query}" OR "${ticker}"',
                'apiKey': self.newsapi_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(days=1)).isoformat(),
                'pageSize': 10
            }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            news_items = []
            for article in data.get('articles', []):
                news_items.append(NewsItem(
                    title=article.get('title', ''),
                    url=article.get('url', ''),
                    source=article.get('source', {}).get('name', 'NewsAPI'),
                    published_date=datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00')),
                    summary=article.get('description', ''),
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from NewsAPI for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"NewsAPI fetch failed for {ticker}: {e}")
            return []

    def fetch_finnhub(self, ticker: str) -> List[NewsItem]:
        """Fetch from Finnhub"""
        if not self.finnhub_key:
            return []

        try:
            url = f"https://finnhub.io/api/v1/company-news"

            params = {
                'symbol': ticker,
                'token': self.finnhub_key,
                'from': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'to': datetime.now().strftime('%Y-%m-%d')
            }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            news_items = []
            for article in data[:10]:
                news_items.append(NewsItem(
                    title=article.get('headline', ''),
                    url=article.get('url', ''),
                    source=article.get('source', 'Finnhub'),
                    published_date=datetime.fromtimestamp(article.get('datetime', 0)),
                    summary=article.get('summary', ''),
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from Finnhub for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Finnhub fetch failed for {ticker}: {e}")
            return []

    def fetch_alphavantage(self, ticker: str) -> List[NewsItem]:
        """Fetch from Alpha Vantage"""
        if not self.alphavantage_key:
            return []

        try:
            url = "https://www.alphavantage.co/query"

            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': ticker,
                'apikey': self.alphavantage_key,
                'limit': 10
            }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            news_items = []
            for article in data.get('feed', []):
                time_str = article.get('time_published', '')
                try:
                    pub_date = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                except:
                    pub_date = datetime.now()

                news_items.append(NewsItem(
                    title=article.get('title', ''),
                    url=article.get('url', ''),
                    source=article.get('source', 'Alpha Vantage'),
                    published_date=pub_date,
                    summary=article.get('summary', ''),
                    ticker=ticker
                ))

            logger.info(f"Fetched {len(news_items)} articles from Alpha Vantage for {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Alpha Vantage fetch failed for {ticker}: {e}")
            return []

    # ── Aggregator ──

    def fetch_all(self, ticker: str, company_name: str = "") -> List[NewsItem]:
        """Fetch from all available sources"""
        all_news = []

        # Free RSS sources (always available)
        all_news.extend(self.fetch_yahoo_finance(ticker))
        all_news.extend(self.fetch_google_news(ticker))
        all_news.extend(self.fetch_seeking_alpha(ticker))
        all_news.extend(self.fetch_marketwatch(ticker))

        # API-based sources (if configured)
        if self.newsapi_key:
            all_news.extend(self.fetch_newsapi(ticker, company_name))

        if self.finnhub_key:
            all_news.extend(self.fetch_finnhub(ticker))

        if self.alphavantage_key:
            all_news.extend(self.fetch_alphavantage(ticker))

        # Remove duplicates based on URL
        seen_urls = set()
        unique_news = []
        for item in all_news:
            if item.url and item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_news.append(item)

        # Sort by date
        unique_news.sort(key=lambda x: x.published_date, reverse=True)

        logger.info(f"Total unique articles for {ticker}: {len(unique_news)}")
        return unique_news
