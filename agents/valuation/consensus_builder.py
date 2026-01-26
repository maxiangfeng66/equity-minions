"""
Consensus Builder - Combine all valuation methods into final recommendation.

This module takes results from all valuation engines and produces:
1. A weighted consensus fair value
2. Confidence level based on convergence
3. Final investment recommendation with supporting analysis
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

from .engines.dcf_engine import DCFResult
from .engines.comps_engine import CompsResult
from .engines.ddm_engine import DDMResult
from .engines.reverse_dcf_engine import ReverseDCFResult
from .cross_checker import CrossCheckResult


@dataclass
class ConsensusValuation:
    """Final valuation output combining all methods"""
    ticker: str
    current_price: float
    currency: str

    # Consensus values
    consensus_fair_value: float
    fair_value_range: Tuple[float, float]

    # Implied metrics
    implied_upside: float
    recommendation: str  # "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"
    confidence: str  # "HIGH", "MEDIUM", "LOW"

    # Method contributions
    method_values: Dict[str, float]
    method_weights: Dict[str, float]

    # Supporting analysis
    key_drivers: List[str]
    key_risks: List[str]

    # Cross-check summary
    convergence_status: str
    convergence_issues: List[str]

    # Market alignment
    market_expectations: str

    # Full calculation breakdown
    valuation_summary: str


class ConsensusBuilder:
    """
    Build consensus valuation from multiple methods.

    Weighting philosophy:
    - DCF: Primary method (40%) - captures intrinsic value
    - Comps: Market reality check (30%) - what market pays for similar
    - DDM: Income investors (15%) - dividend perspective
    - Reverse DCF: Sanity check (15%) - market expectations

    Weights are adjusted based on:
    - Method validity (invalid methods get 0 weight)
    - Convergence (high divergence reduces confidence)
    - Stock characteristics (DDM more important for REITs/utilities)
    """

    def __init__(self):
        self.base_weights = {
            'DCF': 0.40,
            'Comps': 0.30,
            'DDM': 0.15,
            'ReverseDCF': 0.15
        }

    def build_consensus(
        self,
        dcf_result: DCFResult,
        comps_result: CompsResult,
        ddm_result: DDMResult,
        reverse_dcf_result: ReverseDCFResult,
        cross_check: CrossCheckResult,
        broker_target: Optional[float] = None
    ) -> ConsensusValuation:
        """
        Build consensus valuation from all methods.

        Args:
            dcf_result: DCF engine output
            comps_result: Comps engine output
            ddm_result: DDM engine output
            reverse_dcf_result: Reverse DCF output
            cross_check: Cross-check validation result
            broker_target: Optional broker consensus

        Returns:
            ConsensusValuation with final recommendation
        """
        # Collect valid method values
        method_values = {}
        weights = {}

        if dcf_result.is_valid and dcf_result.pwv > 0:
            method_values['DCF'] = dcf_result.pwv
            weights['DCF'] = self.base_weights['DCF']

        if comps_result.is_valid and comps_result.weighted_target > 0:
            method_values['Comps'] = comps_result.weighted_target
            weights['Comps'] = self.base_weights['Comps']

        if ddm_result.is_applicable and ddm_result.fair_value > 0:
            method_values['DDM'] = ddm_result.fair_value
            # Increase DDM weight for dividend stocks
            if ddm_result.dividend_yield > 0.03:  # >3% yield
                weights['DDM'] = self.base_weights['DDM'] * 1.5
            else:
                weights['DDM'] = self.base_weights['DDM']

        # Reverse DCF is a sanity check, not a direct valuation
        # We use it to adjust confidence, not the fair value directly

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # Calculate consensus fair value
        consensus_fv = sum(
            method_values.get(method, 0) * weight
            for method, weight in weights.items()
        )

        # Calculate fair value range
        if method_values:
            fv_min = min(method_values.values())
            fv_max = max(method_values.values())
        else:
            fv_min = fv_max = dcf_result.current_price

        # Calculate implied upside
        current_price = dcf_result.current_price
        implied_upside = (consensus_fv / current_price - 1) if current_price > 0 else 0

        # Determine confidence based on convergence
        confidence = self._determine_confidence(cross_check, len(method_values))

        # Determine recommendation
        recommendation = self._determine_recommendation(
            implied_upside,
            confidence,
            cross_check.is_converged
        )

        # Identify key drivers
        key_drivers = self._identify_key_drivers(dcf_result, comps_result, ddm_result)

        # Identify key risks
        key_risks = self._identify_key_risks(
            dcf_result, cross_check, reverse_dcf_result
        )

        # Market expectations summary
        market_expectations = self._summarize_market_expectations(reverse_dcf_result)

        # Build valuation summary
        valuation_summary = self._build_summary(
            method_values, weights, consensus_fv, current_price,
            dcf_result, comps_result, ddm_result, reverse_dcf_result,
            cross_check, broker_target
        )

        return ConsensusValuation(
            ticker=dcf_result.ticker,
            current_price=current_price,
            currency=dcf_result.currency,
            consensus_fair_value=consensus_fv,
            fair_value_range=(fv_min, fv_max),
            implied_upside=implied_upside,
            recommendation=recommendation,
            confidence=confidence,
            method_values=method_values,
            method_weights=weights,
            key_drivers=key_drivers,
            key_risks=key_risks,
            convergence_status=cross_check.convergence_level,
            convergence_issues=cross_check.issues_found,
            market_expectations=market_expectations,
            valuation_summary=valuation_summary
        )

    def _determine_confidence(
        self,
        cross_check: CrossCheckResult,
        num_methods: int
    ) -> str:
        """Determine confidence level based on convergence and method count"""
        if cross_check.convergence_level == "STRONG" and num_methods >= 3:
            return "HIGH"
        elif cross_check.convergence_level in ["STRONG", "MODERATE"] and num_methods >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def _determine_recommendation(
        self,
        upside: float,
        confidence: str,
        converged: bool
    ) -> str:
        """Determine investment recommendation"""
        # If methods don't converge, be cautious
        if not converged:
            if upside > 0.25:
                return "BUY"  # Not strong buy due to uncertainty
            elif upside < -0.15:
                return "SELL"
            else:
                return "HOLD"

        # High confidence recommendations
        if confidence == "HIGH":
            if upside > 0.25:
                return "STRONG BUY"
            elif upside > 0.10:
                return "BUY"
            elif upside < -0.15:
                return "STRONG SELL"
            elif upside < -0.05:
                return "SELL"
            else:
                return "HOLD"

        # Medium/Low confidence - more conservative
        if upside > 0.20:
            return "BUY"
        elif upside < -0.10:
            return "SELL"
        else:
            return "HOLD"

    def _identify_key_drivers(
        self,
        dcf_result: DCFResult,
        comps_result: CompsResult,
        ddm_result: DDMResult
    ) -> List[str]:
        """Identify key value drivers from the analysis"""
        drivers = []

        # DCF drivers
        if dcf_result.is_valid:
            base = dcf_result.scenarios.get('base')
            if base:
                drivers.append(f"Revenue growth assumption: {base.scenario_name}")
                if base.terminal_value_pct_of_ev > 0.6:
                    drivers.append("Terminal value is significant contributor")

        # Comps drivers
        if comps_result.is_valid:
            if comps_result.median_ev_ebitda:
                drivers.append(f"Trading at peer EV/EBITDA multiple")
            if comps_result.implied_upside > 0.15:
                drivers.append("Discount to peer multiples")
            elif comps_result.implied_upside < -0.10:
                drivers.append("Premium to peer multiples")

        # DDM drivers
        if ddm_result.is_applicable:
            if ddm_result.dividend_yield > 0.04:
                drivers.append(f"Attractive dividend yield: {ddm_result.dividend_yield:.1%}")

        return drivers[:5]  # Top 5 drivers

    def _identify_key_risks(
        self,
        dcf_result: DCFResult,
        cross_check: CrossCheckResult,
        reverse_dcf: ReverseDCFResult
    ) -> List[str]:
        """Identify key risks to the valuation"""
        risks = []

        # Convergence risks
        if not cross_check.is_converged:
            risks.append(f"Valuation methods divergent ({cross_check.value_spread:.0%} spread)")

        # DCF risks
        for warning in dcf_result.warnings:
            if "CRITICAL" in warning or "WARNING" in warning:
                risks.append(warning)

        # Market expectations risk
        if reverse_dcf.is_valid:
            if reverse_dcf.market_view == "MORE_OPTIMISTIC":
                risks.append("Market expects higher growth than our model")
            elif reverse_dcf.market_view == "MORE_PESSIMISTIC":
                risks.append("Market expects lower growth - potential value trap")

        # Cross-check issues
        risks.extend(cross_check.issues_found[:3])

        return list(set(risks))[:5]  # Unique, top 5

    def _summarize_market_expectations(self, reverse_dcf: ReverseDCFResult) -> str:
        """Summarize what the market is pricing in"""
        if not reverse_dcf.is_valid:
            return "Unable to determine market expectations"

        return reverse_dcf.implied_growth_description

    def _build_summary(
        self,
        method_values: Dict[str, float],
        weights: Dict[str, float],
        consensus_fv: float,
        current_price: float,
        dcf_result: DCFResult,
        comps_result: CompsResult,
        ddm_result: DDMResult,
        reverse_dcf: ReverseDCFResult,
        cross_check: CrossCheckResult,
        broker_target: Optional[float]
    ) -> str:
        """Build comprehensive valuation summary"""
        currency = dcf_result.currency

        lines = [
            "=" * 60,
            f"VALUATION SUMMARY: {dcf_result.ticker}",
            "=" * 60,
            "",
            f"Current Price: {currency} {current_price:.2f}",
            f"Consensus Fair Value: {currency} {consensus_fv:.2f}",
            f"Implied Upside: {(consensus_fv/current_price - 1)*100:+.1f}%",
            "",
            "-" * 40,
            "METHOD BREAKDOWN:",
            "-" * 40,
        ]

        # DCF
        if 'DCF' in method_values:
            lines.append(f"DCF (Probability-Weighted): {currency} {method_values['DCF']:.2f} "
                        f"(Weight: {weights['DCF']:.0%})")
            if dcf_result.scenarios:
                for name, scenario in dcf_result.scenarios.items():
                    lines.append(f"  - {name}: {currency} {scenario.fair_value_per_share:.2f} "
                               f"({scenario.probability:.0%} prob)")

        # Comps
        if 'Comps' in method_values:
            lines.append(f"Comps Analysis: {currency} {method_values['Comps']:.2f} "
                        f"(Weight: {weights['Comps']:.0%})")
            lines.append(f"  - Peer P/E: {comps_result.median_pe:.1f}x" if comps_result.median_pe else "")
            lines.append(f"  - Peer EV/EBITDA: {comps_result.median_ev_ebitda:.1f}x"
                        if comps_result.median_ev_ebitda else "")

        # DDM
        if 'DDM' in method_values:
            lines.append(f"DDM (Gordon Growth): {currency} {method_values['DDM']:.2f} "
                        f"(Weight: {weights['DDM']:.0%})")
            lines.append(f"  - Dividend Yield: {ddm_result.dividend_yield:.2%}")
            lines.append(f"  - Dividend Growth: {ddm_result.dividend_growth_rate:.2%}")

        # Broker target
        if broker_target:
            lines.append(f"Broker Consensus: {currency} {broker_target:.2f}")

        lines.extend([
            "",
            "-" * 40,
            "CROSS-CHECK VALIDATION:",
            "-" * 40,
            f"Convergence: {cross_check.convergence_level}",
            f"Value Spread: {cross_check.value_spread:.1%}",
        ])

        if cross_check.issues_found:
            lines.append("Issues:")
            for issue in cross_check.issues_found[:3]:
                lines.append(f"  - {issue}")

        lines.extend([
            "",
            "-" * 40,
            "MARKET EXPECTATIONS (Reverse DCF):",
            "-" * 40,
            f"Implied Growth: {reverse_dcf.implied_growth_rate:.1%}",
            f"Our Base Case: {reverse_dcf.our_base_growth:.1%}",
            f"Market View: {reverse_dcf.market_view}",
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    def to_json(self, consensus: ConsensusValuation) -> str:
        """Convert consensus to JSON for storage/transmission"""
        return json.dumps({
            'ticker': consensus.ticker,
            'current_price': consensus.current_price,
            'currency': consensus.currency,
            'consensus_fair_value': consensus.consensus_fair_value,
            'fair_value_range': list(consensus.fair_value_range),
            'implied_upside': consensus.implied_upside,
            'recommendation': consensus.recommendation,
            'confidence': consensus.confidence,
            'method_values': consensus.method_values,
            'method_weights': consensus.method_weights,
            'key_drivers': consensus.key_drivers,
            'key_risks': consensus.key_risks,
            'convergence_status': consensus.convergence_status,
            'market_expectations': consensus.market_expectations
        }, indent=2)
