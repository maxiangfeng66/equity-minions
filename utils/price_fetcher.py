"""
Multi-Source Price Fetcher with Cross-Validation
Fetches equity prices from multiple sources and cross-validates for accuracy
"""

import asyncio
import httpx
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PriceData:
    """Price data from a single source"""
    source: str
    price: float
    currency: str
    timestamp: str
    market_cap: Optional[float] = None
    volume: Optional[float] = None
    change_pct: Optional[float] = None


@dataclass
class ValidatedPrice:
    """Cross-validated price result"""
    ticker: str
    company: str
    verified_price: float
    currency: str
    market_cap: Optional[float]
    sources: List[PriceData]
    confidence: str  # HIGH, MEDIUM, LOW
    max_deviation: float  # Max % deviation between sources
    timestamp: str


class MultiSourcePriceFetcher:
    """Fetches and cross-validates prices from multiple sources"""

    # Data sources to query
    SOURCES = [
        "stockanalysis.com",
        "investing.com",
        "yahoo.finance",
        "google.finance",
        "bloomberg.com"
    ]

    def __init__(self, search_function):
        """
        Args:
            search_function: Async function that performs web search
                             Returns search results with price data
        """
        self.search = search_function

    async def fetch_price(self, ticker: str, company_name: str = "") -> ValidatedPrice:
        """
        Fetch price from multiple sources and cross-validate

        Args:
            ticker: Stock ticker (e.g., "6682 HK", "AAPL")
            company_name: Company name for additional context

        Returns:
            ValidatedPrice with cross-validated price and confidence level
        """
        # Normalize ticker format
        ticker_clean = ticker.replace(" ", ".").upper()
        if "HK" in ticker.upper():
            ticker_clean = ticker.replace(" ", ".").replace("HK", "HK")

        # Search for price from multiple sources
        prices = []

        # Query 1: Direct stock price search
        query1 = f"{ticker} stock price today"
        result1 = await self._search_and_extract(query1, ticker)
        if result1:
            prices.extend(result1)

        # Query 2: With company name
        if company_name:
            query2 = f"{company_name} {ticker} current price HKD"
            result2 = await self._search_and_extract(query2, ticker)
            if result2:
                prices.extend(result2)

        # Query 3: Financial data sites
        query3 = f"site:stockanalysis.com OR site:investing.com {ticker} price"
        result3 = await self._search_and_extract(query3, ticker)
        if result3:
            prices.extend(result3)

        # Validate and aggregate prices
        return self._validate_prices(ticker, company_name, prices)

    async def _search_and_extract(self, query: str, ticker: str) -> List[PriceData]:
        """Search and extract price data from results"""
        try:
            results = await self.search(query)
            return self._extract_prices_from_results(results, ticker)
        except Exception as e:
            print(f"Search error for '{query}': {e}")
            return []

    def _extract_prices_from_results(self, results: str, ticker: str) -> List[PriceData]:
        """Extract price data from search results text"""
        prices = []

        # Pattern to match price mentions
        # Matches: HKD 52.30, $52.30, 52.30 HKD, etc.
        price_patterns = [
            r'(?:HKD|HK\$)\s*(\d+\.?\d*)',  # HKD 52.30
            r'(\d+\.?\d*)\s*(?:HKD|HK\$)',  # 52.30 HKD
            r'price[:\s]+(?:HKD|HK\$)?\s*(\d+\.?\d*)',  # price: 52.30
            r'current[:\s]+(?:HKD|HK\$)?\s*(\d+\.?\d*)',  # current: 52.30
            r'\$(\d+\.?\d*)\s*(?:USD)?',  # $52.30
        ]

        # Determine currency from ticker
        currency = "HKD" if "HK" in ticker.upper() else "USD"

        for pattern in price_patterns:
            matches = re.findall(pattern, results, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match)
                    # Sanity check - ignore unreasonable prices
                    if 0.01 < price < 10000:
                        prices.append(PriceData(
                            source="web_search",
                            price=price,
                            currency=currency,
                            timestamp=datetime.now().isoformat()
                        ))
                except ValueError:
                    continue

        return prices

    def _validate_prices(self, ticker: str, company: str,
                         prices: List[PriceData]) -> ValidatedPrice:
        """Cross-validate prices and determine confidence"""

        if not prices:
            return ValidatedPrice(
                ticker=ticker,
                company=company,
                verified_price=0.0,
                currency="HKD" if "HK" in ticker.upper() else "USD",
                market_cap=None,
                sources=[],
                confidence="FAILED",
                max_deviation=0.0,
                timestamp=datetime.now().isoformat()
            )

        # Get unique prices and their counts
        price_counts = {}
        for p in prices:
            key = round(p.price, 2)
            price_counts[key] = price_counts.get(key, 0) + 1

        # Find most common price (mode)
        sorted_prices = sorted(price_counts.items(), key=lambda x: -x[1])
        verified_price = sorted_prices[0][0]

        # Calculate max deviation
        all_prices = [p.price for p in prices]
        if len(all_prices) > 1:
            max_dev = max(abs(p - verified_price) / verified_price * 100
                         for p in all_prices)
        else:
            max_dev = 0.0

        # Determine confidence
        if len(prices) >= 3 and max_dev < 2.0:
            confidence = "HIGH"
        elif len(prices) >= 2 and max_dev < 5.0:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return ValidatedPrice(
            ticker=ticker,
            company=company,
            verified_price=verified_price,
            currency=prices[0].currency if prices else "HKD",
            market_cap=None,  # Would need separate fetch
            sources=prices,
            confidence=confidence,
            max_deviation=max_dev,
            timestamp=datetime.now().isoformat()
        )


async def fetch_equity_price(ticker: str, company_name: str = "") -> Dict:
    """
    Convenience function to fetch and validate equity price
    Uses web search for data

    Returns:
        dict with verified_price, confidence, sources, etc.
    """
    # For now, return placeholder - integration with actual search needed
    from dataclasses import asdict

    # This would be integrated with actual web search
    # For demo, return structure
    return {
        "ticker": ticker,
        "company": company_name,
        "verified_price": 0.0,
        "currency": "HKD" if "HK" in ticker.upper() else "USD",
        "confidence": "PENDING",
        "sources": [],
        "instructions": "Integrate with web search API for live data"
    }


if __name__ == "__main__":
    # Test the fetcher
    import asyncio

    async def test():
        result = await fetch_equity_price("6682 HK", "Fourth Paradigm")
        print(result)

    asyncio.run(test())
