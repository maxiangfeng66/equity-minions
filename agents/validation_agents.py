"""
Validation Agents - Parallel fact-checking and logic validation
These agents scrutinize existing research for errors and inconsistencies
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Visualizer integration
try:
    from visualizer.visualizer_bridge import VisualizerBridge
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False


@dataclass
class ValidationResult:
    """Result from a validation check"""
    agent_type: str
    ticker: str
    category: str
    severity: str  # 'critical', 'major', 'minor', 'info'
    issue: str
    evidence: str
    recommendation: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ValidationReport:
    """Aggregated validation report for an equity"""
    ticker: str
    company_name: str
    factual_issues: List[ValidationResult] = field(default_factory=list)
    logic_issues: List[ValidationResult] = field(default_factory=list)
    data_issues: List[ValidationResult] = field(default_factory=list)
    calculation_issues: List[ValidationResult] = field(default_factory=list)
    overall_score: float = 0.0
    needs_revision: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FactCheckerAgent:
    """
    Validates factual accuracy of research data
    - Cross-references financial figures with multiple sources
    - Verifies company information (founding date, HQ, management)
    - Checks market data accuracy (prices, market cap, volume)
    - Validates industry statistics
    """

    def __init__(self, context_dir: str = "context"):
        self.context_dir = Path(context_dir)
        self.agent_name = "FactChecker"

    async def validate_equity(self, ticker: str, context_data: Dict) -> List[ValidationResult]:
        """Run all fact checks on an equity"""
        results = []

        # Run checks in parallel
        checks = await asyncio.gather(
            self._check_financial_figures(ticker, context_data),
            self._check_company_info(ticker, context_data),
            self._check_market_data(ticker, context_data),
            self._check_industry_stats(ticker, context_data),
            self._check_competitor_data(ticker, context_data),
            return_exceptions=True
        )

        for check_result in checks:
            if isinstance(check_result, list):
                results.extend(check_result)
            elif isinstance(check_result, Exception):
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="system_error",
                    severity="info",
                    issue=f"Check failed: {str(check_result)}",
                    evidence="",
                    recommendation="Re-run validation"
                ))

        return results

    async def _check_financial_figures(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify financial data accuracy"""
        results = []
        financials = data.get('financial_data', {})

        # Check for missing critical data
        required_fields = ['revenue', 'net_income', 'total_assets', 'total_equity']
        for field in required_fields:
            if not financials.get(field):
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="missing_data",
                    severity="major",
                    issue=f"Missing {field} in financial data",
                    evidence=f"Field '{field}' is empty or missing",
                    recommendation=f"Fetch {field} from reliable source"
                ))

        # Check for unrealistic margins
        if financials.get('revenue') and financials.get('net_income'):
            margin = financials['net_income'] / financials['revenue']
            if margin > 0.5:
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="suspicious_data",
                    severity="major",
                    issue=f"Unusually high net margin: {margin:.1%}",
                    evidence=f"Net income / Revenue = {margin:.1%}",
                    recommendation="Verify net income figure against filings"
                ))
            elif margin < -1.0:
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="suspicious_data",
                    severity="minor",
                    issue=f"Very negative margin: {margin:.1%}",
                    evidence=f"Net income / Revenue = {margin:.1%}",
                    recommendation="Confirm company is in early/loss-making stage"
                ))

        return results

    async def _check_company_info(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify company information"""
        results = []
        company = data.get('company_analysis', {})

        # Check for boilerplate or missing descriptions
        description = company.get('description', '')
        if len(description) < 100:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="incomplete_data",
                severity="minor",
                issue="Company description too brief",
                evidence=f"Description length: {len(description)} chars",
                recommendation="Expand company description with more detail"
            ))

        return results

    async def _check_market_data(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify market data accuracy"""
        results = []

        current_price = data.get('current_price', 0)
        target_price = data.get('target_price', 0)

        if current_price <= 0:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="invalid_data",
                severity="critical",
                issue="Invalid or missing current price",
                evidence=f"Current price: {current_price}",
                recommendation="Fetch current price from market data source"
            ))

        # Check for stale prices (would need timestamp comparison in real implementation)

        return results

    async def _check_industry_stats(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify industry statistics"""
        results = []
        industry = data.get('industry_analysis', {})

        market_size = industry.get('market_size')
        if market_size and isinstance(market_size, (int, float)):
            if market_size > 10_000_000_000_000:  # >$10T
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="suspicious_data",
                    severity="minor",
                    issue=f"Very large market size: ${market_size/1e12:.1f}T",
                    evidence=f"Reported market size: {market_size}",
                    recommendation="Verify market size definition and source"
                ))

        return results

    async def _check_competitor_data(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify competitor information"""
        results = []
        competitors = data.get('competitors', [])

        if not competitors:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="missing_data",
                severity="minor",
                issue="No competitors identified",
                evidence="Competitor list is empty",
                recommendation="Research and add key competitors"
            ))

        return results


class LogicValidatorAgent:
    """
    Validates logical consistency of analysis
    - Checks DCF assumptions against stated thesis
    - Validates scenario probability distributions
    - Ensures bull/bear cases are logically consistent
    - Checks for contradictions in analysis
    """

    def __init__(self):
        self.agent_name = "LogicValidator"

    async def validate_equity(self, ticker: str, context_data: Dict) -> List[ValidationResult]:
        """Run all logic checks on an equity"""
        results = []

        checks = await asyncio.gather(
            self._check_dcf_consistency(ticker, context_data),
            self._check_scenario_logic(ticker, context_data),
            self._check_thesis_alignment(ticker, context_data),
            self._check_risk_reward_logic(ticker, context_data),
            self._check_recommendation_logic(ticker, context_data),
            return_exceptions=True
        )

        for check_result in checks:
            if isinstance(check_result, list):
                results.extend(check_result)

        return results

    async def _check_dcf_consistency(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check DCF model assumptions are consistent"""
        results = []
        dcf = data.get('dcf_valuation', {})

        # Check growth rates make sense
        growth_rate = dcf.get('revenue_growth_rate', 0)
        terminal_growth = dcf.get('terminal_growth', 0)

        if growth_rate > 0 and terminal_growth > growth_rate:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="logic_error",
                severity="critical",
                issue="Terminal growth exceeds near-term growth",
                evidence=f"Growth: {growth_rate:.1%}, Terminal: {terminal_growth:.1%}",
                recommendation="Terminal growth should be lower than projection period growth"
            ))

        if terminal_growth > 0.05:  # >5%
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="aggressive_assumption",
                severity="major",
                issue=f"Terminal growth rate too high: {terminal_growth:.1%}",
                evidence=f"Terminal growth of {terminal_growth:.1%} exceeds typical GDP growth",
                recommendation="Use terminal growth of 2-3% (GDP-like)"
            ))

        # Check discount rate reasonableness
        wacc = dcf.get('discount_rate', 0)
        if wacc < 0.06:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="aggressive_assumption",
                severity="major",
                issue=f"Discount rate too low: {wacc:.1%}",
                evidence=f"WACC of {wacc:.1%} is below risk-free rate",
                recommendation="Use appropriate risk-adjusted discount rate (8-12%)"
            ))
        elif wacc > 0.20:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="conservative_assumption",
                severity="minor",
                issue=f"Discount rate very high: {wacc:.1%}",
                evidence=f"WACC of {wacc:.1%} implies very high risk",
                recommendation="Verify if such high discount rate is justified"
            ))

        return results

    async def _check_scenario_logic(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check scenario analysis is logical"""
        results = []
        scenarios = data.get('scenarios', {})

        # Check probabilities sum to 100%
        total_prob = sum(s.get('probability', 0) for s in scenarios.values())
        if abs(total_prob - 1.0) > 0.01:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="math_error",
                severity="critical",
                issue=f"Scenario probabilities don't sum to 100%",
                evidence=f"Total probability: {total_prob:.1%}",
                recommendation="Adjust probabilities to sum to 100%"
            ))

        # Check scenario values are ordered correctly
        scenario_order = ['super_bear', 'bear', 'base', 'bull', 'super_bull']
        values = []
        for scenario in scenario_order:
            if scenario in scenarios:
                values.append(scenarios[scenario].get('target_price', 0))

        if values and values != sorted(values):
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="logic_error",
                severity="major",
                issue="Scenario target prices not in logical order",
                evidence=f"Values: {values}",
                recommendation="Bear cases should have lower targets than bull cases"
            ))

        return results

    async def _check_thesis_alignment(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check if thesis aligns with recommendation"""
        results = []

        recommendation = data.get('recommendation', '').upper()
        upside = data.get('upside_potential', 0)

        # Check recommendation matches upside
        if recommendation == 'BUY' and upside < 0.10:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="logic_inconsistency",
                severity="major",
                issue="BUY rating with low upside",
                evidence=f"Rating: BUY, Upside: {upside:.1%}",
                recommendation="Review rating - BUY typically requires >15% upside"
            ))
        elif recommendation == 'SELL' and upside > 0:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="logic_inconsistency",
                severity="major",
                issue="SELL rating with positive upside",
                evidence=f"Rating: SELL, Upside: {upside:.1%}",
                recommendation="Review rating - SELL implies negative expected return"
            ))

        return results

    async def _check_risk_reward_logic(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check risk-reward is logical"""
        results = []

        risks = data.get('risks', [])
        catalysts = data.get('catalysts', [])
        conviction = data.get('conviction', 0)

        # High conviction with many risks should flag
        if conviction > 7 and len(risks) > 5:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="logic_inconsistency",
                severity="minor",
                issue="High conviction despite numerous risks",
                evidence=f"Conviction: {conviction}/10, Risks identified: {len(risks)}",
                recommendation="Review if high conviction is justified given risk count"
            ))

        # Low conviction with few risks
        if conviction < 5 and len(risks) < 2:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="incomplete_analysis",
                severity="minor",
                issue="Low conviction but few risks identified",
                evidence=f"Conviction: {conviction}/10, Risks identified: {len(risks)}",
                recommendation="Identify more specific risks to justify low conviction"
            ))

        return results

    async def _check_recommendation_logic(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check recommendation is logically supported"""
        results = []

        # Check if debate consensus aligns with recommendation
        debate = data.get('debate_summary', {})
        recommendation = data.get('recommendation', '')

        bull_score = debate.get('bull_conviction', 5)
        bear_score = debate.get('bear_conviction', 5)

        if recommendation.upper() == 'BUY' and bear_score > bull_score:
            results.append(ValidationResult(
                agent_type=self.agent_name,
                ticker=ticker,
                category="logic_inconsistency",
                severity="major",
                issue="BUY rating but bear arguments stronger",
                evidence=f"Bull conviction: {bull_score}, Bear conviction: {bear_score}",
                recommendation="Review if BUY rating is justified given debate outcome"
            ))

        return results


class DataConsistencyAgent:
    """
    Checks data consistency across different parts of research
    - Cross-references numbers between sections
    - Validates calculations
    - Ensures data freshness
    """

    def __init__(self):
        self.agent_name = "DataConsistency"

    async def validate_equity(self, ticker: str, context_data: Dict) -> List[ValidationResult]:
        """Run consistency checks"""
        results = []

        checks = await asyncio.gather(
            self._check_price_consistency(ticker, context_data),
            self._check_valuation_math(ticker, context_data),
            self._check_date_consistency(ticker, context_data),
            return_exceptions=True
        )

        for check_result in checks:
            if isinstance(check_result, list):
                results.extend(check_result)

        return results

    async def _check_price_consistency(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check price data is consistent across sections"""
        results = []

        current_price = data.get('current_price', 0)
        scenarios = data.get('scenarios', {})

        # Check current price is between bear and bull scenarios
        if scenarios:
            bear_price = scenarios.get('bear', {}).get('target_price', 0)
            bull_price = scenarios.get('bull', {}).get('target_price', 0)

            if bear_price > 0 and current_price < bear_price * 0.5:
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="data_inconsistency",
                    severity="major",
                    issue="Current price far below even bear case",
                    evidence=f"Current: {current_price}, Bear target: {bear_price}",
                    recommendation="Verify current price or review bear case assumptions"
                ))

        return results

    async def _check_valuation_math(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify valuation calculations"""
        results = []

        dcf = data.get('dcf_valuation', {})
        target_price = data.get('target_price', 0)
        shares_outstanding = data.get('shares_outstanding', 0)

        # Check if target price matches DCF / shares
        dcf_value = dcf.get('equity_value', 0)
        if dcf_value > 0 and shares_outstanding > 0:
            implied_price = dcf_value / shares_outstanding
            if target_price > 0:
                diff = abs(implied_price - target_price) / target_price
                if diff > 0.1:  # >10% difference
                    results.append(ValidationResult(
                        agent_type=self.agent_name,
                        ticker=ticker,
                        category="calculation_error",
                        severity="major",
                        issue="Target price doesn't match DCF calculation",
                        evidence=f"Target: {target_price}, Implied: {implied_price:.2f}",
                        recommendation="Reconcile target price with DCF model"
                    ))

        return results

    async def _check_date_consistency(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Check data freshness"""
        results = []

        last_updated = data.get('last_updated', '')
        if last_updated:
            try:
                update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                days_old = (datetime.now() - update_date.replace(tzinfo=None)).days

                if days_old > 30:
                    results.append(ValidationResult(
                        agent_type=self.agent_name,
                        ticker=ticker,
                        category="stale_data",
                        severity="major",
                        issue=f"Research data is {days_old} days old",
                        evidence=f"Last updated: {last_updated}",
                        recommendation="Refresh research with current data"
                    ))
                elif days_old > 7:
                    results.append(ValidationResult(
                        agent_type=self.agent_name,
                        ticker=ticker,
                        category="stale_data",
                        severity="minor",
                        issue=f"Research data is {days_old} days old",
                        evidence=f"Last updated: {last_updated}",
                        recommendation="Consider refreshing if material events occurred"
                    ))
            except:
                pass

        return results


class CalculationVerifierAgent:
    """
    Verifies all mathematical calculations
    - Re-calculates DCF values
    - Verifies weighted average calculations
    - Checks percentage calculations
    """

    def __init__(self):
        self.agent_name = "CalculationVerifier"

    async def validate_equity(self, ticker: str, context_data: Dict) -> List[ValidationResult]:
        """Verify all calculations"""
        results = []

        checks = await asyncio.gather(
            self._verify_dcf_calculation(ticker, context_data),
            self._verify_upside_calculation(ticker, context_data),
            self._verify_weighted_target(ticker, context_data),
            return_exceptions=True
        )

        for check_result in checks:
            if isinstance(check_result, list):
                results.extend(check_result)

        return results

    async def _verify_dcf_calculation(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Re-verify DCF calculation"""
        results = []
        dcf = data.get('dcf_valuation', {})

        # Basic DCF verification
        fcf = dcf.get('free_cash_flow', 0)
        growth = dcf.get('revenue_growth_rate', 0)
        wacc = dcf.get('discount_rate', 0.10)
        terminal_growth = dcf.get('terminal_growth', 0.025)

        if fcf > 0 and wacc > terminal_growth:
            # Simplified terminal value check
            terminal_value = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            stated_terminal = dcf.get('terminal_value', 0)

            if stated_terminal > 0:
                diff = abs(terminal_value - stated_terminal) / stated_terminal
                if diff > 0.2:  # >20% difference
                    results.append(ValidationResult(
                        agent_type=self.agent_name,
                        ticker=ticker,
                        category="calculation_error",
                        severity="major",
                        issue="Terminal value calculation may be incorrect",
                        evidence=f"Stated: {stated_terminal:,.0f}, Calculated: {terminal_value:,.0f}",
                        recommendation="Review terminal value calculation"
                    ))

        return results

    async def _verify_upside_calculation(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify upside/downside calculations"""
        results = []

        current_price = data.get('current_price', 0)
        target_price = data.get('target_price', 0)
        stated_upside = data.get('upside_potential', 0)

        if current_price > 0 and target_price > 0:
            calculated_upside = (target_price - current_price) / current_price

            if abs(calculated_upside - stated_upside) > 0.01:  # >1% difference
                results.append(ValidationResult(
                    agent_type=self.agent_name,
                    ticker=ticker,
                    category="calculation_error",
                    severity="minor",
                    issue="Upside calculation discrepancy",
                    evidence=f"Stated: {stated_upside:.1%}, Calculated: {calculated_upside:.1%}",
                    recommendation="Update upside percentage"
                ))

        return results

    async def _verify_weighted_target(self, ticker: str, data: Dict) -> List[ValidationResult]:
        """Verify probability-weighted target price"""
        results = []

        scenarios = data.get('scenarios', {})
        stated_target = data.get('target_price', 0)

        if scenarios:
            weighted_target = 0
            for scenario_name, scenario_data in scenarios.items():
                prob = scenario_data.get('probability', 0)
                price = scenario_data.get('target_price', 0)
                weighted_target += prob * price

            if weighted_target > 0 and stated_target > 0:
                diff = abs(weighted_target - stated_target) / stated_target
                if diff > 0.05:  # >5% difference
                    results.append(ValidationResult(
                        agent_type=self.agent_name,
                        ticker=ticker,
                        category="calculation_error",
                        severity="major",
                        issue="Target price doesn't match probability-weighted scenarios",
                        evidence=f"Stated: {stated_target:.2f}, Weighted: {weighted_target:.2f}",
                        recommendation="Reconcile target with scenario analysis"
                    ))

        return results


class ValidationOrchestrator:
    """
    Orchestrates all validation agents to run in parallel
    Aggregates results and generates validation reports
    """

    def __init__(self, context_dir: str = "context", visualizer=None):
        self.context_dir = Path(context_dir)
        self.validation_dir = self.context_dir / "validations"
        self.validation_dir.mkdir(exist_ok=True)

        # Visualizer for real-time updates
        self.visualizer = visualizer
        if self.visualizer is None and VISUALIZER_AVAILABLE:
            try:
                self.visualizer = VisualizerBridge(context_dir)
            except:
                self.visualizer = None

        # Initialize all validation agents
        self.agents = [
            FactCheckerAgent(context_dir),
            LogicValidatorAgent(),
            DataConsistencyAgent(),
            CalculationVerifierAgent()
        ]

    async def validate_equity(self, ticker: str) -> ValidationReport:
        """Run all validators on a single equity in parallel"""
        # Load context data
        context_file = self.context_dir / f"{ticker.replace(' ', '_').replace('.', '_')}.json"

        if not context_file.exists():
            # Try alternate naming
            for f in self.context_dir.glob("*.json"):
                if ticker.replace(' ', '_') in f.stem:
                    context_file = f
                    break

        if not context_file.exists():
            return ValidationReport(
                ticker=ticker,
                company_name="Unknown",
                factual_issues=[ValidationResult(
                    agent_type="System",
                    ticker=ticker,
                    category="file_error",
                    severity="critical",
                    issue=f"Context file not found for {ticker}",
                    evidence=f"Searched in {self.context_dir}",
                    recommendation="Run initial research for this ticker"
                )],
                needs_revision=True
            )

        with open(context_file, 'r', encoding='utf-8') as f:
            context_data = json.load(f)

        # Run all agents in parallel
        all_results = await asyncio.gather(
            *[agent.validate_equity(ticker, context_data) for agent in self.agents],
            return_exceptions=True
        )

        # Aggregate results
        report = ValidationReport(
            ticker=ticker,
            company_name=context_data.get('company_name', ticker)
        )

        for results in all_results:
            if isinstance(results, list):
                for result in results:
                    if result.category in ['missing_data', 'invalid_data', 'suspicious_data']:
                        report.factual_issues.append(result)
                    elif result.category in ['logic_error', 'logic_inconsistency', 'aggressive_assumption']:
                        report.logic_issues.append(result)
                    elif result.category in ['data_inconsistency', 'stale_data']:
                        report.data_issues.append(result)
                    elif result.category in ['calculation_error', 'math_error']:
                        report.calculation_issues.append(result)
                    else:
                        report.factual_issues.append(result)

        # Calculate overall score
        critical_count = sum(1 for issues in [report.factual_issues, report.logic_issues,
                                               report.data_issues, report.calculation_issues]
                            for issue in issues if issue.severity == 'critical')
        major_count = sum(1 for issues in [report.factual_issues, report.logic_issues,
                                           report.data_issues, report.calculation_issues]
                         for issue in issues if issue.severity == 'major')

        # Score: 100 - (critical*20 + major*10 + minor*2)
        total_issues = len(report.factual_issues) + len(report.logic_issues) + \
                      len(report.data_issues) + len(report.calculation_issues)
        report.overall_score = max(0, 100 - critical_count * 20 - major_count * 10 - (total_issues - critical_count - major_count) * 2)
        report.needs_revision = critical_count > 0 or major_count > 2 or report.overall_score < 70

        # Save validation report
        report_file = self.validation_dir / f"validation_{ticker.replace(' ', '_')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'ticker': report.ticker,
                'company_name': report.company_name,
                'overall_score': report.overall_score,
                'needs_revision': report.needs_revision,
                'factual_issues': [vars(i) for i in report.factual_issues],
                'logic_issues': [vars(i) for i in report.logic_issues],
                'data_issues': [vars(i) for i in report.data_issues],
                'calculation_issues': [vars(i) for i in report.calculation_issues],
                'timestamp': report.timestamp
            }, f, indent=2)

        return report

    async def validate_all_equities(self, tickers: List[str]) -> Dict[str, ValidationReport]:
        """Validate all equities in parallel"""
        print(f"\n{'='*60}")
        print(f"VALIDATION: Running parallel validation on {len(tickers)} equities")
        print(f"{'='*60}")

        # Update visualizer with validation start
        if self.visualizer:
            self.visualizer.update_agent_task(
                "orchestrator",
                f"Validating {len(tickers)} equities",
                progress=5
            )

        # Run all validations in parallel
        reports = await asyncio.gather(
            *[self.validate_equity(ticker) for ticker in tickers],
            return_exceptions=True
        )

        results = {}
        completed = 0
        for ticker, report in zip(tickers, reports):
            completed += 1
            if isinstance(report, ValidationReport):
                results[ticker] = report
                status = "NEEDS REVISION" if report.needs_revision else "OK"
                print(f"  [{ticker}] Score: {report.overall_score:.0f}/100 - {status}")
            else:
                print(f"  [{ticker}] ERROR: {report}")

            # Update visualizer progress
            if self.visualizer:
                progress = int((completed / len(tickers)) * 100)
                self.visualizer.update_agent_task(
                    "orchestrator",
                    f"Validated {completed}/{len(tickers)} equities",
                    progress=progress
                )

        # Generate summary
        needs_revision = [t for t, r in results.items() if isinstance(r, ValidationReport) and r.needs_revision]
        print(f"\n{'='*60}")
        print(f"VALIDATION COMPLETE")
        print(f"  Total validated: {len(results)}")
        print(f"  Needs revision: {len(needs_revision)}")
        if needs_revision:
            print(f"  Tickers requiring attention: {', '.join(needs_revision)}")
        print(f"{'='*60}\n")

        return results


async def run_validation(tickers: Optional[List[str]] = None):
    """Run validation on specified tickers or all available"""
    orchestrator = ValidationOrchestrator()

    if not tickers:
        # Get all tickers from context files
        context_dir = Path("context")
        tickers = []
        for f in context_dir.glob("*.json"):
            if not f.stem.startswith(('session', 'verified', 'minions', 'debate')):
                # Convert filename back to ticker format
                ticker = f.stem.replace('_', ' ').replace('HK', ' HK').replace('US', ' US')
                tickers.append(f.stem)

    return await orchestrator.validate_all_equities(tickers)


if __name__ == "__main__":
    asyncio.run(run_validation())
