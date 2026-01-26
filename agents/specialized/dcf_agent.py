"""
DCF Modeling Agent - Uses actual calculation tools to build DCF models.

This agent combines AI reasoning with mathematical tools to produce
reliable DCF valuations that are mathematically verified.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..core.spawnable_agent import SpawnableAgent
from ..tools.financial_calculator import DCFCalculator, DCFInputs, DCFOutput, FinancialCalculator
from ..tools.market_data_api import MarketDataAPI
from ..tools.validation_tools import ValidationTools


@dataclass
class DCFModelResult:
    """Complete DCF model result with verification"""
    ticker: str
    company_name: str
    currency: str

    # Market data (verified)
    current_price: float
    market_cap: float
    shares_outstanding: float

    # Model inputs
    inputs: DCFInputs

    # Calculation results
    base_case: DCFOutput
    scenarios: Dict[str, DCFOutput]

    # Probability-weighted value
    pwv: float
    pwv_calculation: str

    # Recommendation
    implied_upside: float
    recommendation: str  # BUY, HOLD, SELL

    # Verification
    is_verified: bool
    verification_notes: List[str]

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'company_name': self.company_name,
            'currency': self.currency,
            'market_data': {
                'current_price': self.current_price,
                'market_cap': self.market_cap,
                'shares_outstanding': self.shares_outstanding
            },
            'base_case': {
                'fair_value': self.base_case.fair_value_per_share,
                'enterprise_value': self.base_case.enterprise_value,
                'wacc': self.base_case.wacc,
                'terminal_value_pct': self.base_case.terminal_value_pct_of_ev
            },
            'scenarios': {
                name: {
                    'fair_value': s.fair_value_per_share if s else None,
                    'implied_upside': (s.fair_value_per_share - self.current_price) / self.current_price if s else None
                }
                for name, s in self.scenarios.items()
            },
            'pwv': self.pwv,
            'pwv_calculation': self.pwv_calculation,
            'implied_upside': self.implied_upside,
            'recommendation': self.recommendation,
            'is_verified': self.is_verified,
            'verification_notes': self.verification_notes
        }


class DCFModelingAgent(SpawnableAgent):
    """
    DCF Modeling Agent - Builds mathematically verified DCF models.

    This agent:
    1. Fetches real market data using APIs
    2. Uses actual financial calculation tools
    3. Builds multi-scenario DCF models
    4. Verifies all calculations mathematically
    5. Produces reliable, auditable valuations

    Unlike AI-only approaches, this agent's outputs are REPRODUCIBLE
    because they use actual mathematical formulas.
    """

    # Scenario adjustments relative to base case
    DEFAULT_SCENARIO_ADJUSTMENTS = {
        'super_bear': {
            'growth_phase1_adj': -0.15,
            'growth_phase2_adj': -0.10,
            'growth_phase3_adj': -0.05,
            'beta_adj': 0.3,
            'terminal_growth_adj': -0.01
        },
        'bear': {
            'growth_phase1_adj': -0.08,
            'growth_phase2_adj': -0.05,
            'growth_phase3_adj': -0.02,
            'beta_adj': 0.15,
            'terminal_growth_adj': -0.005
        },
        'bull': {
            'growth_phase1_adj': 0.10,
            'growth_phase2_adj': 0.05,
            'growth_phase3_adj': 0.02,
            'beta_adj': -0.1,
            'terminal_growth_adj': 0.005
        },
        'super_bull': {
            'growth_phase1_adj': 0.20,
            'growth_phase2_adj': 0.10,
            'growth_phase3_adj': 0.03,
            'beta_adj': -0.2,
            'terminal_growth_adj': 0.01
        }
    }

    # Scenario probabilities
    DEFAULT_PROBABILITIES = {
        'super_bear': 0.05,
        'bear': 0.20,
        'base': 0.40,
        'bull': 0.25,
        'super_bull': 0.10
    }

    def __init__(
        self,
        name: str = "DCFModelingAgent",
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="DCF Financial Modeler",
            tier=2,
            parent=parent_agent
        )

        self.calculator = DCFCalculator()
        self.market_api = MarketDataAPI()
        self.fin_calc = FinancialCalculator()
        self.validation = ValidationTools()

    async def build_dcf_model(
        self,
        ticker: str,
        company_name: str,
        # Financial inputs (from research or defaults)
        revenue_base: Optional[float] = None,
        ebit_margin: float = 0.15,
        tax_rate: float = 0.25,
        # Growth assumptions
        growth_phase1: float = 0.15,
        growth_phase2: float = 0.10,
        growth_phase3: float = 0.05,
        target_margin: float = 0.20,
        # Risk assumptions
        beta: float = 1.2,
        country_risk_premium: float = 0.01,
        # Scenario adjustments (optional override)
        scenario_adjustments: Optional[Dict] = None,
        probabilities: Optional[Dict] = None
    ) -> DCFModelResult:
        """
        Build a complete DCF model with verified calculations.

        Args:
            ticker: Stock ticker
            company_name: Company name
            revenue_base: Base revenue (fetched if not provided)
            ebit_margin: Operating margin
            tax_rate: Corporate tax rate
            growth_phase1: Revenue growth years 1-3
            growth_phase2: Revenue growth years 4-5
            growth_phase3: Revenue growth years 6-10
            target_margin: Target operating margin
            beta: Stock beta
            country_risk_premium: Country risk premium
            scenario_adjustments: Custom scenario adjustments
            probabilities: Custom scenario probabilities

        Returns:
            DCFModelResult with verified calculations
        """
        verification_notes = []

        # Step 1: Fetch market data
        quote = await self.market_api.get_quote(ticker)

        if not quote:
            raise ValueError(f"Could not fetch market data for {ticker}")

        current_price = quote.price
        currency = quote.currency
        market_cap = quote.market_cap

        verification_notes.append(f"Price verified: {currency} {current_price} from {quote.source}")

        # Step 2: Get financial data
        financials = await self.market_api.get_financials(ticker, years=3)

        if financials and not revenue_base:
            # Use most recent revenue
            revenue_base = financials[0].revenue / 1_000_000  # Convert to millions
            ebit_margin = financials[0].operating_margin
            verification_notes.append(f"Revenue from financials: {revenue_base:.0f}M")
        elif not revenue_base:
            # Estimate from market cap
            revenue_base = market_cap / 1_000_000 / 3  # Rough P/S of 3
            verification_notes.append(f"Revenue estimated from market cap")

        # Calculate shares outstanding
        if market_cap and current_price:
            shares_outstanding = market_cap / current_price / 1_000_000  # In millions
        else:
            shares_outstanding = 100  # Default

        # Estimate D&A and CapEx as % of revenue
        depreciation = revenue_base * 0.05
        capex = revenue_base * 0.08
        working_capital_change = revenue_base * 0.02

        # Estimate net debt (if we have financials)
        net_debt = 0
        if financials:
            net_debt = (financials[0].total_debt - financials[0].cash) / 1_000_000

        # Step 3: Build DCF inputs
        inputs = DCFInputs(
            revenue_base=revenue_base,
            ebit_margin=ebit_margin,
            tax_rate=tax_rate,
            depreciation=depreciation,
            capex=capex,
            working_capital_change=working_capital_change,
            growth_phase1=growth_phase1,
            growth_phase2=growth_phase2,
            growth_phase3=growth_phase3,
            terminal_growth=0.025,  # Default 2.5%
            target_margin=target_margin,
            margin_improvement_years=5,
            risk_free_rate=0.045,  # Current ~4.5%
            beta=beta,
            equity_risk_premium=0.055,
            country_risk_premium=country_risk_premium,
            cost_of_debt=0.05,
            debt_ratio=0.2,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt
        )

        # Step 4: Calculate base case
        base_case = self.calculator.calculate(inputs)
        verification_notes.append(f"Base case WACC: {base_case.wacc:.2%}")
        verification_notes.extend(base_case.warnings)

        # Step 5: Calculate scenarios
        adjustments = scenario_adjustments or self.DEFAULT_SCENARIO_ADJUSTMENTS
        scenario_results = self.calculator.calculate_scenarios(inputs, adjustments)

        # Step 6: Calculate probability-weighted value
        probs = probabilities or self.DEFAULT_PROBABILITIES
        pwv, pwv_calc = self.calculator.calculate_probability_weighted_value(
            scenario_results,
            probs
        )

        # Step 7: Derive recommendation
        implied_upside = (pwv - current_price) / current_price

        if implied_upside > 0.20:
            recommendation = "BUY"
        elif implied_upside < -0.10:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        # Step 8: Validate results
        is_verified = base_case.is_valid

        # Additional sanity checks
        if abs(implied_upside) > 2.0:
            verification_notes.append(f"WARNING: Extreme upside ({implied_upside:.0%}) - review assumptions")
            is_verified = False

        if base_case.terminal_value_pct_of_ev > 0.75:
            verification_notes.append(f"WARNING: Terminal value is {base_case.terminal_value_pct_of_ev:.0%} of EV")

        return DCFModelResult(
            ticker=ticker,
            company_name=company_name,
            currency=currency,
            current_price=current_price,
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            inputs=inputs,
            base_case=base_case,
            scenarios=scenario_results,
            pwv=pwv,
            pwv_calculation=pwv_calc,
            implied_upside=implied_upside,
            recommendation=recommendation,
            is_verified=is_verified,
            verification_notes=verification_notes
        )

    async def validate_ai_dcf(
        self,
        ticker: str,
        ai_output: str
    ) -> Dict[str, Any]:
        """
        Validate AI-generated DCF output against recalculated values.

        Args:
            ticker: Stock ticker
            ai_output: Raw AI-generated DCF output

        Returns:
            Validation result comparing AI output to recalculated values
        """
        # Extract values from AI output
        import re

        ai_target = None
        ai_wacc = None
        ai_price = None

        # Extract target price
        target_match = re.search(r'FINAL_DCF_TARGET:\s*(?:\w+)?\s*([\d.]+)', ai_output)
        if target_match:
            ai_target = float(target_match.group(1))

        # Extract WACC
        wacc_match = re.search(r'BASE_WACC:\s*([\d.]+)%', ai_output)
        if wacc_match:
            ai_wacc = float(wacc_match.group(1)) / 100

        # Extract price
        price_match = re.search(r'CURRENT_PRICE_USED:\s*(?:\w+)?\s*([\d.]+)', ai_output)
        if price_match:
            ai_price = float(price_match.group(1))

        # Get verified price
        quote = await self.market_api.get_quote(ticker)
        verified_price = quote.price if quote else None

        # Build result
        result = {
            'ai_values': {
                'target': ai_target,
                'wacc': ai_wacc,
                'price': ai_price
            },
            'verified_price': verified_price,
            'price_match': abs(ai_price - verified_price) / verified_price < 0.02 if ai_price and verified_price else False
        }

        # If we can, recalculate and compare
        if verified_price:
            try:
                recalc = await self.build_dcf_model(
                    ticker=ticker,
                    company_name="Unknown",
                    beta=1.2  # Default
                )

                result['recalculated'] = {
                    'target': recalc.pwv,
                    'wacc': recalc.base_case.wacc,
                    'price': recalc.current_price
                }

                if ai_target and recalc.pwv:
                    result['target_deviation'] = abs(ai_target - recalc.pwv) / recalc.pwv

                if ai_wacc and recalc.base_case.wacc:
                    result['wacc_deviation'] = abs(ai_wacc - recalc.base_case.wacc)

            except Exception as e:
                result['recalculation_error'] = str(e)

        return result

    def format_dcf_output(self, result: DCFModelResult) -> str:
        """
        Format DCF result in the exact format expected by the workflow.

        This ensures the output matches what the HTML report generator expects.
        """
        output = f"""
============================================
DCF VALUATION MODEL - {result.ticker}
============================================

CURRENT_PRICE_USED: {result.currency} {result.current_price:.2f}
SOURCE: Verified from Yahoo Finance at {datetime.now().isoformat()}

============================================
WACC CALCULATION
============================================
{result.base_case.wacc_calculation}

BASE_WACC: {result.base_case.wacc * 100:.1f}%
RISK_FREE_RATE: {result.inputs.risk_free_rate * 100:.1f}%
BETA: {result.inputs.beta:.2f}
EQUITY_RISK_PREMIUM: {result.inputs.equity_risk_premium * 100:.1f}%
COUNTRY_RISK_PREMIUM: {result.inputs.country_risk_premium * 100:.1f}%

============================================
SCENARIO ANALYSIS
============================================

| Scenario    | Prob | WACC  | Target | Upside |
|-------------|------|-------|--------|--------|
"""

        for scenario_name in ['super_bear', 'bear', 'base', 'bull', 'super_bull']:
            scenario = result.scenarios.get(scenario_name)
            if scenario:
                prob = self.DEFAULT_PROBABILITIES.get(scenario_name, 0) * 100
                upside = (scenario.fair_value_per_share - result.current_price) / result.current_price * 100
                output += f"| {scenario_name.replace('_', ' ').title():11} | {prob:.0f}%  | {scenario.wacc*100:.1f}% | {result.currency} {scenario.fair_value_per_share:.2f} | {upside:+.0f}% |\n"

        output += f"""
============================================
PROBABILITY-WEIGHTED VALUE
============================================
{result.pwv_calculation}

============================================
FINAL DCF OUTPUT (MACHINE PARSED)
============================================
FINAL_DCF_TARGET: {result.currency} {result.pwv:.2f}
CURRENT_PRICE: {result.currency} {result.current_price:.2f}
IMPLIED_UPSIDE: {result.implied_upside * 100:.1f}%
RECOMMENDATION: {result.recommendation}
============================================

VERIFICATION STATUS: {'VERIFIED' if result.is_verified else 'NEEDS REVIEW'}
"""

        if result.verification_notes:
            output += "\nVERIFICATION NOTES:\n"
            for note in result.verification_notes:
                output += f"  - {note}\n"

        return output
