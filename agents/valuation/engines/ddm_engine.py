"""
DDM Engine - Dividend Discount Model valuation.

This engine values dividend-paying stocks using the Gordon Growth Model:
P = D1 / (r - g)

Where:
- D1 = Next year's expected dividend
- r = Required return (cost of equity)
- g = Dividend growth rate
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..assumption_extractor import ValuationInputs


@dataclass
class DDMResult:
    """Result of Dividend Discount Model valuation"""
    ticker: str
    current_price: float
    currency: str

    # Dividend data
    current_dividend: float
    dividend_yield: float
    payout_ratio: float

    # Growth assumptions
    dividend_growth_rate: float
    cost_of_equity: float

    # Valuation
    fair_value: float
    is_applicable: bool

    # Comparison
    implied_upside: float
    recommendation: str

    # Calculation breakdown
    calculation: str

    # Validation
    warnings: List[str]


class DDMEngine:
    """
    Dividend Discount Model Engine.

    Uses Gordon Growth Model for dividend-paying stocks:
    Fair Value = D0 × (1 + g) / (r - g)

    Where:
    - D0 = Current annual dividend per share
    - g = Expected dividend growth rate
    - r = Required return (cost of equity from CAPM)
    """

    def calculate(self, inputs: ValuationInputs) -> DDMResult:
        """
        Run Dividend Discount Model valuation.

        Args:
            inputs: Complete valuation inputs

        Returns:
            DDMResult with fair value estimate
        """
        warnings = []
        md = inputs.market_data
        wi = inputs.wacc_inputs

        # Check if DDM is applicable
        is_applicable = md.dividend_per_share > 0 and md.dividend_yield > 0

        if not is_applicable:
            warnings.append("DDM not applicable: Company does not pay dividends")
            return DDMResult(
                ticker=inputs.ticker,
                current_price=md.current_price,
                currency=md.currency,
                current_dividend=0,
                dividend_yield=0,
                payout_ratio=0,
                dividend_growth_rate=0,
                cost_of_equity=0,
                fair_value=0,
                is_applicable=False,
                implied_upside=0,
                recommendation="N/A",
                calculation="DDM not applicable - no dividends",
                warnings=warnings
            )

        # Calculate cost of equity using CAPM
        cost_of_equity = (
            wi.risk_free_rate +
            wi.beta * wi.equity_risk_premium +
            wi.country_risk_premium
        )

        # Estimate dividend growth rate
        # Use sustainable growth: g = ROE × (1 - payout_ratio)
        if md.payout_ratio > 0 and md.payout_ratio < 1:
            # Estimate ROE from earnings yield
            eps = md.net_income / md.shares_outstanding if md.shares_outstanding > 0 else 0
            earnings_yield = eps / md.current_price if md.current_price > 0 else 0

            # Rough ROE estimate
            roe = earnings_yield * (md.pe_ratio if md.pe_ratio else 15)
            sustainable_growth = roe * (1 - md.payout_ratio)

            # Cap growth rate
            dividend_growth = min(sustainable_growth, 0.08)  # Max 8%
            dividend_growth = max(dividend_growth, 0.02)  # Min 2%
        else:
            # Default to GDP growth rate
            dividend_growth = 0.025
            warnings.append("Using default 2.5% dividend growth rate")

        # Validate inputs
        if cost_of_equity <= dividend_growth:
            warnings.append(f"CRITICAL: Cost of equity ({cost_of_equity:.2%}) <= dividend growth ({dividend_growth:.2%})")
            # Force minimum spread
            dividend_growth = cost_of_equity - 0.02

        # Gordon Growth Model
        # P = D1 / (r - g) = D0 × (1 + g) / (r - g)
        d0 = md.dividend_per_share
        d1 = d0 * (1 + dividend_growth)
        fair_value = d1 / (cost_of_equity - dividend_growth)

        # Build calculation string
        calculation = f"""Gordon Growth Model:
Fair Value = D1 / (r - g)
D0 (Current Dividend) = {md.currency} {d0:.2f}
D1 (Next Year) = D0 × (1 + g) = {d0:.2f} × (1 + {dividend_growth:.2%}) = {d1:.2f}
r (Cost of Equity) = {cost_of_equity:.2%}
g (Dividend Growth) = {dividend_growth:.2%}
Fair Value = {d1:.2f} / ({cost_of_equity:.2%} - {dividend_growth:.2%}) = {md.currency} {fair_value:.2f}"""

        # Calculate implied upside
        implied_upside = (fair_value / md.current_price - 1) if md.current_price > 0 else 0

        # Determine recommendation
        if implied_upside > 0.15:
            recommendation = "BUY"
        elif implied_upside < -0.10:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        return DDMResult(
            ticker=inputs.ticker,
            current_price=md.current_price,
            currency=md.currency,
            current_dividend=md.dividend_per_share,
            dividend_yield=md.dividend_yield,
            payout_ratio=md.payout_ratio,
            dividend_growth_rate=dividend_growth,
            cost_of_equity=cost_of_equity,
            fair_value=fair_value,
            is_applicable=True,
            implied_upside=implied_upside,
            recommendation=recommendation,
            calculation=calculation,
            warnings=warnings
        )
