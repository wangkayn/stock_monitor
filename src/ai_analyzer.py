"""
AI Analyzer - Analyzes news and social media using OpenAI-compatible API

Supports any OpenAI-compatible provider:
- OpenAI (default)
- DeepSeek
- Groq
- Ollama (local)
- Any other OpenAI-compatible endpoint
"""

import logging
from typing import List, Dict
import httpx
from openai import AsyncOpenAI
from src.news_fetcher import NewsItem
from src.social_fetcher import SocialPost
from src.locale import t

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT = """You are a financial analyst. Analyze the following news articles and social media posts about {ticker}.

**News Articles:**
{news_summary}

**Social Media (Reddit):**
{social_summary}

Provide a comprehensive analysis. The FIRST LINE must be a brief one-line summary for quick preview.

Format:

{analysis_format}

IMPORTANT:
- {analysis_lang}
- The BRIEF line is critical - it will be shown in a compact list view.
- {analysis_brief_example}
- Each key development MUST include a clickable source link in Markdown format
- Use the exact URLs provided in the news articles above."""


BREAKING_NEWS_PROMPT = """Analyze this breaking news about {ticker}:

**Title:** {title}
**Source:** {source}
**Summary:** {summary}

Answer these questions:
1. Is this URGENT/breaking news requiring immediate attention? (Yes/No)
2. Sentiment: Bullish/Bearish/Neutral
3. Potential Impact: High/Medium/Low
4. One-line summary of what happened and why it matters

Format:
URGENT: [Yes/No]
SENTIMENT: [Bullish/Bearish/Neutral]
IMPACT: [High/Medium/Low]
{breaking_summary_instruction}"""


class AIAnalyzer:
    """Analyzes financial content using OpenAI-compatible API"""

    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(90.0, connect=10.0),
        )
        self.model = model
        logger.info(f"AI Analyzer initialized: model={model}, base_url={base_url or 'default (OpenAI)'}")

    async def validate_connection(self) -> bool:
        """Test API connection at startup."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            logger.info(f"AI API connection validated: {self.model}")
            return True
        except Exception as e:
            logger.error(f"AI API connection failed: {e}")
            return False

    async def analyze_ticker(self, ticker: str, news: List[NewsItem],
                      social: List[SocialPost]) -> str:
        """Analyze all content for a ticker and generate summary"""

        # Format news (include URL for source linking)
        if news:
            news_items = []
            for item in news[:10]:
                news_items.append(
                    f"- [{item.source}] {item.title}\n  URL: {item.url}\n  {item.summary[:200]}"
                )
            news_summary = "\n".join(news_items)
        else:
            news_summary = "No recent news found."

        # Format social
        if social:
            social_items = []
            for post in social[:10]:
                social_items.append(
                    f"- [{post.source}] {post.title} (Score: {post.score}, Comments: {post.comments})\n  URL: {post.url}\n  {post.content[:200]}"
                )
            social_summary = "\n".join(social_items)
        else:
            social_summary = "No recent social media discussions found."

        # Generate analysis
        try:
            prompt = ANALYSIS_PROMPT.format(
                ticker=ticker,
                news_summary=news_summary,
                social_summary=social_summary,
                analysis_format=t("ai_analysis_format"),
                analysis_lang=t("ai_analysis_lang"),
                analysis_brief_example=t("ai_analysis_brief_example"),
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            analysis = response.choices[0].message.content

            # Parse BRIEF line from analysis
            brief = ""
            detail_lines = []
            for line in analysis.split('\n'):
                if line.strip().startswith('BRIEF:'):
                    brief = line.strip().replace('BRIEF:', '').strip()
                else:
                    detail_lines.append(line)
            detail = '\n'.join(detail_lines).strip()

            if not brief:
                brief = t("ai_no_brief")

            logger.info(f"Generated analysis for {ticker}: {brief}")
            return {'brief': brief, 'detail': detail}

        except Exception as e:
            logger.error(f"Analysis failed for {ticker}: {e}")
            return {
                'brief': t("ai_fail_brief"),
                'detail': f"Failed to analyze {ticker}: {str(e)}"
            }

    async def analyze_breaking_news(self, ticker: str, news_item: NewsItem) -> Dict[str, str]:
        """Analyze a single news item for urgency"""

        try:
            prompt = BREAKING_NEWS_PROMPT.format(
                ticker=ticker,
                title=news_item.title,
                source=news_item.source,
                summary=news_item.summary,
                breaking_summary_instruction=t("ai_breaking_summary_instruction"),
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.choices[0].message.content

            # Parse response
            result = {
                'urgent': False,
                'sentiment': 'neutral',
                'impact': 'low',
                'summary': ''
            }

            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('URGENT:'):
                    result['urgent'] = 'yes' in line.lower()
                elif line.startswith('SENTIMENT:'):
                    sentiment = line.split(':', 1)[1].strip().lower()
                    if sentiment in ['bullish', 'bearish', 'neutral']:
                        result['sentiment'] = sentiment
                elif line.startswith('IMPACT:'):
                    impact = line.split(':', 1)[1].strip().lower()
                    if impact in ['high', 'medium', 'low']:
                        result['impact'] = impact
                elif line.startswith('SUMMARY:'):
                    result['summary'] = line.split(':', 1)[1].strip()

            logger.info(f"Breaking news analysis for {ticker}: urgent={result['urgent']}, impact={result['impact']}")
            return result

        except Exception as e:
            logger.error(f"Breaking news analysis failed: {e}")
            return {
                'urgent': False,
                'sentiment': 'neutral',
                'impact': 'low',
                'summary': news_item.title
            }
