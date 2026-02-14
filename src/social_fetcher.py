"""
Social Media Fetcher - Fetches content from Reddit, Twitter, etc.
社交媒体获取器 - 从 Reddit、Twitter 等获取内容
"""

import logging
import praw
from typing import List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SocialPost:
    """Social media post data structure"""
    title: str
    url: str
    source: str  # reddit, twitter, etc.
    author: str
    created_date: datetime
    content: str
    score: int = 0  # upvotes, likes, etc.
    comments: int = 0
    ticker: str = ""

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'author': self.author,
            'created_date': self.created_date.isoformat(),
            'content': self.content,
            'score': self.score,
            'comments': self.comments,
            'ticker': self.ticker
        }


class RedditFetcher:
    """Fetches posts from Reddit"""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            logger.info("Reddit client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None

    def search_ticker(self, ticker: str, subreddits: List[str] = None,
                     time_filter: str = 'day', limit: int = 20) -> List[SocialPost]:
        """Search for ticker mentions in Reddit"""
        if not self.reddit:
            return []

        if subreddits is None:
            # Popular stock subreddits
            subreddits = ['wallstreetbets', 'stocks', 'investing', 'stockmarket']

        posts = []

        try:
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Search for ticker
                    for submission in subreddit.search(
                        f"${ticker} OR {ticker}",
                        time_filter=time_filter,
                        limit=limit
                    ):
                        posts.append(SocialPost(
                            title=submission.title,
                            url=f"https://reddit.com{submission.permalink}",
                            source=f"r/{subreddit_name}",
                            author=str(submission.author),
                            created_date=datetime.fromtimestamp(submission.created_utc),
                            content=submission.selftext[:500] if submission.selftext else "",
                            score=submission.score,
                            comments=submission.num_comments,
                            ticker=ticker
                        ))

                except Exception as e:
                    logger.error(f"Failed to search r/{subreddit_name}: {e}")
                    continue

            logger.info(f"Found {len(posts)} Reddit posts for {ticker}")

        except Exception as e:
            logger.error(f"Reddit search failed for {ticker}: {e}")

        return posts

    def get_hot_posts(self, ticker: str, subreddits: List[str] = None,
                     limit: int = 10) -> List[SocialPost]:
        """Get hot posts mentioning ticker"""
        if not self.reddit:
            return []

        if subreddits is None:
            subreddits = ['wallstreetbets', 'stocks']

        posts = []

        try:
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    for submission in subreddit.hot(limit=limit):
                        # Check if ticker is mentioned
                        text = f"{submission.title} {submission.selftext}".upper()
                        if f"${ticker}" in text or f" {ticker} " in text:
                            posts.append(SocialPost(
                                title=submission.title,
                                url=f"https://reddit.com{submission.permalink}",
                                source=f"r/{subreddit_name}",
                                author=str(submission.author),
                                created_date=datetime.fromtimestamp(submission.created_utc),
                                content=submission.selftext[:500] if submission.selftext else "",
                                score=submission.score,
                                comments=submission.num_comments,
                                ticker=ticker
                            ))

                except Exception as e:
                    logger.error(f"Failed to get hot posts from r/{subreddit_name}: {e}")
                    continue

            logger.info(f"Found {len(posts)} hot Reddit posts for {ticker}")

        except Exception as e:
            logger.error(f"Reddit hot posts failed for {ticker}: {e}")

        return posts


class SocialFetcher:
    """Main social media fetcher that combines all sources"""

    def __init__(self, reddit_client_id: str = None, reddit_client_secret: str = None,
                 reddit_user_agent: str = None, twitter_bearer_token: str = None):

        self.reddit = None
        if reddit_client_id and reddit_client_secret and reddit_user_agent:
            try:
                self.reddit = RedditFetcher(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    user_agent=reddit_user_agent
                )
                logger.info("Reddit fetcher initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Reddit fetcher: {e}")
        else:
            logger.info("Reddit credentials not provided, skipping Reddit monitoring")

        self.twitter_token = twitter_bearer_token
        # Twitter API implementation can be added here

    def fetch_all(self, ticker: str) -> List[SocialPost]:
        """Fetch from all available social sources"""
        all_posts = []

        if self.reddit:
            all_posts.extend(self.reddit.search_ticker(ticker))
            all_posts.extend(self.reddit.get_hot_posts(ticker))

        # Remove duplicates
        seen_urls = set()
        unique_posts = []
        for post in all_posts:
            if post.url not in seen_urls:
                seen_urls.add(post.url)
                unique_posts.append(post)

        # Sort by score and date
        unique_posts.sort(key=lambda x: (x.score, x.created_date), reverse=True)

        logger.info(f"Total unique social posts for {ticker}: {len(unique_posts)}")
        return unique_posts[:20]  # Limit to top 20
