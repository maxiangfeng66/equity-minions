"""
Multi-Source Shares Outstanding Validator

This module fetches shares outstanding from multiple sources and cross-validates
to ensure data accuracy. Never rely on a single source alone.

Sources:
1. Manual override from context/research files (highest priority)
2. Yahoo Finance via yfinance
3. Calculated from market_cap / price (if both verified)
4. Exchange data (if available)

Validation:
- Flags discrepancies > 10% between sources
- Returns most reliable value with source tracking
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class SharesDataPoint:
    """A single data point for shares outstanding"""
    value: float  # in millions
    source: str
    timestamp: str
    confidence: float  # 0.0-1.0
    raw_value: float = 0  # original value before conversion


@dataclass
class SharesValidationResult:
    """Result of multi-source shares validation"""
    recommended_value: float  # in millions
    recommended_source: str
    confidence: float
    all_sources: List[SharesDataPoint]
    discrepancy_detected: bool
    discrepancy_pct: float
    warnings: List[str]

    def as_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'recommended_value': self.recommended_value,
            'recommended_source': self.recommended_source,
            'confidence': self.confidence,
            'all_sources': [
                {
                    'value': dp.value,
                    'source': dp.source,
                    'timestamp': dp.timestamp,
                    'confidence': dp.confidence
                }
                for dp in self.all_sources
            ],
            'discrepancy_detected': self.discrepancy_detected,
            'discrepancy_pct': self.discrepancy_pct,
            'warnings': self.warnings
        }


class SharesOutstandingValidator:
    """
    Multi-source validator for shares outstanding data.

    Priority order:
    1. Manual override from context files (user-verified)
    2. Exchange filings / regulatory data
    3. Cross-validated Yahoo Finance
    4. Calculated from market cap
    """

    DISCREPANCY_THRESHOLD = 0.10  # 10% threshold for flagging

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.context_dir = self.project_root / "context"

    def validate_shares(
        self,
        ticker: str,
        verified_price: float = None,
        verified_market_cap: float = None
    ) -> SharesValidationResult:
        """
        Validate shares outstanding from multiple sources.

        Args:
            ticker: Stock ticker (e.g., "6682_HK", "AAPL")
            verified_price: User-verified current price
            verified_market_cap: User-verified market cap (in millions)

        Returns:
            SharesValidationResult with recommended value and all sources
        """
        sources: List[SharesDataPoint] = []
        warnings: List[str] = []

        # Normalize ticker
        ticker_clean = ticker.replace(" ", "_").replace(".", "_")

        # Source 1: Check for manual override in context files (HIGHEST PRIORITY)
        manual_shares = self._get_manual_override(ticker_clean)
        if manual_shares:
            sources.append(manual_shares)
            print(f"[SharesValidator] Found manual override: {manual_shares.value:.2f}M")

        # Source 2: Yahoo Finance
        yf_shares = self._get_yahoo_finance(ticker)
        if yf_shares:
            sources.append(yf_shares)
            print(f"[SharesValidator] Yahoo Finance: {yf_shares.value:.2f}M")

        # Source 3: Calculate from market cap / price (if we have verified values)
        if verified_price and verified_market_cap:
            calc_shares = verified_market_cap / verified_price
            sources.append(SharesDataPoint(
                value=calc_shares,
                source="Calculated (MarketCap/Price)",
                timestamp=datetime.now().isoformat(),
                confidence=0.8,  # High if inputs are verified
                raw_value=calc_shares
            ))
            print(f"[SharesValidator] Calculated: {calc_shares:.2f}M")

        # Source 4: Get from yfinance implied shares (different field)
        yf_implied = self._get_yahoo_implied_shares(ticker)
        if yf_implied and yf_implied.value != (yf_shares.value if yf_shares else 0):
            sources.append(yf_implied)
            print(f"[SharesValidator] Yahoo Implied: {yf_implied.value:.2f}M")

        # Validate and select best value
        if not sources:
            warnings.append("CRITICAL: No shares outstanding data available from any source")
            return SharesValidationResult(
                recommended_value=0,
                recommended_source="None",
                confidence=0,
                all_sources=[],
                discrepancy_detected=False,
                discrepancy_pct=0,
                warnings=warnings
            )

        # Check for discrepancies
        discrepancy_detected, discrepancy_pct = self._check_discrepancy(sources)

        if discrepancy_detected:
            warnings.append(
                f"WARNING: Shares outstanding discrepancy detected! "
                f"Sources differ by {discrepancy_pct:.1%}. "
                f"Values: {', '.join([f'{s.source}: {s.value:.2f}M' for s in sources])}"
            )
            print(f"[SharesValidator] DISCREPANCY DETECTED: {discrepancy_pct:.1%}")

        # Select best value (highest confidence, prefer manual override)
        best = self._select_best_source(sources)

        return SharesValidationResult(
            recommended_value=best.value,
            recommended_source=best.source,
            confidence=best.confidence,
            all_sources=sources,
            discrepancy_detected=discrepancy_detected,
            discrepancy_pct=discrepancy_pct,
            warnings=warnings
        )

    def _get_manual_override(self, ticker: str) -> Optional[SharesDataPoint]:
        """Check context files for manual shares override"""

        # Check multiple possible file locations
        possible_files = [
            self.context_dir / f"{ticker}_context.json",
            self.context_dir / f"{ticker}.json",
            self.context_dir / f"{ticker}_research.json",
            self.context_dir / f"{ticker}_fundamental.json",
        ]

        # Also check company-named files
        for f in self.context_dir.glob(f"{ticker}*.json"):
            if f not in possible_files:
                possible_files.append(f)

        for filepath in possible_files:
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Check various locations for shares data
                    shares = None
                    source_detail = ""

                    # Check fundamental_data section
                    if 'fundamental_data' in data:
                        fd = data['fundamental_data']
                        shares = fd.get('shares_outstanding') or fd.get('shares_outstanding_millions')
                        source_detail = "fundamental_data"

                    # Check market_data section
                    if not shares and 'market_data' in data:
                        md = data['market_data']
                        shares = md.get('shares_outstanding') or md.get('shares_outstanding_millions')
                        source_detail = "market_data"

                    # Check top-level
                    if not shares:
                        shares = data.get('shares_outstanding') or data.get('shares_outstanding_millions')
                        source_detail = "top-level"

                    # Check verified_shares field
                    if not shares:
                        shares = data.get('verified_shares_outstanding')
                        source_detail = "verified_shares"

                    if shares:
                        return SharesDataPoint(
                            value=float(shares),
                            source=f"Manual Override ({filepath.name}/{source_detail})",
                            timestamp=data.get('last_updated', datetime.now().isoformat()),
                            confidence=0.95,  # Highest confidence for manual override
                            raw_value=float(shares)
                        )

                except Exception as e:
                    print(f"[SharesValidator] Error reading {filepath}: {e}")

        return None

    def _get_yahoo_finance(self, ticker: str) -> Optional[SharesDataPoint]:
        """Get shares outstanding from Yahoo Finance"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            # Convert ticker format
            yahoo_ticker = self._convert_to_yahoo_ticker(ticker)
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            shares = info.get('sharesOutstanding')
            if shares:
                shares_millions = shares / 1e6
                return SharesDataPoint(
                    value=shares_millions,
                    source="Yahoo Finance (sharesOutstanding)",
                    timestamp=datetime.now().isoformat(),
                    confidence=0.7,  # Medium confidence
                    raw_value=shares
                )
        except Exception as e:
            print(f"[SharesValidator] Yahoo Finance error: {e}")

        return None

    def _get_yahoo_implied_shares(self, ticker: str) -> Optional[SharesDataPoint]:
        """Get implied shares from Yahoo Finance (marketCap / price)"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            yahoo_ticker = self._convert_to_yahoo_ticker(ticker)
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            implied = info.get('impliedSharesOutstanding')
            if implied:
                implied_millions = implied / 1e6
                return SharesDataPoint(
                    value=implied_millions,
                    source="Yahoo Finance (impliedSharesOutstanding)",
                    timestamp=datetime.now().isoformat(),
                    confidence=0.75,  # Slightly higher - market consistent
                    raw_value=implied
                )

            # Calculate from market cap if implied not available
            market_cap = info.get('marketCap')
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if market_cap and price:
                calc_shares = (market_cap / price) / 1e6
                return SharesDataPoint(
                    value=calc_shares,
                    source="Yahoo Finance (MarketCap/Price)",
                    timestamp=datetime.now().isoformat(),
                    confidence=0.7,
                    raw_value=market_cap / price
                )

        except Exception as e:
            print(f"[SharesValidator] Yahoo implied shares error: {e}")

        return None

    def _convert_to_yahoo_ticker(self, ticker: str) -> str:
        """Convert internal ticker format to Yahoo Finance format"""
        ticker = ticker.replace("_", " ")

        if " HK" in ticker.upper():
            num = ticker.upper().replace(" HK", "").replace("_HK", "")
            return f"{num.zfill(4)}.HK"
        elif " US" in ticker.upper():
            return ticker.upper().replace(" US", "").replace("_US", "")
        elif " CH" in ticker.upper() or " SS" in ticker.upper():
            num = ticker.upper().replace(" CH", "").replace("_CH", "").replace(" SS", "").replace("_SS", "")
            return f"{num}.SS"

        return ticker

    def _check_discrepancy(self, sources: List[SharesDataPoint]) -> Tuple[bool, float]:
        """Check if there's a significant discrepancy between sources"""
        if len(sources) < 2:
            return False, 0.0

        values = [s.value for s in sources if s.value > 0]
        if len(values) < 2:
            return False, 0.0

        min_val = min(values)
        max_val = max(values)

        if min_val == 0:
            return True, 1.0  # 100% discrepancy if one is zero

        discrepancy = (max_val - min_val) / min_val
        return discrepancy > self.DISCREPANCY_THRESHOLD, discrepancy

    def _select_best_source(self, sources: List[SharesDataPoint]) -> SharesDataPoint:
        """Select the best source based on confidence and priority"""
        # Sort by confidence (descending)
        sorted_sources = sorted(sources, key=lambda x: x.confidence, reverse=True)
        return sorted_sources[0]

    def add_manual_override(
        self,
        ticker: str,
        shares_outstanding: float,
        source_description: str = "User verified"
    ):
        """
        Add a manual override for shares outstanding.

        Args:
            ticker: Stock ticker
            shares_outstanding: Shares in millions
            source_description: Description of source
        """
        ticker_clean = ticker.replace(" ", "_").replace(".", "_")
        context_file = self.context_dir / f"{ticker_clean}_context.json"

        # Load existing or create new
        data = {}
        if context_file.exists():
            with open(context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # Add/update fundamental_data section
        if 'fundamental_data' not in data:
            data['fundamental_data'] = {}

        data['fundamental_data']['shares_outstanding'] = shares_outstanding
        data['fundamental_data']['shares_outstanding_source'] = source_description
        data['fundamental_data']['shares_outstanding_updated'] = datetime.now().isoformat()

        # Also add top-level for easy access
        data['verified_shares_outstanding'] = shares_outstanding

        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[SharesValidator] Added manual override: {ticker} = {shares_outstanding}M shares")


def validate_shares_outstanding(
    ticker: str,
    verified_price: float = None,
    verified_market_cap: float = None,
    project_root: str = None
) -> SharesValidationResult:
    """
    Convenience function to validate shares outstanding.

    Args:
        ticker: Stock ticker
        verified_price: User-verified price
        verified_market_cap: User-verified market cap (millions)
        project_root: Project root directory

    Returns:
        SharesValidationResult
    """
    validator = SharesOutstandingValidator(project_root)
    return validator.validate_shares(ticker, verified_price, verified_market_cap)


def set_manual_shares(
    ticker: str,
    shares_millions: float,
    source: str = "User verified",
    project_root: str = None
):
    """
    Set manual override for shares outstanding.

    Args:
        ticker: Stock ticker
        shares_millions: Shares outstanding in millions
        source: Source description
        project_root: Project root directory
    """
    validator = SharesOutstandingValidator(project_root)
    validator.add_manual_override(ticker, shares_millions, source)


# CLI testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python shares_validator.py <ticker> [--set <shares_millions>]")
        print("Example: python shares_validator.py 6682_HK")
        print("Example: python shares_validator.py 6682_HK --set 320")
        sys.exit(1)

    ticker = sys.argv[1]

    if len(sys.argv) >= 4 and sys.argv[2] == "--set":
        shares = float(sys.argv[3])
        set_manual_shares(ticker, shares)
        print(f"Set {ticker} shares to {shares}M")
    else:
        result = validate_shares_outstanding(ticker)
        print(f"\n{'='*60}")
        print(f"SHARES OUTSTANDING VALIDATION: {ticker}")
        print(f"{'='*60}")
        print(f"Recommended Value: {result.recommended_value:.2f}M")
        print(f"Source: {result.recommended_source}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Discrepancy Detected: {result.discrepancy_detected}")
        if result.discrepancy_detected:
            print(f"Discrepancy: {result.discrepancy_pct:.1%}")
        print(f"\nAll Sources:")
        for s in result.all_sources:
            print(f"  - {s.source}: {s.value:.2f}M (confidence: {s.confidence:.1%})")
        if result.warnings:
            print(f"\nWarnings:")
            for w in result.warnings:
                print(f"  - {w}")
