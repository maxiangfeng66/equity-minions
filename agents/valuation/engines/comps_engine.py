"""
Comps Engine - Comparable Company Analysis valuation.

This engine values a company by applying peer multiples:
- P/E ratio (Price to Earnings)
- EV/EBITDA (Enterprise Value to EBITDA)
- EV/Revenue (Enterprise Value to Revenue)
- P/B ratio (Price to Book)

The target's financials are multiplied by peer median multiples
to derive implied values.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import statistics

from ..assumption_extractor import ValuationInputs, PeerData


@dataclass
class CompsResult:
    """Result of comparable company analysis"""
    ticker: str
    current_price: float
    currency: str

    # Peer analysis
    peer_count: int
    peers_used: List[str]

    # Median multiples
    median_pe: Optional[float]
    median_ev_ebitda: Optional[float]
    median_ev_revenue: Optional[float]
    median_pb: Optional[float]

    # Implied values per method
    implied_from_pe: Optional[float]
    implied_from_ev_ebitda: Optional[float]
    implied_from_ev_revenue: Optional[float]
    implied_from_pb: Optional[float]

    # Weighted target
    weighted_target: float
    weights_used: Dict[str, float]

    # Comparison
    implied_upside: float
    recommendation: str

    # Validation
    is_valid: bool
    warnings: List[str]


class CompsEngine:
    """
    Comparable Company Analysis Engine.

    Derives fair value by applying peer multiples to target's financials.
    This is a market-based valuation that reflects what investors are
    paying for similar companies.
    """

    def __init__(self):
        # Default weights for different multiples
        self.default_weights = {
            'pe': 0.30,
            'ev_ebitda': 0.40,
            'ev_revenue': 0.20,
            'pb': 0.10
        }

    def calculate(self, inputs: ValuationInputs) -> CompsResult:
        """
        Run comparable company analysis.

        Args:
            inputs: Complete valuation inputs with peer data

        Returns:
            CompsResult with implied values
        """
        warnings = []
        md = inputs.market_data

        # Get peer multiples
        if inputs.peers and len(inputs.peers) > 0:
            # Filter out fake/placeholder peers
            real_peers = [p for p in inputs.peers if p.ticker != "PEER_AVG" and p.name != "Industry Average"]
            if real_peers:
                peers = real_peers
            else:
                peers = []
                warnings.append("CRITICAL: No real peer data - comps valuation unreliable")
        else:
            # NO FAKE PEER DATA - mark comps as unavailable
            peers = []
            warnings.append("CRITICAL: No peer data provided - comps valuation NOT AVAILABLE")
            warnings.append("To fix: Provide real comparable company data from broker research or yfinance")

        # Calculate median multiples
        pe_values = [p.pe_ratio for p in peers if p.pe_ratio and 0 < p.pe_ratio < 100]
        ev_ebitda_values = [p.ev_ebitda for p in peers if p.ev_ebitda and 0 < p.ev_ebitda < 50]
        ev_rev_values = [p.ev_revenue for p in peers if p.ev_revenue and 0 < p.ev_revenue < 20]
        pb_values = [p.price_to_book for p in peers if p.price_to_book and 0 < p.price_to_book < 20]

        median_pe = statistics.median(pe_values) if pe_values else None
        median_ev_ebitda = statistics.median(ev_ebitda_values) if ev_ebitda_values else None
        median_ev_revenue = statistics.median(ev_rev_values) if ev_rev_values else None
        median_pb = statistics.median(pb_values) if pb_values else None

        # Calculate implied values
        implied_values = {}
        weights = {}

        # P/E based valuation
        if median_pe and md.net_income > 0:
            eps = md.net_income / md.shares_outstanding
            implied_from_pe = eps * median_pe
            implied_values['pe'] = implied_from_pe
            weights['pe'] = self.default_weights['pe']
        else:
            implied_from_pe = None
            warnings.append("P/E valuation not available (no earnings or peers)")

        # EV/EBITDA based valuation
        if median_ev_ebitda and md.ebit_ttm > 0:
            # Approximate EBITDA from EBIT (add back ~15% D&A)
            ebitda = md.ebit_ttm * 1.15
            implied_ev = ebitda * median_ev_ebitda
            implied_equity = implied_ev - md.net_debt
            implied_from_ev_ebitda = implied_equity / md.shares_outstanding if md.shares_outstanding > 0 else 0
            implied_values['ev_ebitda'] = implied_from_ev_ebitda
            weights['ev_ebitda'] = self.default_weights['ev_ebitda']
        else:
            implied_from_ev_ebitda = None
            warnings.append("EV/EBITDA valuation not available")

        # EV/Revenue based valuation
        if median_ev_revenue and md.revenue_ttm > 0:
            implied_ev = md.revenue_ttm * median_ev_revenue
            implied_equity = implied_ev - md.net_debt
            implied_from_ev_revenue = implied_equity / md.shares_outstanding if md.shares_outstanding > 0 else 0
            implied_values['ev_revenue'] = implied_from_ev_revenue
            weights['ev_revenue'] = self.default_weights['ev_revenue']
        else:
            implied_from_ev_revenue = None
            warnings.append("EV/Revenue valuation not available")

        # P/B based valuation
        if median_pb:
            # Estimate book value from market cap / P/B ratio
            if md.price_to_book and md.price_to_book > 0:
                book_value_per_share = md.current_price / md.price_to_book
                implied_from_pb = book_value_per_share * median_pb
                implied_values['pb'] = implied_from_pb
                weights['pb'] = self.default_weights['pb']
            else:
                implied_from_pb = None
        else:
            implied_from_pb = None

        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        else:
            warnings.append("CRITICAL: No valid valuation methods available")

        # Calculate weighted target
        weighted_target = sum(
            implied_values.get(method, 0) * weight
            for method, weight in weights.items()
            if method in implied_values
        )

        # Calculate implied upside
        implied_upside = (weighted_target / md.current_price - 1) if md.current_price > 0 else 0

        # Determine recommendation
        if implied_upside > 0.15:
            recommendation = "BUY"
        elif implied_upside < -0.10:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        # Mark as invalid if no real peers were used
        has_real_peers = len(peers) > 0
        is_valid = weighted_target > 0 and has_real_peers

        if not has_real_peers:
            warnings.insert(0, "WARNING: Comps valuation based on NO REAL PEER DATA - treat as unreliable")
            recommendation = "N/A - No peer data"

        return CompsResult(
            ticker=inputs.ticker,
            current_price=md.current_price,
            currency=md.currency,
            peer_count=len(peers),
            peers_used=[p.name for p in peers] if peers else ["NONE - No real peer data available"],
            median_pe=median_pe,
            median_ev_ebitda=median_ev_ebitda,
            median_ev_revenue=median_ev_revenue,
            median_pb=median_pb,
            implied_from_pe=implied_from_pe,
            implied_from_ev_ebitda=implied_from_ev_ebitda,
            implied_from_ev_revenue=implied_from_ev_revenue,
            implied_from_pb=implied_from_pb,
            weighted_target=weighted_target if has_real_peers else 0.0,
            weights_used=weights,
            implied_upside=implied_upside if has_real_peers else 0.0,
            recommendation=recommendation,
            is_valid=is_valid,
            warnings=warnings
        )

    def _get_default_peers(self, market_data) -> List[PeerData]:
        """
        DO NOT generate fake peer data.

        Previously this generated fake "Industry Average" peers with made-up multiples.
        This was WRONG - it created hallucinated valuation data.

        Now we return an empty list and let the comps result show as invalid/unavailable.
        Real peer data should come from:
        1. Broker research (PDFs/Excel models)
        2. yfinance peer lookup
        3. User-provided peer list
        """
        # Return empty - no fake peers
        return []
