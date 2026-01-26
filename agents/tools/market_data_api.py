"""
Market Data API - Real market data fetching tools.

Provides actual market data from Yahoo Finance and other sources.
Eliminates AI hallucination of stock prices and financial data.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import re


@dataclass
class StockQuote:
    """Real-time stock quote data"""
    ticker: str
    price: float
    currency: str
    change: float
    change_percent: float
    volume: int
    market_cap: float
    timestamp: datetime
    source: str

    # Additional data
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'price': self.price,
            'currency': self.currency,
            'change': self.change,
            'change_percent': self.change_percent,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'day_high': self.day_high,
            'day_low': self.day_low,
            'week_52_high': self.week_52_high,
            'week_52_low': self.week_52_low
        }


@dataclass
class FinancialData:
    """Company financial data"""
    ticker: str
    fiscal_year: int

    # Income Statement
    revenue: float
    gross_profit: float
    operating_income: float
    net_income: float
    ebitda: float
    eps: float

    # Balance Sheet
    total_assets: float
    total_liabilities: float
    total_equity: float
    cash: float
    total_debt: float

    # Cash Flow
    operating_cash_flow: float
    capex: float
    free_cash_flow: float

    # Margins (calculated)
    gross_margin: float
    operating_margin: float
    net_margin: float

    # Shares
    shares_outstanding: float

    currency: str
    source: str

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'fiscal_year': self.fiscal_year,
            'revenue': self.revenue,
            'gross_profit': self.gross_profit,
            'operating_income': self.operating_income,
            'net_income': self.net_income,
            'ebitda': self.ebitda,
            'eps': self.eps,
            'total_assets': self.total_assets,
            'total_liabilities': self.total_liabilities,
            'total_equity': self.total_equity,
            'cash': self.cash,
            'total_debt': self.total_debt,
            'operating_cash_flow': self.operating_cash_flow,
            'capex': self.capex,
            'free_cash_flow': self.free_cash_flow,
            'gross_margin': self.gross_margin,
            'operating_margin': self.operating_margin,
            'net_margin': self.net_margin,
            'shares_outstanding': self.shares_outstanding,
            'currency': self.currency,
            'source': self.source
        }


@dataclass
class AnalystEstimates:
    """Analyst consensus data"""
    ticker: str

    # Target prices
    target_low: float
    target_mean: float
    target_high: float
    target_median: float

    # Ratings
    num_analysts: int
    buy_ratings: int
    hold_ratings: int
    sell_ratings: int

    # EPS estimates
    eps_current_year: float
    eps_next_year: float
    eps_growth: float

    # Revenue estimates
    revenue_current_year: float
    revenue_next_year: float
    revenue_growth: float

    currency: str
    source: str
    last_updated: datetime

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'target_low': self.target_low,
            'target_mean': self.target_mean,
            'target_high': self.target_high,
            'target_median': self.target_median,
            'num_analysts': self.num_analysts,
            'buy_ratings': self.buy_ratings,
            'hold_ratings': self.hold_ratings,
            'sell_ratings': self.sell_ratings,
            'eps_current_year': self.eps_current_year,
            'eps_next_year': self.eps_next_year,
            'eps_growth': self.eps_growth,
            'revenue_current_year': self.revenue_current_year,
            'revenue_next_year': self.revenue_next_year,
            'revenue_growth': self.revenue_growth,
            'currency': self.currency,
            'source': self.source,
            'last_updated': self.last_updated.isoformat()
        }


class MarketDataAPI:
    """
    Market Data API wrapper for fetching real financial data.

    Uses Yahoo Finance as primary source with fallback to other APIs.
    All data is REAL, not AI-generated.
    """

    # Ticker format mappings
    EXCHANGE_SUFFIXES = {
        'HK': '.HK',      # Hong Kong
        'US': '',         # US (no suffix for Yahoo)
        'CH': '.SS',      # Shanghai
        'SZ': '.SZ',      # Shenzhen
        'JP': '.T',       # Tokyo
        'UK': '.L',       # London
    }

    CURRENCY_MAP = {
        'HK': 'HKD',
        'US': 'USD',
        'CH': 'CNY',
        'SZ': 'CNY',
        'JP': 'JPY',
        'UK': 'GBP',
    }

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=15)

    def _normalize_ticker(self, ticker: str) -> Tuple[str, str, str]:
        """
        Normalize ticker to Yahoo Finance format.

        Args:
            ticker: Ticker like "6682 HK", "LEGN US", "9660.HK"

        Returns:
            (yahoo_ticker, exchange, currency)
        """
        ticker = ticker.strip().upper()

        # Handle space-separated format: "6682 HK"
        if ' ' in ticker:
            parts = ticker.split()
            if len(parts) == 2:
                symbol, exchange = parts
                suffix = self.EXCHANGE_SUFFIXES.get(exchange, '')
                currency = self.CURRENCY_MAP.get(exchange, 'USD')
                return f"{symbol}{suffix}", exchange, currency

        # Handle dot-separated format: "6682.HK"
        if '.' in ticker:
            parts = ticker.split('.')
            if len(parts) == 2:
                symbol, exchange = parts
                currency = self.CURRENCY_MAP.get(exchange, 'USD')
                return ticker, exchange, currency

        # Assume US stock
        return ticker, 'US', 'USD'

    async def get_quote(self, ticker: str) -> Optional[StockQuote]:
        """
        Get real-time stock quote from Yahoo Finance.

        Args:
            ticker: Stock ticker (e.g., "6682 HK", "AAPL")

        Returns:
            StockQuote with real data or None if failed
        """
        yahoo_ticker, exchange, currency = self._normalize_ticker(ticker)

        # Check cache
        cache_key = f"quote:{yahoo_ticker}"
        if cache_key in self._cache:
            data, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < self._cache_ttl:
                return data

        try:
            import yfinance as yf

            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            if not info or 'regularMarketPrice' not in info:
                return None

            quote = StockQuote(
                ticker=ticker,
                price=info.get('regularMarketPrice', 0),
                currency=info.get('currency', currency),
                change=info.get('regularMarketChange', 0),
                change_percent=info.get('regularMarketChangePercent', 0),
                volume=info.get('regularMarketVolume', 0),
                market_cap=info.get('marketCap', 0),
                timestamp=datetime.now(),
                source='Yahoo Finance',
                day_high=info.get('dayHigh'),
                day_low=info.get('dayLow'),
                week_52_high=info.get('fiftyTwoWeekHigh'),
                week_52_low=info.get('fiftyTwoWeekLow')
            )

            # Cache the result
            self._cache[cache_key] = (quote, datetime.now())

            return quote

        except ImportError:
            # yfinance not installed, try httpx directly
            return await self._get_quote_httpx(yahoo_ticker, ticker, exchange, currency)
        except Exception as e:
            print(f"Error fetching quote for {ticker}: {e}")
            return None

    async def _get_quote_httpx(
        self,
        yahoo_ticker: str,
        original_ticker: str,
        exchange: str,
        currency: str
    ) -> Optional[StockQuote]:
        """Fallback quote fetching using httpx"""
        try:
            import httpx

            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}"
            params = {'interval': '1d', 'range': '1d'}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)

                if response.status_code != 200:
                    return None

                data = response.json()
                result = data.get('chart', {}).get('result', [])

                if not result:
                    return None

                meta = result[0].get('meta', {})

                return StockQuote(
                    ticker=original_ticker,
                    price=meta.get('regularMarketPrice', 0),
                    currency=meta.get('currency', currency),
                    change=0,  # Not available in this endpoint
                    change_percent=0,
                    volume=meta.get('regularMarketVolume', 0),
                    market_cap=0,
                    timestamp=datetime.now(),
                    source='Yahoo Finance API'
                )

        except Exception as e:
            print(f"Error in httpx fallback for {yahoo_ticker}: {e}")
            return None

    async def get_financials(self, ticker: str, years: int = 3) -> List[FinancialData]:
        """
        Get historical financial data.

        Args:
            ticker: Stock ticker
            years: Number of years of history

        Returns:
            List of FinancialData for each fiscal year
        """
        yahoo_ticker, exchange, currency = self._normalize_ticker(ticker)

        try:
            import yfinance as yf

            stock = yf.Ticker(yahoo_ticker)

            # Get financial statements
            income_stmt = stock.income_stmt
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            info = stock.info

            if income_stmt is None or income_stmt.empty:
                return []

            financials = []

            for i, col in enumerate(income_stmt.columns[:years]):
                year = col.year if hasattr(col, 'year') else int(str(col)[:4])

                # Extract income statement data
                revenue = self._safe_get(income_stmt, 'Total Revenue', col, 0)
                gross_profit = self._safe_get(income_stmt, 'Gross Profit', col, 0)
                operating_income = self._safe_get(income_stmt, 'Operating Income', col, 0)
                net_income = self._safe_get(income_stmt, 'Net Income', col, 0)
                ebitda = self._safe_get(income_stmt, 'EBITDA', col, 0)

                # Extract balance sheet data
                total_assets = self._safe_get(balance_sheet, 'Total Assets', col, 0)
                total_liabilities = self._safe_get(balance_sheet, 'Total Liabilities Net Minority Interest', col, 0)
                total_equity = self._safe_get(balance_sheet, 'Total Equity Gross Minority Interest', col, 0)
                cash = self._safe_get(balance_sheet, 'Cash And Cash Equivalents', col, 0)
                total_debt = self._safe_get(balance_sheet, 'Total Debt', col, 0)

                # Extract cash flow data
                operating_cf = self._safe_get(cash_flow, 'Operating Cash Flow', col, 0)
                capex = abs(self._safe_get(cash_flow, 'Capital Expenditure', col, 0))
                fcf = self._safe_get(cash_flow, 'Free Cash Flow', col, operating_cf - capex)

                # Calculate margins
                gross_margin = gross_profit / revenue if revenue else 0
                operating_margin = operating_income / revenue if revenue else 0
                net_margin = net_income / revenue if revenue else 0

                # Get shares outstanding
                shares = info.get('sharesOutstanding', 0)
                eps = net_income / shares if shares else 0

                financials.append(FinancialData(
                    ticker=ticker,
                    fiscal_year=year,
                    revenue=revenue,
                    gross_profit=gross_profit,
                    operating_income=operating_income,
                    net_income=net_income,
                    ebitda=ebitda,
                    eps=eps,
                    total_assets=total_assets,
                    total_liabilities=total_liabilities,
                    total_equity=total_equity,
                    cash=cash,
                    total_debt=total_debt,
                    operating_cash_flow=operating_cf,
                    capex=capex,
                    free_cash_flow=fcf,
                    gross_margin=gross_margin,
                    operating_margin=operating_margin,
                    net_margin=net_margin,
                    shares_outstanding=shares,
                    currency=info.get('currency', currency),
                    source='Yahoo Finance'
                ))

            return financials

        except Exception as e:
            print(f"Error fetching financials for {ticker}: {e}")
            return []

    async def get_analyst_estimates(self, ticker: str) -> Optional[AnalystEstimates]:
        """
        Get analyst consensus estimates.

        Args:
            ticker: Stock ticker

        Returns:
            AnalystEstimates with consensus data
        """
        yahoo_ticker, exchange, currency = self._normalize_ticker(ticker)

        try:
            import yfinance as yf

            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            # Get analyst recommendations
            recommendations = stock.recommendations

            # Count ratings
            buy_count = 0
            hold_count = 0
            sell_count = 0

            if recommendations is not None and not recommendations.empty:
                recent = recommendations.tail(30)  # Last 30 days
                for _, row in recent.iterrows():
                    grade = str(row.get('To Grade', '')).lower()
                    if any(x in grade for x in ['buy', 'outperform', 'overweight']):
                        buy_count += 1
                    elif any(x in grade for x in ['sell', 'underperform', 'underweight']):
                        sell_count += 1
                    else:
                        hold_count += 1

            return AnalystEstimates(
                ticker=ticker,
                target_low=info.get('targetLowPrice', 0),
                target_mean=info.get('targetMeanPrice', 0),
                target_high=info.get('targetHighPrice', 0),
                target_median=info.get('targetMedianPrice', 0),
                num_analysts=info.get('numberOfAnalystOpinions', 0),
                buy_ratings=buy_count,
                hold_ratings=hold_count,
                sell_ratings=sell_count,
                eps_current_year=info.get('forwardEps', 0),
                eps_next_year=0,  # Not directly available
                eps_growth=info.get('earningsGrowth', 0),
                revenue_current_year=info.get('totalRevenue', 0),
                revenue_next_year=0,  # Not directly available
                revenue_growth=info.get('revenueGrowth', 0),
                currency=info.get('currency', currency),
                source='Yahoo Finance',
                last_updated=datetime.now()
            )

        except Exception as e:
            print(f"Error fetching analyst estimates for {ticker}: {e}")
            return None

    async def get_peers(self, ticker: str) -> List[str]:
        """Get list of peer/comparable companies"""
        yahoo_ticker, exchange, currency = self._normalize_ticker(ticker)

        try:
            import yfinance as yf

            stock = yf.Ticker(yahoo_ticker)

            # Try to get from recommendations or industry
            info = stock.info
            industry = info.get('industry', '')
            sector = info.get('sector', '')

            # This is a simplified peer lookup
            # In production, you'd use a more sophisticated industry mapping
            peers = []

            # Return industry/sector for now
            return peers

        except Exception as e:
            print(f"Error fetching peers for {ticker}: {e}")
            return []

    async def verify_price(self, ticker: str, claimed_price: float, tolerance: float = 0.05) -> Dict[str, Any]:
        """
        Verify a claimed price against real market data.

        Args:
            ticker: Stock ticker
            claimed_price: The price to verify
            tolerance: Acceptable deviation (default 5%)

        Returns:
            Verification result with actual price and status
        """
        quote = await self.get_quote(ticker)

        if not quote:
            return {
                'verified': False,
                'reason': 'Could not fetch real-time price',
                'claimed_price': claimed_price,
                'actual_price': None,
                'ticker': ticker
            }

        deviation = abs(quote.price - claimed_price) / quote.price if quote.price else 1

        return {
            'verified': deviation <= tolerance,
            'claimed_price': claimed_price,
            'actual_price': quote.price,
            'deviation': deviation,
            'deviation_pct': f"{deviation:.2%}",
            'currency': quote.currency,
            'ticker': ticker,
            'source': quote.source,
            'timestamp': quote.timestamp.isoformat(),
            'reason': 'Price verified' if deviation <= tolerance else f'Price deviation {deviation:.2%} exceeds tolerance {tolerance:.2%}'
        }

    def _safe_get(self, df, key: str, col, default=0):
        """Safely get value from DataFrame"""
        try:
            if key in df.index:
                val = df.loc[key, col]
                if val is not None and not (isinstance(val, float) and val != val):  # Check for NaN
                    return float(val)
        except:
            pass
        return default


class MultiSourceVerifier:
    """
    Verifies data across multiple sources to ensure accuracy.
    """

    def __init__(self):
        self.primary = MarketDataAPI()

    async def verify_with_multiple_sources(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Verify stock data across multiple sources.

        Returns:
            Aggregated verification result
        """
        results = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'sources': [],
            'consensus_price': None,
            'price_variance': None,
            'is_reliable': False
        }

        # Primary source: Yahoo Finance
        quote = await self.primary.get_quote(ticker)
        if quote:
            results['sources'].append({
                'source': 'Yahoo Finance',
                'price': quote.price,
                'currency': quote.currency,
                'market_cap': quote.market_cap
            })

        # TODO: Add additional sources
        # - Alpha Vantage
        # - IEX Cloud
        # - Polygon.io

        # Calculate consensus
        if results['sources']:
            prices = [s['price'] for s in results['sources'] if s['price']]
            if prices:
                results['consensus_price'] = sum(prices) / len(prices)
                if len(prices) > 1:
                    variance = max(prices) - min(prices)
                    results['price_variance'] = variance / results['consensus_price']
                results['is_reliable'] = True

        return results
