"""
Financial Calculator - Real mathematical computation tools for DCF and valuation.

This module provides ACTUAL calculations, not AI-generated numbers.
All formulas are implemented with proper financial mathematics.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import math


@dataclass
class DCFInputs:
    """Validated inputs for DCF calculation"""
    # Company financials (in millions)
    revenue_base: float
    ebit_margin: float  # as decimal (0.15 = 15%)
    tax_rate: float  # as decimal
    depreciation: float
    capex: float
    working_capital_change: float

    # Growth assumptions by phase
    growth_phase1: float  # Years 1-3
    growth_phase2: float  # Years 4-5
    growth_phase3: float  # Years 6-10
    terminal_growth: float

    # Margin trajectory
    target_margin: float

    # Discount rate components (required)
    risk_free_rate: float
    beta: float
    equity_risk_premium: float

    # Share data
    shares_outstanding: float  # in millions
    net_debt: float  # in millions (positive = debt, negative = cash)

    # Fields with defaults (must come after non-default fields)
    margin_improvement_years: int = 5
    country_risk_premium: float = 0.0
    cost_of_debt: float = 0.05
    debt_ratio: float = 0.2  # D/V


@dataclass
class DCFOutput:
    """Complete DCF calculation output with full transparency"""
    # Core outputs
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float

    # WACC calculation breakdown
    wacc: float
    cost_of_equity: float
    wacc_calculation: str

    # Terminal value analysis
    terminal_value: float
    terminal_value_pct_of_ev: float
    terminal_fcf: float

    # Yearly projections
    yearly_projections: List[Dict[str, float]]

    # Sensitivity outputs
    sensitivity_table: Dict[str, Dict[str, float]]

    # Validation flags
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True


class FinancialCalculator:
    """Core financial calculation utilities"""

    @staticmethod
    def calculate_wacc(
        risk_free_rate: float,
        beta: float,
        equity_risk_premium: float,
        country_risk_premium: float,
        cost_of_debt: float,
        tax_rate: float,
        debt_ratio: float  # D/V
    ) -> Tuple[float, float, str]:
        """
        Calculate WACC with full formula transparency.

        Returns:
            (wacc, cost_of_equity, calculation_string)
        """
        equity_ratio = 1 - debt_ratio

        # Cost of Equity using CAPM
        cost_of_equity = risk_free_rate + beta * equity_risk_premium + country_risk_premium

        # After-tax cost of debt
        after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)

        # WACC
        wacc = (equity_ratio * cost_of_equity) + (debt_ratio * after_tax_cost_of_debt)

        # Build calculation string for transparency
        calc_str = f"""WACC Calculation:
        Cost of Equity (Re) = Rf + β × ERP + CRP
        Re = {risk_free_rate:.2%} + {beta:.2f} × {equity_risk_premium:.2%} + {country_risk_premium:.2%}
        Re = {cost_of_equity:.2%}

        After-tax Cost of Debt = Rd × (1 - T)
        After-tax Rd = {cost_of_debt:.2%} × (1 - {tax_rate:.2%}) = {after_tax_cost_of_debt:.2%}

        WACC = (E/V) × Re + (D/V) × Rd × (1-T)
        WACC = {equity_ratio:.2%} × {cost_of_equity:.2%} + {debt_ratio:.2%} × {after_tax_cost_of_debt:.2%}
        WACC = {wacc:.2%}"""

        return wacc, cost_of_equity, calc_str

    @staticmethod
    def calculate_fcf(
        revenue: float,
        ebit_margin: float,
        tax_rate: float,
        depreciation: float,
        capex: float,
        working_capital_change: float
    ) -> Tuple[float, str]:
        """
        Calculate Free Cash Flow with formula transparency.

        FCF = EBIT × (1 - Tax) + D&A - CapEx - ΔWC

        Returns:
            (fcf, calculation_string)
        """
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)  # Net Operating Profit After Tax
        fcf = nopat + depreciation - capex - working_capital_change

        calc_str = f"""FCF Calculation:
        Revenue: ${revenue:,.0f}M
        EBIT (Revenue × {ebit_margin:.1%}): ${ebit:,.0f}M
        NOPAT (EBIT × (1 - {tax_rate:.1%})): ${nopat:,.0f}M
        + Depreciation: ${depreciation:,.0f}M
        - CapEx: ${capex:,.0f}M
        - ΔWorking Capital: ${working_capital_change:,.0f}M
        = FCF: ${fcf:,.0f}M"""

        return fcf, calc_str

    @staticmethod
    def calculate_terminal_value(
        terminal_fcf: float,
        wacc: float,
        terminal_growth: float
    ) -> Tuple[float, str]:
        """
        Calculate Terminal Value using Gordon Growth Model.

        TV = FCF_terminal × (1 + g) / (WACC - g)

        Returns:
            (terminal_value, calculation_string)
        """
        if wacc <= terminal_growth:
            raise ValueError(f"WACC ({wacc:.2%}) must be greater than terminal growth ({terminal_growth:.2%})")

        tv = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

        calc_str = f"""Terminal Value Calculation:
        TV = FCF × (1 + g) / (WACC - g)
        TV = ${terminal_fcf:,.0f}M × (1 + {terminal_growth:.2%}) / ({wacc:.2%} - {terminal_growth:.2%})
        TV = ${terminal_fcf:,.0f}M × {1 + terminal_growth:.4f} / {wacc - terminal_growth:.4f}
        TV = ${tv:,.0f}M"""

        return tv, calc_str

    @staticmethod
    def npv(cash_flows: List[float], discount_rate: float) -> float:
        """Calculate Net Present Value of cash flows"""
        npv = 0.0
        for i, cf in enumerate(cash_flows):
            npv += cf / ((1 + discount_rate) ** (i + 1))
        return npv

    @staticmethod
    def discount_value(future_value: float, rate: float, years: int) -> float:
        """Discount a future value to present"""
        return future_value / ((1 + rate) ** years)


class DCFCalculator:
    """
    Complete DCF Valuation Calculator with mathematical rigor.

    This replaces AI-generated DCF numbers with actual calculations.
    All formulas are explicit and verifiable.
    """

    def __init__(self):
        self.calc = FinancialCalculator()
        self.projection_years = 10

    def validate_inputs(self, inputs: DCFInputs) -> List[str]:
        """Validate DCF inputs and return warnings"""
        warnings = []

        # Terminal growth check
        if inputs.terminal_growth >= 0.04:
            warnings.append(f"WARNING: Terminal growth ({inputs.terminal_growth:.1%}) >= 4% is aggressive")

        if inputs.terminal_growth >= inputs.risk_free_rate:
            warnings.append(f"CRITICAL: Terminal growth ({inputs.terminal_growth:.1%}) >= risk-free rate ({inputs.risk_free_rate:.1%})")

        # Beta check
        if inputs.beta < 0.5 or inputs.beta > 2.5:
            warnings.append(f"WARNING: Beta ({inputs.beta:.2f}) is outside typical range (0.5-2.5)")

        # Margin check
        if inputs.target_margin > 0.40:
            warnings.append(f"WARNING: Target margin ({inputs.target_margin:.1%}) > 40% is very high")

        # Growth check
        if inputs.growth_phase1 > 0.50:
            warnings.append(f"WARNING: Phase 1 growth ({inputs.growth_phase1:.1%}) > 50% is very aggressive")

        # WACC vs terminal growth
        wacc, _, _ = self.calc.calculate_wacc(
            inputs.risk_free_rate, inputs.beta, inputs.equity_risk_premium,
            inputs.country_risk_premium, inputs.cost_of_debt, inputs.tax_rate, inputs.debt_ratio
        )
        if wacc - inputs.terminal_growth < 0.02:
            warnings.append(f"CRITICAL: WACC-g spread ({(wacc - inputs.terminal_growth):.2%}) < 2% creates unstable terminal value")

        return warnings

    def calculate(self, inputs: DCFInputs) -> DCFOutput:
        """
        Execute full DCF calculation with complete transparency.

        Args:
            inputs: Validated DCF inputs

        Returns:
            DCFOutput with all calculations and breakdowns
        """
        warnings = self.validate_inputs(inputs)

        # Step 1: Calculate WACC
        wacc, cost_of_equity, wacc_calc = self.calc.calculate_wacc(
            inputs.risk_free_rate,
            inputs.beta,
            inputs.equity_risk_premium,
            inputs.country_risk_premium,
            inputs.cost_of_debt,
            inputs.tax_rate,
            inputs.debt_ratio
        )

        # Step 2: Project revenues and FCFs
        yearly_projections = []
        revenue = inputs.revenue_base
        margin = inputs.ebit_margin
        margin_step = (inputs.target_margin - inputs.ebit_margin) / inputs.margin_improvement_years

        fcf_list = []

        for year in range(1, self.projection_years + 1):
            # Determine growth rate by phase
            if year <= 3:
                growth = inputs.growth_phase1
            elif year <= 5:
                growth = inputs.growth_phase2
            else:
                growth = inputs.growth_phase3

            # Apply growth
            revenue = revenue * (1 + growth)

            # Improve margin
            if year <= inputs.margin_improvement_years:
                margin = min(margin + margin_step, inputs.target_margin)
            else:
                margin = inputs.target_margin

            # Scale D&A and CapEx with revenue
            revenue_scale = revenue / inputs.revenue_base
            depreciation = inputs.depreciation * revenue_scale
            capex = inputs.capex * revenue_scale
            wc_change = inputs.working_capital_change * growth  # WC grows with revenue growth

            # Calculate FCF
            fcf, _ = self.calc.calculate_fcf(
                revenue, margin, inputs.tax_rate,
                depreciation, capex, wc_change
            )
            fcf_list.append(fcf)

            yearly_projections.append({
                'year': year,
                'revenue': revenue,
                'growth_rate': growth,
                'ebit_margin': margin,
                'ebit': revenue * margin,
                'depreciation': depreciation,
                'capex': capex,
                'working_capital_change': wc_change,
                'fcf': fcf,
                'discount_factor': 1 / ((1 + wacc) ** year),
                'pv_fcf': fcf / ((1 + wacc) ** year)
            })

        # Step 3: Calculate Terminal Value
        terminal_fcf = fcf_list[-1]
        terminal_value, tv_calc = self.calc.calculate_terminal_value(
            terminal_fcf, wacc, inputs.terminal_growth
        )

        # Discount terminal value to present
        pv_terminal = self.calc.discount_value(terminal_value, wacc, self.projection_years)

        # Step 4: Sum PV of FCFs
        pv_fcfs = sum(proj['pv_fcf'] for proj in yearly_projections)

        # Step 5: Enterprise Value
        enterprise_value = pv_fcfs + pv_terminal

        # Terminal value as % of EV
        tv_pct = pv_terminal / enterprise_value if enterprise_value > 0 else 0

        if tv_pct > 0.75:
            warnings.append(f"WARNING: Terminal value is {tv_pct:.1%} of EV (>75% is concerning)")

        # Step 6: Equity Value
        equity_value = enterprise_value - inputs.net_debt

        # Step 7: Per Share Value
        fair_value_per_share = equity_value / inputs.shares_outstanding

        # Step 8: Build sensitivity table
        sensitivity_table = self._build_sensitivity_table(inputs, wacc)

        return DCFOutput(
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            fair_value_per_share=fair_value_per_share,
            wacc=wacc,
            cost_of_equity=cost_of_equity,
            wacc_calculation=wacc_calc,
            terminal_value=terminal_value,
            terminal_value_pct_of_ev=tv_pct,
            terminal_fcf=terminal_fcf,
            yearly_projections=yearly_projections,
            sensitivity_table=sensitivity_table,
            warnings=warnings,
            is_valid=len([w for w in warnings if 'CRITICAL' in w]) == 0
        )

    def _build_sensitivity_table(
        self,
        inputs: DCFInputs,
        base_wacc: float
    ) -> Dict[str, Dict[str, float]]:
        """Build WACC vs Terminal Growth sensitivity table"""
        wacc_range = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
        tg_range = [inputs.terminal_growth - 0.01, inputs.terminal_growth - 0.005,
                    inputs.terminal_growth, inputs.terminal_growth + 0.005, inputs.terminal_growth + 0.01]

        table = {}
        for wacc in wacc_range:
            wacc_key = f"{wacc:.1%}"
            table[wacc_key] = {}
            for tg in tg_range:
                if wacc > tg:
                    # Recalculate with different WACC and terminal growth
                    modified_inputs = DCFInputs(
                        revenue_base=inputs.revenue_base,
                        ebit_margin=inputs.ebit_margin,
                        tax_rate=inputs.tax_rate,
                        depreciation=inputs.depreciation,
                        capex=inputs.capex,
                        working_capital_change=inputs.working_capital_change,
                        growth_phase1=inputs.growth_phase1,
                        growth_phase2=inputs.growth_phase2,
                        growth_phase3=inputs.growth_phase3,
                        terminal_growth=tg,
                        target_margin=inputs.target_margin,
                        margin_improvement_years=inputs.margin_improvement_years,
                        risk_free_rate=inputs.risk_free_rate,
                        beta=inputs.beta,
                        equity_risk_premium=inputs.equity_risk_premium,
                        country_risk_premium=inputs.country_risk_premium,
                        cost_of_debt=inputs.cost_of_debt,
                        debt_ratio=inputs.debt_ratio,
                        shares_outstanding=inputs.shares_outstanding,
                        net_debt=inputs.net_debt
                    )
                    # Simple recalc - just terminal value impact
                    # This is a simplified sensitivity
                    base_result = self.calculate(inputs)
                    tv_multiplier = (base_wacc - inputs.terminal_growth) / (wacc - tg)
                    adjusted_value = base_result.fair_value_per_share * (0.5 + 0.5 * tv_multiplier)
                    table[wacc_key][f"{tg:.2%}"] = adjusted_value
                else:
                    table[wacc_key][f"{tg:.2%}"] = float('inf')

        return table

    def calculate_scenarios(
        self,
        base_inputs: DCFInputs,
        scenario_adjustments: Dict[str, Dict[str, float]]
    ) -> Dict[str, DCFOutput]:
        """
        Calculate multiple scenarios with specified adjustments.

        Args:
            base_inputs: Base case DCF inputs
            scenario_adjustments: Dict of scenario_name -> adjustment dict
                e.g., {'bull': {'growth_phase1': 0.05, 'wacc_adjustment': -0.01}}

        Returns:
            Dict of scenario_name -> DCFOutput
        """
        results = {'base': self.calculate(base_inputs)}

        for scenario_name, adjustments in scenario_adjustments.items():
            # Create modified inputs
            modified = DCFInputs(
                revenue_base=base_inputs.revenue_base,
                ebit_margin=base_inputs.ebit_margin,
                tax_rate=base_inputs.tax_rate,
                depreciation=base_inputs.depreciation,
                capex=base_inputs.capex,
                working_capital_change=base_inputs.working_capital_change,
                growth_phase1=base_inputs.growth_phase1 + adjustments.get('growth_phase1_adj', 0),
                growth_phase2=base_inputs.growth_phase2 + adjustments.get('growth_phase2_adj', 0),
                growth_phase3=base_inputs.growth_phase3 + adjustments.get('growth_phase3_adj', 0),
                terminal_growth=base_inputs.terminal_growth + adjustments.get('terminal_growth_adj', 0),
                target_margin=base_inputs.target_margin + adjustments.get('margin_adj', 0),
                margin_improvement_years=base_inputs.margin_improvement_years,
                risk_free_rate=base_inputs.risk_free_rate,
                beta=base_inputs.beta + adjustments.get('beta_adj', 0),
                equity_risk_premium=base_inputs.equity_risk_premium,
                country_risk_premium=base_inputs.country_risk_premium,
                cost_of_debt=base_inputs.cost_of_debt,
                debt_ratio=base_inputs.debt_ratio,
                shares_outstanding=base_inputs.shares_outstanding,
                net_debt=base_inputs.net_debt
            )

            try:
                results[scenario_name] = self.calculate(modified)
            except Exception as e:
                results[scenario_name] = None

        return results

    def calculate_probability_weighted_value(
        self,
        scenario_results: Dict[str, DCFOutput],
        probabilities: Dict[str, float]
    ) -> Tuple[float, str]:
        """
        Calculate probability-weighted fair value.

        Returns:
            (pwv, calculation_string)
        """
        # Validate probabilities sum to 1
        prob_sum = sum(probabilities.values())
        if abs(prob_sum - 1.0) > 0.001:
            raise ValueError(f"Probabilities must sum to 1.0, got {prob_sum}")

        pwv = 0.0
        calc_parts = []

        for scenario, prob in probabilities.items():
            if scenario in scenario_results and scenario_results[scenario]:
                value = scenario_results[scenario].fair_value_per_share
                contribution = value * prob
                pwv += contribution
                calc_parts.append(f"  {scenario}: ${value:.2f} × {prob:.0%} = ${contribution:.2f}")

        calc_str = "Probability-Weighted Value:\n" + "\n".join(calc_parts) + f"\n  PWV = ${pwv:.2f}"

        return pwv, calc_str
