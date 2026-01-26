"""
DCF Engine - Discounted Cash Flow valuation using real math.

This engine calculates intrinsic value by:
1. Projecting future Free Cash Flows
2. Discounting them to present value using WACC
3. Adding discounted terminal value
4. Subtracting net debt to get equity value
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import math

from ..assumption_extractor import ValuationInputs, ScenarioAssumptions


@dataclass
class YearlyProjection:
    """Detailed projection for a single year"""
    year: int
    revenue: float
    revenue_growth: float
    ebit: float
    ebit_margin: float
    nopat: float
    da: float  # Depreciation & Amortization
    capex: float
    wc_change: float  # Working Capital Change
    fcf: float  # Free Cash Flow
    discount_factor: float
    pv_fcf: float  # Present Value of FCF


@dataclass
class DCFScenarioResult:
    """Result of DCF calculation for a single scenario"""
    scenario_name: str
    probability: float

    # Core values
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float

    # WACC breakdown
    wacc: float
    cost_of_equity: float
    wacc_calculation: str

    # Terminal value analysis
    terminal_value: float
    pv_terminal_value: float
    terminal_value_pct_of_ev: float

    # Cash flow projections
    yearly_fcfs: List[float]
    pv_fcfs: float

    # NEW: Detailed yearly projections
    yearly_projections: List[YearlyProjection]

    # NEW: Key inputs used
    inputs_used: Dict

    # Warnings
    warnings: List[str]


@dataclass
class DCFResult:
    """Complete DCF result with all scenarios"""
    ticker: str
    current_price: float
    currency: str

    # Individual scenario results
    scenarios: Dict[str, DCFScenarioResult]

    # Probability-weighted value
    pwv: float
    pwv_calculation: str

    # Implied metrics
    implied_upside: float
    recommendation: str

    # Validation
    is_valid: bool
    warnings: List[str]


class DCFEngine:
    """
    DCF Valuation Engine - Pure Python calculation.

    This replaces AI-generated DCF numbers with actual formulas:
    - WACC = (E/V) × Re + (D/V) × Rd × (1-T)
    - Re = Rf + β × ERP + CRP
    - FCF = EBIT × (1-T) + D&A - CapEx - ΔWC
    - TV = FCF_terminal × (1+g) / (WACC-g)
    - EV = Σ PV(FCF) + PV(TV)
    """

    def __init__(self, projection_years: int = 10):
        self.projection_years = projection_years

    def calculate(self, inputs: ValuationInputs) -> DCFResult:
        """
        Run DCF for all scenarios and calculate PWV.

        Args:
            inputs: Complete valuation inputs

        Returns:
            DCFResult with all scenarios and PWV
        """
        scenario_results = {}
        all_warnings = []

        for scenario_name, scenario in inputs.scenarios.items():
            try:
                result = self._calculate_scenario(inputs, scenario)
                scenario_results[scenario_name] = result
                all_warnings.extend(result.warnings)
            except Exception as e:
                all_warnings.append(f"Error calculating {scenario_name}: {str(e)}")

        # Calculate PWV
        pwv, pwv_calc = self._calculate_pwv(scenario_results)

        # Calculate implied upside
        current_price = inputs.market_data.current_price
        implied_upside = (pwv / current_price - 1) if current_price > 0 else 0

        # Determine recommendation
        if implied_upside > 0.15:
            recommendation = "BUY"
        elif implied_upside < -0.10:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        return DCFResult(
            ticker=inputs.ticker,
            current_price=current_price,
            currency=inputs.market_data.currency,
            scenarios=scenario_results,
            pwv=pwv,
            pwv_calculation=pwv_calc,
            implied_upside=implied_upside,
            recommendation=recommendation,
            is_valid=len([w for w in all_warnings if 'CRITICAL' in w]) == 0,
            warnings=all_warnings
        )

    def _calculate_scenario(
        self,
        inputs: ValuationInputs,
        scenario: ScenarioAssumptions
    ) -> DCFScenarioResult:
        """Calculate DCF for a single scenario"""
        warnings = []
        md = inputs.market_data
        wi = inputs.wacc_inputs

        # Step 1: Calculate WACC
        # Adjust beta and inputs based on scenario
        adjusted_beta = wi.beta + scenario.wacc_adjustment * 10  # rough conversion
        wacc, cost_of_equity, wacc_calc = self._calculate_wacc(
            wi.risk_free_rate,
            adjusted_beta,
            wi.equity_risk_premium,
            wi.country_risk_premium,
            wi.cost_of_debt,
            wi.tax_rate,
            wi.debt_to_total_capital
        )

        # Apply scenario WACC adjustment directly
        wacc = wacc + scenario.wacc_adjustment

        # Validate WACC
        if wacc <= scenario.terminal_growth:
            warnings.append(f"CRITICAL: WACC ({wacc:.2%}) <= terminal growth ({scenario.terminal_growth:.2%})")
            wacc = scenario.terminal_growth + 0.02  # Force minimum spread

        if wacc - scenario.terminal_growth < 0.02:
            warnings.append(f"WARNING: WACC-g spread ({(wacc - scenario.terminal_growth):.2%}) < 2%")

        # Step 2: Project FCFs with detailed breakdown
        yearly_fcfs, yearly_projections = self._project_fcfs(md, scenario, wi.tax_rate, wacc)

        # Step 3: Calculate PV of FCFs
        pv_fcfs = sum(proj.pv_fcf for proj in yearly_projections)

        # Step 4: Calculate terminal value
        terminal_fcf = yearly_fcfs[-1]
        terminal_value = terminal_fcf * (1 + scenario.terminal_growth) / (wacc - scenario.terminal_growth)

        # Discount terminal value to present
        pv_terminal = terminal_value / ((1 + wacc) ** self.projection_years)

        # Step 5: Enterprise Value
        enterprise_value = pv_fcfs + pv_terminal

        # Check terminal value percentage
        tv_pct = pv_terminal / enterprise_value if enterprise_value > 0 else 0
        if tv_pct > 0.75:
            warnings.append(f"WARNING: Terminal value is {tv_pct:.1%} of EV (>75%)")

        # Step 6: Equity Value
        equity_value = enterprise_value - md.net_debt

        # Step 7: Per share value
        fair_value = equity_value / md.shares_outstanding if md.shares_outstanding > 0 else 0

        # Build inputs_used dict for transparency
        inputs_used = {
            'base_revenue': md.revenue_ttm,
            'base_ebit_margin': md.ebit_margin,
            'net_debt': md.net_debt,
            'shares_outstanding': md.shares_outstanding,
            'tax_rate': wi.tax_rate,
            'risk_free_rate': wi.risk_free_rate,
            'beta': wi.beta,
            'equity_risk_premium': wi.equity_risk_premium,
            'country_risk_premium': wi.country_risk_premium,
            'cost_of_debt': wi.cost_of_debt,
            'debt_ratio': wi.debt_to_total_capital,
            'da_pct': 0.05,
            'capex_pct': 0.06,
            'wc_pct': 0.02,
            'projection_years': self.projection_years,
            'terminal_growth': scenario.terminal_growth,
            'revenue_growth_y1_3': scenario.revenue_growth_y1_3,
            'revenue_growth_y4_5': scenario.revenue_growth_y4_5,
            'revenue_growth_y6_10': scenario.revenue_growth_y6_10,
            'target_ebit_margin': scenario.target_ebit_margin
        }

        return DCFScenarioResult(
            scenario_name=scenario.name,
            probability=scenario.probability,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            fair_value_per_share=fair_value,
            wacc=wacc,
            cost_of_equity=cost_of_equity,
            wacc_calculation=wacc_calc,
            terminal_value=terminal_value,
            pv_terminal_value=pv_terminal,
            terminal_value_pct_of_ev=tv_pct,
            yearly_fcfs=yearly_fcfs,
            pv_fcfs=pv_fcfs,
            yearly_projections=yearly_projections,
            inputs_used=inputs_used,
            warnings=warnings
        )

    def _calculate_wacc(
        self,
        risk_free_rate: float,
        beta: float,
        equity_risk_premium: float,
        country_risk_premium: float,
        cost_of_debt: float,
        tax_rate: float,
        debt_ratio: float
    ) -> Tuple[float, float, str]:
        """Calculate WACC with CAPM for cost of equity"""
        equity_ratio = 1 - debt_ratio

        # Cost of Equity using CAPM
        cost_of_equity = risk_free_rate + beta * equity_risk_premium + country_risk_premium

        # After-tax cost of debt
        after_tax_cod = cost_of_debt * (1 - tax_rate)

        # WACC
        wacc = (equity_ratio * cost_of_equity) + (debt_ratio * after_tax_cod)

        calc = f"""WACC = (E/V)×Re + (D/V)×Rd×(1-T)
Re = Rf + β×ERP + CRP = {risk_free_rate:.2%} + {beta:.2f}×{equity_risk_premium:.2%} + {country_risk_premium:.2%} = {cost_of_equity:.2%}
WACC = {equity_ratio:.0%}×{cost_of_equity:.2%} + {debt_ratio:.0%}×{after_tax_cod:.2%} = {wacc:.2%}"""

        return wacc, cost_of_equity, calc

    def _project_fcfs(
        self,
        market_data,
        scenario: ScenarioAssumptions,
        tax_rate: float,
        wacc: float
    ) -> Tuple[List[float], List[YearlyProjection]]:
        """Project Free Cash Flows for 10 years with detailed breakdown"""
        fcfs = []
        projections = []

        revenue = market_data.revenue_ttm
        ebit_margin = market_data.ebit_margin

        # Estimate D&A and CapEx as % of revenue
        da_pct = 0.05  # 5% of revenue
        capex_pct = 0.06  # 6% of revenue
        wc_pct = 0.02  # 2% of revenue growth

        # Margin improvement trajectory
        margin_step = (scenario.target_ebit_margin - ebit_margin) / scenario.years_to_target_margin

        for year in range(1, self.projection_years + 1):
            # Determine growth rate by phase
            if year <= 3:
                growth = scenario.revenue_growth_y1_3
            elif year <= 5:
                growth = scenario.revenue_growth_y4_5
            else:
                growth = scenario.revenue_growth_y6_10

            # Apply growth
            prev_revenue = revenue
            revenue = revenue * (1 + growth)

            # Improve margin
            if year <= scenario.years_to_target_margin:
                ebit_margin = min(ebit_margin + margin_step, scenario.target_ebit_margin)
            else:
                ebit_margin = scenario.target_ebit_margin

            # Calculate components
            ebit = revenue * ebit_margin
            nopat = ebit * (1 - tax_rate)
            da = revenue * da_pct
            capex = revenue * capex_pct
            wc_change = (revenue - prev_revenue) * wc_pct

            # FCF = NOPAT + D&A - CapEx - ΔWC
            fcf = nopat + da - capex - wc_change
            fcfs.append(fcf)

            # Calculate discount factor and PV
            discount_factor = 1 / ((1 + wacc) ** year)
            pv_fcf = fcf * discount_factor

            # Store detailed projection
            projections.append(YearlyProjection(
                year=year,
                revenue=revenue,
                revenue_growth=growth,
                ebit=ebit,
                ebit_margin=ebit_margin,
                nopat=nopat,
                da=da,
                capex=capex,
                wc_change=wc_change,
                fcf=fcf,
                discount_factor=discount_factor,
                pv_fcf=pv_fcf
            ))

        return fcfs, projections

    def _calculate_pwv(
        self,
        scenarios: Dict[str, DCFScenarioResult]
    ) -> Tuple[float, str]:
        """Calculate probability-weighted value"""
        pwv = 0.0
        calc_parts = []

        for name, result in scenarios.items():
            contribution = result.fair_value_per_share * result.probability
            pwv += contribution
            calc_parts.append(
                f"{name}: {result.fair_value_per_share:.2f} × {result.probability:.0%} = {contribution:.2f}"
            )

        calc = "PWV = " + " + ".join([f"{s.fair_value_per_share:.2f}×{s.probability:.0%}"
                                       for s in scenarios.values()])
        calc += f" = {pwv:.2f}"

        return pwv, calc
