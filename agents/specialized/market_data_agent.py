"""
Market Data Agent - Fetches and validates real market data.

This agent uses actual APIs to fetch market data, eliminating
the risk of AI hallucinating stock prices and financial figures.
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from ..core.spawnable_agent import SpawnableAgent
from ..tools.market_data_api import MarketDataAPI, StockQuote, FinancialData, AnalystEstimates


@dataclass
class MarketDataPackage:
    """Complete market data package for a stock"""
    ticker: str
    fetched_at: datetime

    # Quote data
    quote: Optional[StockQuote] = None

    # Financial data (3 years)
    financials: List[FinancialData] = None

    # Analyst estimates
    estimates: Optional[AnalystEstimates] = None

    # Verification
    is_verified: bool = False
    verification_errors: List[str] = None

    def __post_init__(self):
        if self.financials is None:
            self.financials = []
        if self.verification_errors is None:
            self.verification_errors = []

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'fetched_at': self.fetched_at.isoformat(),
            'quote': self.quote.to_dict() if self.quote else None,
            'financials': [f.to_dict() for f in self.financials],
            'estimates': self.estimates.to_dict() if self.estimates else None,
            'is_verified': self.is_verified,
            'verification_errors': self.verification_errors
        }


class MarketDataAgent(SpawnableAgent):
    """
    Market Data Agent - Reliable market data fetching.

    This agent:
    1. Fetches real-time stock quotes from Yahoo Finance
    2. Gets historical financial data
    3. Retrieves analyst estimates
    4. Validates data consistency
    5. Provides formatted output for other agents

    All data is REAL, fetched from APIs, not AI-generated.
    """

    def __init__(
        self,
        name: str = "MarketDataAgent",
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="Market Data Collector",
            tier=1,
            parent=parent_agent
        )

        self.api = MarketDataAPI()

    async def fetch_complete_data(self, ticker: str) -> MarketDataPackage:
        """
        Fetch complete market data package for a ticker.

        Args:
            ticker: Stock ticker (e.g., "6682 HK", "AAPL")

        Returns:
            MarketDataPackage with all available data
        """
        package = MarketDataPackage(
            ticker=ticker,
            fetched_at=datetime.now()
        )

        # Fetch quote
        try:
            package.quote = await self.api.get_quote(ticker)
            if package.quote:
                package.is_verified = True
        except Exception as e:
            package.verification_errors.append(f"Quote fetch failed: {e}")

        # Fetch financials
        try:
            package.financials = await self.api.get_financials(ticker, years=3)
        except Exception as e:
            package.verification_errors.append(f"Financials fetch failed: {e}")

        # Fetch analyst estimates
        try:
            package.estimates = await self.api.get_analyst_estimates(ticker)
        except Exception as e:
            package.verification_errors.append(f"Estimates fetch failed: {e}")

        # Validate consistency
        if package.quote and package.financials:
            # Check market cap consistency
            if package.financials[0].shares_outstanding > 0:
                calculated_mcap = package.quote.price * package.financials[0].shares_outstanding
                reported_mcap = package.quote.market_cap

                if reported_mcap > 0:
                    deviation = abs(calculated_mcap - reported_mcap) / reported_mcap
                    if deviation > 0.1:
                        package.verification_errors.append(
                            f"Market cap inconsistency: calculated {calculated_mcap:,.0f} vs reported {reported_mcap:,.0f}"
                        )

        return package

    async def verify_price(
        self,
        ticker: str,
        claimed_price: float
    ) -> Dict[str, Any]:
        """
        Verify a claimed price against real market data.

        Args:
            ticker: Stock ticker
            claimed_price: Price to verify

        Returns:
            Verification result
        """
        return await self.api.verify_price(ticker, claimed_price)

    async def fetch_for_workflow(self, ticker: str) -> str:
        """
        Fetch data and format for workflow injection.

        Returns formatted string that can be injected at workflow START.
        """
        package = await self.fetch_complete_data(ticker)

        if not package.quote:
            return f"""
============================================
MARKET DATA FETCH FAILED
============================================
Ticker: {ticker}
Error: Could not fetch market data
Errors: {', '.join(package.verification_errors)}
============================================
"""

        output = f"""
============================================
VERIFIED MARKET DATA - {ticker}
============================================
FETCHED AT: {package.fetched_at.isoformat()}
SOURCE: Yahoo Finance (Real-time API)

VERIFIED CURRENT PRICE: {package.quote.currency} {package.quote.price:.2f}

Quote Details:
  - Price: {package.quote.currency} {package.quote.price:.2f}
  - Change: {package.quote.change:+.2f} ({package.quote.change_percent:+.2f}%)
  - Volume: {package.quote.volume:,}
  - Market Cap: {package.quote.currency} {package.quote.market_cap:,.0f}
  - Day Range: {package.quote.day_low:.2f} - {package.quote.day_high:.2f}
  - 52-Week Range: {package.quote.week_52_low:.2f} - {package.quote.week_52_high:.2f}

THIS PRICE IS VERIFIED AND MUST BE USED BY ALL AGENTS.
DO NOT USE ANY OTHER PRICE.
============================================
"""

        if package.financials:
            latest = package.financials[0]
            output += f"""
LATEST FINANCIALS (FY{latest.fiscal_year}):
  - Revenue: {latest.currency} {latest.revenue:,.0f}
  - Gross Margin: {latest.gross_margin:.1%}
  - Operating Margin: {latest.operating_margin:.1%}
  - Net Margin: {latest.net_margin:.1%}
  - EPS: {latest.currency} {latest.eps:.2f}
  - Free Cash Flow: {latest.currency} {latest.free_cash_flow:,.0f}
"""

        if package.estimates:
            output += f"""
ANALYST CONSENSUS:
  - Target Low: {package.estimates.currency} {package.estimates.target_low:.2f}
  - Target Mean: {package.estimates.currency} {package.estimates.target_mean:.2f}
  - Target High: {package.estimates.currency} {package.estimates.target_high:.2f}
  - Analysts: {package.estimates.num_analysts}
  - Buy: {package.estimates.buy_ratings}, Hold: {package.estimates.hold_ratings}, Sell: {package.estimates.sell_ratings}
"""

        output += f"""
============================================
DATA VERIFICATION: {'VERIFIED' if package.is_verified else 'ISSUES FOUND'}
"""

        if package.verification_errors:
            output += f"Issues: {'; '.join(package.verification_errors)}\n"

        output += "============================================\n"

        return output

    async def batch_fetch(self, tickers: List[str]) -> Dict[str, MarketDataPackage]:
        """
        Fetch data for multiple tickers in parallel.

        Args:
            tickers: List of stock tickers

        Returns:
            Dict mapping ticker to MarketDataPackage
        """
        tasks = [self.fetch_complete_data(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            ticker: result if not isinstance(result, Exception) else MarketDataPackage(
                ticker=ticker,
                fetched_at=datetime.now(),
                verification_errors=[str(result)]
            )
            for ticker, result in zip(tickers, results)
        }
