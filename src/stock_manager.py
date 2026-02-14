"""
Stock Manager - Manages watched stock list
股票管理器 - 管理关注股票列表
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Stock:
    """Stock information"""
    ticker: str  # Stock ticker symbol (e.g., AAPL, TSLA)
    name: str = ""  # Company name
    added_date: str = ""
    keywords: List[str] = None  # Additional keywords to monitor

    def __post_init__(self):
        self.ticker = self.ticker.upper()
        if self.keywords is None:
            self.keywords = []


class StockManager:
    """Manages the list of stocks to monitor"""

    def __init__(self, data_file: Path = Path("data/stocks.json")):
        self.data_file = data_file
        self.stocks: Dict[str, Stock] = {}
        self._load()

    def _load(self):
        """Load stocks from file"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for ticker, stock_data in data.items():
                        self.stocks[ticker] = Stock(**stock_data)
                logger.info(f"Loaded {len(self.stocks)} stocks")
            except Exception as e:
                logger.error(f"Failed to load stocks: {e}")
        else:
            logger.info("No existing stock list found, starting fresh")

    def _save(self):
        """Save stocks to file"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                data = {ticker: asdict(stock) for ticker, stock in self.stocks.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.stocks)} stocks")
        except Exception as e:
            logger.error(f"Failed to save stocks: {e}")

    def add_stock(self, ticker: str, name: str = "", keywords: List[str] = None) -> bool:
        """Add a stock to monitor"""
        from datetime import datetime

        ticker = ticker.upper()

        if ticker in self.stocks:
            logger.warning(f"Stock {ticker} already exists")
            return False

        self.stocks[ticker] = Stock(
            ticker=ticker,
            name=name,
            added_date=datetime.now().isoformat(),
            keywords=keywords or []
        )
        self._save()
        logger.info(f"Added stock: {ticker}")
        return True

    def remove_stock(self, ticker: str) -> bool:
        """Remove a stock from monitoring"""
        ticker = ticker.upper()

        if ticker not in self.stocks:
            logger.warning(f"Stock {ticker} not found")
            return False

        del self.stocks[ticker]
        self._save()
        logger.info(f"Removed stock: {ticker}")
        return True

    def get_stock(self, ticker: str) -> Optional[Stock]:
        """Get stock information"""
        return self.stocks.get(ticker.upper())

    def list_stocks(self) -> List[Stock]:
        """Get all stocks"""
        return list(self.stocks.values())

    def get_all_tickers(self) -> List[str]:
        """Get all ticker symbols"""
        return list(self.stocks.keys())

    def update_stock(self, ticker: str, **kwargs) -> bool:
        """Update stock information"""
        ticker = ticker.upper()

        if ticker not in self.stocks:
            return False

        stock = self.stocks[ticker]
        for key, value in kwargs.items():
            if hasattr(stock, key):
                setattr(stock, key, value)

        self._save()
        return True
