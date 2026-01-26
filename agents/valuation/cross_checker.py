"""
Cross-Checker - Validate that multiple valuation methods converge.

If DCF says $50 and Comps says $30, something is wrong.
This module identifies divergences and helps diagnose the issue.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

from .engines.dcf_engine import DCFResult
from .engines.comps_engine import CompsResult
from .engines.ddm_engine import DDMResult
from .engines.reverse_dcf_engine import ReverseDCFResult


@dataclass
class CrossCheckResult:
    """Result of cross-checking all valuation methods"""
    ticker: str
    current_price: float
    currency: str

    # Individual method results
    dcf_value: Optional[float]
    comps_value: Optional[float]
    ddm_value: Optional[float]
    implied_growth: Optional[float]

    # Convergence analysis
    method_values: Dict[str, float]
    value_range: Tuple[float, float]  # (min, max)
    value_spread: float  # (max - min) / average
    median_value: float
    mean_value: float

    # Convergence status
    is_converged: bool  # True if spread < 25%
    convergence_level: str  # "STRONG", "MODERATE", "WEAK", "DIVERGENT"

    # Specific checks
    dcf_vs_comps_diff: Optional[float]
    dcf_vs_broker_diff: Optional[float]
    implied_vs_assumed_growth_diff: Optional[float]

    # Market alignment
    market_alignment: str  # "ALIGNED", "UNDERVALUED", "OVERVALUED"
    market_alignment_pct: float

    # Diagnostics
    issues_found: List[str]
    recommendations: List[str]


class CrossChecker:
    """
    Cross-Check Validator for multiple valuation methods.

    This ensures that different approaches produce consistent results.
    Significant divergence triggers investigation.
    """

    def __init__(self, convergence_threshold: float = 0.25):
        """
        Initialize cross-checker.

        Args:
            convergence_threshold: Max acceptable spread between methods (default 25%)
        """
        self.convergence_threshold = convergence_threshold

    def check(
        self,
        dcf_result: DCFResult,
        comps_result: CompsResult,
        ddm_result: DDMResult,
        reverse_dcf_result: ReverseDCFResult,
        broker_target: Optional[float] = None
    ) -> CrossCheckResult:
        """
        Cross-check all valuation methods.

        Args:
            dcf_result: Result from DCF engine
            comps_result: Result from Comps engine
            ddm_result: Result from DDM engine
            reverse_dcf_result: Result from Reverse DCF
            broker_target: Broker consensus target (if available)

        Returns:
            CrossCheckResult with convergence analysis
        """
        issues = []
        recommendations = []

        # Collect valid method values
        method_values = {}

        if dcf_result.is_valid and dcf_result.pwv > 0:
            method_values['DCF'] = dcf_result.pwv

        if comps_result.is_valid and comps_result.weighted_target > 0:
            method_values['Comps'] = comps_result.weighted_target

        if ddm_result.is_applicable and ddm_result.fair_value > 0:
            method_values['DDM'] = ddm_result.fair_value

        if len(method_values) < 2:
            issues.append("CRITICAL: Less than 2 valid valuation methods available")

        # Calculate statistics
        values = list(method_values.values())
        if values:
            min_val = min(values)
            max_val = max(values)
            mean_val = statistics.mean(values)
            median_val = statistics.median(values)
            spread = (max_val - min_val) / mean_val if mean_val > 0 else 0
        else:
            min_val = max_val = mean_val = median_val = 0
            spread = 1.0

        # Determine convergence level
        if spread <= 0.15:
            convergence_level = "STRONG"
            is_converged = True
        elif spread <= 0.25:
            convergence_level = "MODERATE"
            is_converged = True
        elif spread <= 0.40:
            convergence_level = "WEAK"
            is_converged = False
            issues.append(f"Weak convergence: {spread:.0%} spread between methods")
        else:
            convergence_level = "DIVERGENT"
            is_converged = False
            issues.append(f"CRITICAL: Methods divergent with {spread:.0%} spread")

        # DCF vs Comps comparison
        dcf_vs_comps = None
        if 'DCF' in method_values and 'Comps' in method_values:
            dcf_vs_comps = (method_values['DCF'] - method_values['Comps']) / method_values['Comps']
            if abs(dcf_vs_comps) > 0.30:
                issues.append(f"DCF vs Comps divergence: {dcf_vs_comps:+.0%}")
                if dcf_vs_comps > 0:
                    recommendations.append("DCF higher than Comps - check growth assumptions aren't too aggressive")
                else:
                    recommendations.append("DCF lower than Comps - market may be pricing in growth not in model")

        # DCF vs Broker comparison
        dcf_vs_broker = None
        if 'DCF' in method_values and broker_target:
            dcf_vs_broker = (method_values['DCF'] - broker_target) / broker_target
            if abs(dcf_vs_broker) > 0.30:
                issues.append(f"DCF vs Broker consensus divergence: {dcf_vs_broker:+.0%}")
                recommendations.append("Significant deviation from broker consensus - review assumptions")

        # Implied growth vs assumed growth
        implied_vs_assumed = None
        base_scenario = dcf_result.scenarios.get('base')
        if reverse_dcf_result.is_valid and base_scenario:
            implied_vs_assumed = reverse_dcf_result.growth_difference
            if reverse_dcf_result.market_view == "MORE_OPTIMISTIC":
                issues.append(f"Market expects higher growth than model: +{implied_vs_assumed:.1%}")
            elif reverse_dcf_result.market_view == "MORE_PESSIMISTIC":
                issues.append(f"Market expects lower growth than model: {implied_vs_assumed:.1%}")

        # Market alignment
        current_price = dcf_result.current_price
        if median_val > 0:
            market_diff = (median_val - current_price) / current_price
            if market_diff > 0.15:
                market_alignment = "UNDERVALUED"
            elif market_diff < -0.10:
                market_alignment = "OVERVALUED"
            else:
                market_alignment = "ALIGNED"
        else:
            market_alignment = "UNKNOWN"
            market_diff = 0

        # Generate recommendations
        if is_converged and market_alignment == "UNDERVALUED":
            recommendations.append("Methods converge and indicate upside - BUY candidate")
        elif is_converged and market_alignment == "OVERVALUED":
            recommendations.append("Methods converge and indicate downside - SELL candidate")
        elif not is_converged:
            recommendations.append("Methods divergent - more analysis needed before recommendation")

        return CrossCheckResult(
            ticker=dcf_result.ticker,
            current_price=current_price,
            currency=dcf_result.currency,
            dcf_value=method_values.get('DCF'),
            comps_value=method_values.get('Comps'),
            ddm_value=method_values.get('DDM'),
            implied_growth=reverse_dcf_result.implied_growth_rate if reverse_dcf_result.is_valid else None,
            method_values=method_values,
            value_range=(min_val, max_val),
            value_spread=spread,
            median_value=median_val,
            mean_value=mean_val,
            is_converged=is_converged,
            convergence_level=convergence_level,
            dcf_vs_comps_diff=dcf_vs_comps,
            dcf_vs_broker_diff=dcf_vs_broker,
            implied_vs_assumed_growth_diff=implied_vs_assumed,
            market_alignment=market_alignment,
            market_alignment_pct=market_diff,
            issues_found=issues,
            recommendations=recommendations
        )
