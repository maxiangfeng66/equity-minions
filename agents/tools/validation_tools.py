"""
Validation Tools - Mathematical and logical validation utilities.

Provides tools for validating DCF calculations, checking data consistency,
and ensuring mathematical correctness.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import math


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    severity: str  # 'critical', 'warning', 'info'
    message: str
    expected: Any = None
    actual: Any = None
    fix_suggestion: Optional[str] = None


class ValidationTools:
    """
    Comprehensive validation tools for financial calculations and data.
    """

    # Valid ranges for financial metrics
    VALID_RANGES = {
        'wacc': (0.04, 0.25),  # 4% - 25%
        'terminal_growth': (0.01, 0.04),  # 1% - 4%
        'beta': (0.3, 3.0),
        'risk_free_rate': (0.01, 0.08),
        'equity_risk_premium': (0.04, 0.10),
        'operating_margin': (-0.50, 0.60),
        'revenue_growth': (-0.30, 1.00),  # -30% to 100%
        'terminal_value_pct': (0.30, 0.75),  # 30% - 75% of EV
    }

    @staticmethod
    def validate_dcf_math(
        fcf_projections: List[float],
        wacc: float,
        terminal_growth: float,
        terminal_value: float,
        enterprise_value: float,
        tolerance: float = 0.01
    ) -> List[ValidationResult]:
        """
        Validate DCF mathematical calculations.

        Checks:
        1. NPV calculation is correct
        2. Terminal value formula is correct
        3. Total EV matches sum of PV(FCFs) + PV(TV)
        """
        results = []

        # Check 1: WACC > terminal growth
        if wacc <= terminal_growth:
            results.append(ValidationResult(
                check_name='wacc_vs_terminal_growth',
                passed=False,
                severity='critical',
                message=f'WACC ({wacc:.2%}) must be greater than terminal growth ({terminal_growth:.2%})',
                expected='WACC > g',
                actual=f'{wacc:.2%} <= {terminal_growth:.2%}',
                fix_suggestion='Increase WACC or decrease terminal growth rate'
            ))
            return results  # Can't continue if this fails

        # Check 2: Verify terminal value calculation
        if fcf_projections:
            final_fcf = fcf_projections[-1]
            expected_tv = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            tv_error = abs(terminal_value - expected_tv) / expected_tv if expected_tv else 0

            results.append(ValidationResult(
                check_name='terminal_value_formula',
                passed=tv_error < tolerance,
                severity='critical' if tv_error >= tolerance else 'info',
                message=f'Terminal value {"matches" if tv_error < tolerance else "DOES NOT match"} Gordon Growth formula',
                expected=f'${expected_tv:,.0f}',
                actual=f'${terminal_value:,.0f}',
                fix_suggestion=f'TV should be FCF_final × (1+g) / (WACC-g) = ${expected_tv:,.0f}'
            ))

        # Check 3: Verify NPV calculation
        n_years = len(fcf_projections)
        pv_fcfs = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcf_projections))
        pv_tv = terminal_value / ((1 + wacc) ** n_years)
        calculated_ev = pv_fcfs + pv_tv

        ev_error = abs(enterprise_value - calculated_ev) / calculated_ev if calculated_ev else 0

        results.append(ValidationResult(
            check_name='enterprise_value_calculation',
            passed=ev_error < tolerance,
            severity='critical' if ev_error >= tolerance else 'info',
            message=f'Enterprise value {"matches" if ev_error < tolerance else "DOES NOT match"} NPV calculation',
            expected=f'${calculated_ev:,.0f}',
            actual=f'${enterprise_value:,.0f}',
            fix_suggestion=f'EV = PV(FCFs) + PV(TV) = ${pv_fcfs:,.0f} + ${pv_tv:,.0f} = ${calculated_ev:,.0f}'
        ))

        return results

    @staticmethod
    def validate_wacc_calculation(
        stated_wacc: float,
        risk_free_rate: float,
        beta: float,
        equity_risk_premium: float,
        country_risk_premium: float,
        cost_of_debt: float,
        tax_rate: float,
        debt_ratio: float,
        tolerance: float = 0.005
    ) -> List[ValidationResult]:
        """
        Validate WACC calculation components and formula.
        """
        results = []

        # Check component ranges
        for name, (min_val, max_val) in [
            ('risk_free_rate', ValidationTools.VALID_RANGES['risk_free_rate']),
            ('beta', ValidationTools.VALID_RANGES['beta']),
            ('equity_risk_premium', ValidationTools.VALID_RANGES['equity_risk_premium']),
        ]:
            value = locals()[name]
            in_range = min_val <= value <= max_val
            results.append(ValidationResult(
                check_name=f'{name}_range',
                passed=in_range,
                severity='warning' if not in_range else 'info',
                message=f'{name} {"is" if in_range else "is NOT"} within typical range',
                expected=f'{min_val:.2%} - {max_val:.2%}',
                actual=f'{value:.2%}'
            ))

        # Calculate expected WACC
        equity_ratio = 1 - debt_ratio
        cost_of_equity = risk_free_rate + beta * equity_risk_premium + country_risk_premium
        after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
        expected_wacc = equity_ratio * cost_of_equity + debt_ratio * after_tax_cost_of_debt

        wacc_error = abs(stated_wacc - expected_wacc)

        results.append(ValidationResult(
            check_name='wacc_formula',
            passed=wacc_error < tolerance,
            severity='critical' if wacc_error >= tolerance else 'info',
            message=f'WACC calculation {"is correct" if wacc_error < tolerance else "HAS ERRORS"}',
            expected=f'{expected_wacc:.2%}',
            actual=f'{stated_wacc:.2%}',
            fix_suggestion=f'WACC = {equity_ratio:.0%} × {cost_of_equity:.2%} + {debt_ratio:.0%} × {after_tax_cost_of_debt:.2%} = {expected_wacc:.2%}'
        ))

        return results

    @staticmethod
    def validate_scenario_consistency(
        scenarios: Dict[str, Dict[str, float]],
        current_price: float
    ) -> List[ValidationResult]:
        """
        Validate scenario analysis for logical consistency.

        Checks:
        1. Probabilities sum to 1
        2. Scenario targets are ordered correctly (super_bear < bear < base < bull < super_bull)
        3. Upside/downside calculations are correct
        4. No scenario implies impossible returns (>300% or <-80%)
        """
        results = []

        # Extract data
        scenario_order = ['super_bear', 'bear', 'base', 'bull', 'super_bull']
        probabilities = []
        targets = []

        for scenario in scenario_order:
            if scenario in scenarios:
                probabilities.append(scenarios[scenario].get('probability', 0))
                targets.append(scenarios[scenario].get('target', 0))

        # Check 1: Probabilities sum to 1
        prob_sum = sum(probabilities)
        results.append(ValidationResult(
            check_name='probability_sum',
            passed=abs(prob_sum - 1.0) < 0.01,
            severity='critical' if abs(prob_sum - 1.0) >= 0.01 else 'info',
            message=f'Scenario probabilities {"sum to 100%" if abs(prob_sum - 1.0) < 0.01 else "DO NOT sum to 100%"}',
            expected='100%',
            actual=f'{prob_sum:.0%}'
        ))

        # Check 2: Targets are ordered correctly
        if len(targets) >= 2:
            is_ordered = all(targets[i] <= targets[i+1] for i in range(len(targets)-1))
            results.append(ValidationResult(
                check_name='scenario_ordering',
                passed=is_ordered,
                severity='warning' if not is_ordered else 'info',
                message=f'Scenario targets {"are" if is_ordered else "are NOT"} in correct order (bear < base < bull)',
                expected='Ascending order',
                actual=str(targets)
            ))

        # Check 3: Validate implied returns
        for scenario, data in scenarios.items():
            target = data.get('target', current_price)
            implied_return = (target - current_price) / current_price if current_price else 0

            is_reasonable = -0.80 <= implied_return <= 3.00

            results.append(ValidationResult(
                check_name=f'{scenario}_return_reasonableness',
                passed=is_reasonable,
                severity='warning' if not is_reasonable else 'info',
                message=f'{scenario} implied return {"is" if is_reasonable else "is NOT"} reasonable',
                expected='-80% to +300%',
                actual=f'{implied_return:.0%}'
            ))

        return results

    @staticmethod
    def validate_price_consistency(
        stated_price: float,
        verified_price: float,
        tolerance: float = 0.02
    ) -> ValidationResult:
        """
        Validate that stated price matches verified market price.
        """
        if verified_price <= 0:
            return ValidationResult(
                check_name='price_verification',
                passed=False,
                severity='critical',
                message='Could not verify market price',
                expected='Valid market price',
                actual=str(verified_price)
            )

        deviation = abs(stated_price - verified_price) / verified_price

        return ValidationResult(
            check_name='price_consistency',
            passed=deviation <= tolerance,
            severity='critical' if deviation > tolerance else 'info',
            message=f'Stated price {"matches" if deviation <= tolerance else "DOES NOT match"} verified market price',
            expected=f'{verified_price:.2f}',
            actual=f'{stated_price:.2f}',
            fix_suggestion=f'Use verified price: {verified_price:.2f}' if deviation > tolerance else None
        )

    @staticmethod
    def validate_fcf_calculation(
        revenue: float,
        ebit_margin: float,
        tax_rate: float,
        depreciation: float,
        capex: float,
        working_capital_change: float,
        stated_fcf: float,
        tolerance: float = 0.01
    ) -> ValidationResult:
        """
        Validate Free Cash Flow calculation.

        FCF = EBIT × (1 - Tax) + D&A - CapEx - ΔWC
        """
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)
        expected_fcf = nopat + depreciation - capex - working_capital_change

        if expected_fcf == 0:
            return ValidationResult(
                check_name='fcf_calculation',
                passed=False,
                severity='warning',
                message='Calculated FCF is zero',
                expected='Non-zero FCF',
                actual='0'
            )

        fcf_error = abs(stated_fcf - expected_fcf) / abs(expected_fcf)

        calculation = f"""FCF = EBIT × (1-T) + D&A - CapEx - ΔWC
        = {revenue:,.0f} × {ebit_margin:.1%} × (1 - {tax_rate:.1%}) + {depreciation:,.0f} - {capex:,.0f} - {working_capital_change:,.0f}
        = {expected_fcf:,.0f}"""

        return ValidationResult(
            check_name='fcf_calculation',
            passed=fcf_error < tolerance,
            severity='critical' if fcf_error >= tolerance else 'info',
            message=f'FCF calculation {"is correct" if fcf_error < tolerance else "HAS ERRORS"}',
            expected=f'{expected_fcf:,.0f}',
            actual=f'{stated_fcf:,.0f}',
            fix_suggestion=calculation if fcf_error >= tolerance else None
        )

    @staticmethod
    def run_full_validation(
        dcf_output: Dict[str, Any],
        verified_price: float
    ) -> Dict[str, Any]:
        """
        Run comprehensive validation on DCF output.

        Returns summary with all checks and overall pass/fail.
        """
        all_results = []

        # Price validation
        stated_price = dcf_output.get('current_price', 0)
        all_results.append(
            ValidationTools.validate_price_consistency(stated_price, verified_price)
        )

        # WACC validation
        wacc_results = ValidationTools.validate_wacc_calculation(
            stated_wacc=dcf_output.get('wacc', 0),
            risk_free_rate=dcf_output.get('risk_free_rate', 0.045),
            beta=dcf_output.get('beta', 1.0),
            equity_risk_premium=dcf_output.get('equity_risk_premium', 0.055),
            country_risk_premium=dcf_output.get('country_risk_premium', 0),
            cost_of_debt=dcf_output.get('cost_of_debt', 0.05),
            tax_rate=dcf_output.get('tax_rate', 0.25),
            debt_ratio=dcf_output.get('debt_ratio', 0.2)
        )
        all_results.extend(wacc_results)

        # Scenario validation
        if 'scenarios' in dcf_output:
            scenario_results = ValidationTools.validate_scenario_consistency(
                dcf_output['scenarios'],
                verified_price
            )
            all_results.extend(scenario_results)

        # DCF math validation
        if 'fcf_projections' in dcf_output:
            math_results = ValidationTools.validate_dcf_math(
                fcf_projections=dcf_output['fcf_projections'],
                wacc=dcf_output.get('wacc', 0.10),
                terminal_growth=dcf_output.get('terminal_growth', 0.025),
                terminal_value=dcf_output.get('terminal_value', 0),
                enterprise_value=dcf_output.get('enterprise_value', 0)
            )
            all_results.extend(math_results)

        # Aggregate results
        critical_failures = [r for r in all_results if not r.passed and r.severity == 'critical']
        warnings = [r for r in all_results if not r.passed and r.severity == 'warning']

        return {
            'overall_passed': len(critical_failures) == 0,
            'critical_failures': len(critical_failures),
            'warnings': len(warnings),
            'total_checks': len(all_results),
            'passed_checks': len([r for r in all_results if r.passed]),
            'results': [
                {
                    'check': r.check_name,
                    'passed': r.passed,
                    'severity': r.severity,
                    'message': r.message,
                    'expected': r.expected,
                    'actual': r.actual,
                    'fix': r.fix_suggestion
                }
                for r in all_results
            ]
        }
