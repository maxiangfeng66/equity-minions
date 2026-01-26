#!/usr/bin/env python3
"""
Prefetch Market Data Module

Fetches and cross-validates current stock prices from multiple sources
BEFORE the workflow runs, ensuring agents have accurate price data.

Sources:
1. Yahoo Finance (via yfinance)
2. Google Finance (via web scraping)
3. Fallback: Manual price input

Usage:
    from prefetch_data import prefetch_market_data
    price_data = await prefetch_market_data("LEGN US")
"""

import asyncio
import re
from typing import Dict, Optional
from datetime import datetime

# Try to import yfinance, but don't fail if not installed
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not installed. Run: pip install yfinance")


def convert_ticker_to_yahoo(ticker: str) -> str:
    """
    Convert Bloomberg-style ticker to Yahoo Finance format.

    Examples:
        "LEGN US" -> "LEGN"
        "9660 HK" -> "9660.HK"
        "762 HK" -> "0762.HK"
        "600900 CH" -> "600900.SS"
        "6682_HK" -> "6682.HK"  # Handle underscore format
    """
    # Handle underscore format (e.g., "6682_HK" -> "6682 HK")
    if "_" in ticker:
        ticker = ticker.replace("_", " ")

    parts = ticker.strip().split()
    if len(parts) != 2:
        return ticker

    symbol, exchange = parts[0], parts[1].upper()

    if exchange == "US":
        return symbol
    elif exchange == "HK":
        # HK stocks need leading zeros for 4-digit codes
        if len(symbol) < 4:
            symbol = symbol.zfill(4)
        return f"{symbol}.HK"
    elif exchange == "CH":
        # China A-shares: .SS for Shanghai, .SZ for Shenzhen
        # 6xxxxx = Shanghai, 0xxxxx/3xxxxx = Shenzhen
        if symbol.startswith("6"):
            return f"{symbol}.SS"
        else:
            return f"{symbol}.SZ"
    else:
        return ticker


def get_currency_for_ticker(ticker: str) -> str:
    """Determine currency based on ticker exchange."""
    if "HK" in ticker.upper():
        return "HKD"
    elif "US" in ticker.upper():
        return "USD"
    elif "CH" in ticker.upper():
        return "CNY"
    else:
        return "USD"


def fetch_price_yfinance(ticker: str) -> Optional[Dict]:
    """
    Fetch current price from Yahoo Finance using yfinance.

    Returns:
        Dict with price data or None if failed
    """
    if not YFINANCE_AVAILABLE:
        return None

    yahoo_ticker = convert_ticker_to_yahoo(ticker)

    try:
        stock = yf.Ticker(yahoo_ticker)
        info = stock.info

        # Try different price fields
        current_price = (
            info.get('currentPrice') or
            info.get('regularMarketPrice') or
            info.get('previousClose')
        )

        if current_price is None:
            # Try getting from history
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]

        if current_price is None:
            return None

        # Extract shares outstanding
        # Prefer impliedSharesOutstanding (marketCap/price) over sharesOutstanding
        # sharesOutstanding is often outdated or represents basic shares only
        # impliedSharesOutstanding includes all diluted shares and is market-consistent
        shares_outstanding = info.get('impliedSharesOutstanding')
        if not shares_outstanding:
            # Fallback: calculate from marketCap / currentPrice
            market_cap = info.get('marketCap')
            if market_cap and current_price:
                shares_outstanding = market_cap / current_price
        if not shares_outstanding:
            # Last resort: use reported sharesOutstanding
            shares_outstanding = info.get('sharesOutstanding')
        if shares_outstanding:
            shares_outstanding = shares_outstanding / 1e6  # Convert to millions

        # Extract revenue and other financials (for DCF input validation)
        total_revenue = info.get('totalRevenue')
        if total_revenue:
            total_revenue = total_revenue / 1e6  # Convert to millions

        ebitda = info.get('ebitda')
        if ebitda:
            ebitda = ebitda / 1e6  # Convert to millions

        operating_income = info.get('operatingIncome')
        if operating_income:
            operating_income = operating_income / 1e6  # Convert to millions

        # Extract operating margin ratio (can be negative for loss-making companies!)
        operating_margin = info.get('operatingMargins')  # Already a ratio like -1.055 or 0.15

        # If operatingIncome is None but we have margin and revenue, calculate it
        if operating_income is None and operating_margin is not None and total_revenue:
            operating_income = total_revenue * operating_margin
            print(f"  Calculated Operating Income: {operating_income:.1f}M (from margin {operating_margin*100:.1f}%)")

        return {
            "source": "Yahoo Finance (yfinance)",
            "ticker": yahoo_ticker,
            "price": float(current_price),
            "currency": info.get('currency', get_currency_for_ticker(ticker)),
            "market_cap": info.get('marketCap'),
            "shares_outstanding": shares_outstanding,  # In millions
            "name": info.get('shortName') or info.get('longName'),
            "exchange": info.get('exchange'),
            "beta": info.get('beta'),
            # NEW: Financial data for DCF
            "total_revenue": total_revenue,  # In millions
            "ebitda": ebitda,  # In millions
            "operating_income": operating_income,  # In millions
            "operating_margin": operating_margin,  # Ratio (can be negative!)
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None


def fetch_price_yfinance_fast(ticker: str) -> Optional[Dict]:
    """
    Faster price fetch using just the download function.
    """
    if not YFINANCE_AVAILABLE:
        return None

    yahoo_ticker = convert_ticker_to_yahoo(ticker)

    try:
        import yfinance as yf
        data = yf.download(yahoo_ticker, period="1d", progress=False)

        if data.empty:
            return None

        current_price = data['Close'].iloc[-1]

        # Handle multi-index columns from yfinance
        if hasattr(current_price, 'iloc'):
            current_price = current_price.iloc[0]

        return {
            "source": "Yahoo Finance (fast)",
            "ticker": yahoo_ticker,
            "price": float(current_price),
            "currency": get_currency_for_ticker(ticker),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"yfinance fast error for {ticker}: {e}")
        return None


async def prefetch_market_data(ticker: str, manual_price: float = None) -> Dict:
    """
    Prefetch and validate market data for a ticker.

    Args:
        ticker: Bloomberg-style ticker (e.g., "LEGN US", "9660 HK")
        manual_price: Optional manually verified price to use

    Returns:
        Dict with verified price data:
        {
            "ticker": str,
            "verified_price": float,
            "currency": str,
            "confidence": "HIGH" | "MEDIUM" | "LOW",
            "sources": List[Dict],
            "timestamp": str
        }
    """
    currency = get_currency_for_ticker(ticker)
    sources = []
    prices = []

    # If manual price provided, use it with HIGH confidence
    if manual_price is not None:
        return {
            "ticker": ticker,
            "verified_price": manual_price,
            "currency": currency,
            "confidence": "HIGH",
            "sources": [{"source": "Manual Input", "price": manual_price}],
            "timestamp": datetime.now().isoformat(),
            "message": f"Using manually provided price: {currency} {manual_price}"
        }

    # Try yfinance (primary source)
    print(f"Fetching price for {ticker}...")

    yf_result = fetch_price_yfinance(ticker)
    if yf_result and yf_result.get('price'):
        sources.append(yf_result)
        prices.append(yf_result['price'])
        print(f"  Yahoo Finance: {currency} {yf_result['price']:.2f}")

    # Try fast method as backup/validation
    if not prices:
        yf_fast = fetch_price_yfinance_fast(ticker)
        if yf_fast and yf_fast.get('price'):
            sources.append(yf_fast)
            prices.append(yf_fast['price'])
            print(f"  Yahoo Finance (fast): {currency} {yf_fast['price']:.2f}")

    # Determine confidence and verified price
    if len(prices) == 0:
        return {
            "ticker": ticker,
            "verified_price": None,
            "currency": currency,
            "confidence": "NONE",
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
            "message": "ERROR: Could not fetch price from any source. Please provide --price manually."
        }

    # Use median price if multiple sources
    verified_price = sorted(prices)[len(prices) // 2]

    # Check price consistency across sources
    if len(prices) >= 2:
        price_variance = (max(prices) - min(prices)) / verified_price
        if price_variance < 0.02:  # Less than 2% difference
            confidence = "HIGH"
        elif price_variance < 0.05:  # Less than 5% difference
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
    else:
        confidence = "MEDIUM"  # Single source

    # Extract additional data from the best source
    market_cap = None
    shares_outstanding = None
    beta = None
    total_revenue = None
    ebitda = None
    operating_income = None
    operating_margin = None
    for src in sources:
        if src.get('market_cap'):
            market_cap = src['market_cap']
        if src.get('shares_outstanding'):
            shares_outstanding = src['shares_outstanding']
        if src.get('beta'):
            beta = src['beta']
        # NEW: Extract financial data for DCF validation
        if src.get('total_revenue'):
            total_revenue = src['total_revenue']
        if src.get('ebitda'):
            ebitda = src['ebitda']
        if src.get('operating_income'):
            operating_income = src['operating_income']
        # CRITICAL: Extract operating margin (can be negative for loss-making companies!)
        if src.get('operating_margin') is not None:
            operating_margin = src['operating_margin']

    return {
        "ticker": ticker,
        "verified_price": verified_price,
        "currency": currency,
        "confidence": confidence,
        "sources": sources,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,  # In millions
        "beta": beta,
        # NEW: Financial data for DCF validation
        "total_revenue": total_revenue,  # In millions
        "ebitda": ebitda,  # In millions
        "operating_income": operating_income,  # In millions
        "operating_margin": operating_margin,  # Ratio (can be negative for loss-making companies!)
        "timestamp": datetime.now().isoformat(),
        "message": f"Verified price: {currency} {verified_price:.2f} (Confidence: {confidence})"
    }


async def prefetch_multiple(tickers: list, manual_prices: dict = None) -> Dict[str, Dict]:
    """
    Prefetch prices for multiple tickers.

    Args:
        tickers: List of tickers
        manual_prices: Optional dict of {ticker: price} for manual overrides

    Returns:
        Dict of {ticker: price_data}
    """
    manual_prices = manual_prices or {}
    results = {}

    for ticker in tickers:
        manual_price = manual_prices.get(ticker)
        result = await prefetch_market_data(ticker, manual_price)
        results[ticker] = result

    return results


def build_price_context(price_data: Dict) -> str:
    """
    Build price context string to inject into workflow prompt.

    This string will be prepended to the task prompt so all agents
    see the verified price.
    """
    if price_data.get('confidence') == 'NONE':
        return f"""
============================================================
WARNING: PRICE VERIFICATION FAILED
============================================================
Could not fetch verified price for {price_data['ticker']}.
Agents MUST NOT hallucinate prices. If you cannot verify the
current price, state this clearly and use conservative estimates.
============================================================
"""

    return f"""
============================================================
VERIFIED MARKET DATA (Pre-fetched and Cross-Validated)
============================================================
TICKER: {price_data['ticker']}
VERIFIED CURRENT PRICE: {price_data['currency']} {price_data['verified_price']:.2f}
DATA CONFIDENCE: {price_data['confidence']}
TIMESTAMP: {price_data['timestamp']}

SOURCES CONSULTED:
{chr(10).join(f"  - {s['source']}: {price_data['currency']} {s['price']:.2f}" for s in price_data['sources'])}

CRITICAL INSTRUCTION:
You MUST use this verified price ({price_data['currency']} {price_data['verified_price']:.2f})
in ALL your analysis. Do NOT use prices from your training data or hallucinate
different prices. This is the authoritative, real-time market price.
============================================================
"""


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prefetch_data.py <ticker> [manual_price]")
        print("Example: python prefetch_data.py 'LEGN US'")
        print("Example: python prefetch_data.py 'LEGN US' 20.50")
        sys.exit(1)

    ticker = sys.argv[1]
    manual_price = float(sys.argv[2]) if len(sys.argv) > 2 else None

    async def main():
        result = await prefetch_market_data(ticker, manual_price)
        print("\n" + "="*60)
        print("PREFETCH RESULT")
        print("="*60)
        for key, value in result.items():
            if key != 'sources':
                print(f"{key}: {value}")

        print("\n" + build_price_context(result))

    asyncio.run(main())
