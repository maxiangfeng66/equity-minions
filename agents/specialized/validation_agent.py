"""
Validation Agent - Validates AI outputs using mathematical tools.

This agent acts as a quality gate, verifying that AI-generated
financial analyses are mathematically correct and logically sound.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from ..core.spawnable_agent import SpawnableAgent
from ..tools.financial_calculator import FinancialCalculator
from ..tools.market_data_api import MarketDataAPI
from ..tools.validation_tools import ValidationTools, ValidationResult


@dataclass
class ValidationReport:
    """Complete validation report for an AI output"""
    ticker: str
    validated_at: datetime
    content_type: str  # 'dcf', 'debate', 'research', etc.

    # Validation results
    checks_passed: int = 0
    checks_failed: int = 0
    critical_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Extracted and verified values
    extracted_values: Dict[str, Any] = field(default_factory=dict)
    verified_values: Dict[str, Any] = field(default_factory=dict)
    corrections_needed: Dict[str, Any] = field(default_factory=dict)

    # Overall assessment
    is_valid: bool = True
    confidence: float = 1.0  # 0-1 confidence in validation

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'validated_at': self.validated_at.isoformat(),
            'content_type': self.content_type,
            'summary': {
                'checks_passed': self.checks_passed,
                'checks_failed': self.checks_failed,
                'is_valid': self.is_valid,
                'confidence': self.confidence
            },
            'critical_failures': self.critical_failures,
            'warnings': self.warnings,
            'values': {
                'extracted': self.extracted_values,
                'verified': self.verified_values,
                'corrections': self.corrections_needed
            }
        }


class ValidationAgent(SpawnableAgent):
    """
    Validation Agent - Validates AI outputs mathematically.

    This agent:
    1. Extracts numerical claims from AI outputs
    2. Verifies prices against real market data
    3. Checks mathematical calculations
    4. Validates logical consistency
    5. Produces correction suggestions

    It serves as a quality gate before any AI output is published.
    """

    def __init__(
        self,
        name: str = "ValidationAgent",
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="AI Output Validator",
            tier=2,
            parent=parent_agent
        )

        self.market_api = MarketDataAPI()
        self.fin_calc = FinancialCalculator()
        self.validation_tools = ValidationTools()

    async def validate_dcf_output(
        self,
        ticker: str,
        content: str
    ) -> ValidationReport:
        """
        Validate DCF model output from AI.

        Args:
            ticker: Stock ticker
            content: AI-generated DCF output

        Returns:
            ValidationReport with all checks
        """
        report = ValidationReport(
            ticker=ticker,
            validated_at=datetime.now(),
            content_type='dcf'
        )

        # Extract values from content
        extracted = self._extract_dcf_values(content)
        report.extracted_values = extracted

        # Verify current price
        if 'current_price' in extracted:
            verification = await self.market_api.verify_price(
                ticker, extracted['current_price']
            )

            if verification.get('verified'):
                report.checks_passed += 1
                report.verified_values['current_price'] = verification['actual_price']
            else:
                report.checks_failed += 1
                report.critical_failures.append(
                    f"Price mismatch: stated {extracted['current_price']}, actual {verification.get('actual_price')}"
                )
                report.corrections_needed['current_price'] = verification.get('actual_price')
                report.is_valid = False
        else:
            report.checks_failed += 1
            report.critical_failures.append("No current price found in DCF output")
            report.is_valid = False

        # Validate WACC if components are present
        if all(k in extracted for k in ['wacc', 'risk_free_rate', 'beta', 'equity_risk_premium']):
            expected_wacc, _, _ = self.fin_calc.calculate_wacc(
                risk_free_rate=extracted['risk_free_rate'],
                beta=extracted['beta'],
                equity_risk_premium=extracted['equity_risk_premium'],
                country_risk_premium=extracted.get('country_risk_premium', 0),
                cost_of_debt=extracted.get('cost_of_debt', 0.05),
                tax_rate=extracted.get('tax_rate', 0.25),
                debt_ratio=extracted.get('debt_ratio', 0.2)
            )

            stated_wacc = extracted['wacc']
            if abs(stated_wacc - expected_wacc) < 0.005:
                report.checks_passed += 1
                report.verified_values['wacc'] = expected_wacc
            else:
                report.checks_failed += 1
                report.warnings.append(
                    f"WACC mismatch: stated {stated_wacc:.2%}, calculated {expected_wacc:.2%}"
                )
                report.corrections_needed['wacc'] = expected_wacc

        # Validate terminal growth
        if 'terminal_growth' in extracted:
            tg = extracted['terminal_growth']
            if tg >= 0.04:
                report.warnings.append(f"Terminal growth {tg:.2%} >= 4% is aggressive")

            if 'wacc' in extracted and tg >= extracted['wacc']:
                report.checks_failed += 1
                report.critical_failures.append(
                    f"Terminal growth {tg:.2%} >= WACC {extracted['wacc']:.2%} is invalid"
                )
                report.is_valid = False
            else:
                report.checks_passed += 1

        # Validate scenario probabilities
        if 'scenarios' in extracted:
            prob_sum = sum(s.get('probability', 0) for s in extracted['scenarios'].values())
            if abs(prob_sum - 1.0) < 0.01:
                report.checks_passed += 1
            else:
                report.checks_failed += 1
                report.warnings.append(f"Scenario probabilities sum to {prob_sum:.0%}, not 100%")

        # Validate implied upside reasonableness
        if 'target_price' in extracted and 'current_price' in extracted:
            upside = (extracted['target_price'] - extracted['current_price']) / extracted['current_price']

            if abs(upside) > 2.0:
                report.checks_failed += 1
                report.warnings.append(f"Extreme implied upside: {upside:.0%}")

            if abs(upside) <= 2.0:
                report.checks_passed += 1

        # Calculate confidence
        total_checks = report.checks_passed + report.checks_failed
        if total_checks > 0:
            report.confidence = report.checks_passed / total_checks

        return report

    async def validate_debate_output(
        self,
        ticker: str,
        content: str
    ) -> ValidationReport:
        """
        Validate debate output - check for price consistency.

        Args:
            ticker: Stock ticker
            content: AI-generated debate output

        Returns:
            ValidationReport
        """
        report = ValidationReport(
            ticker=ticker,
            validated_at=datetime.now(),
            content_type='debate'
        )

        # Get verified price
        quote = await self.market_api.get_quote(ticker)
        verified_price = quote.price if quote else None

        if verified_price:
            report.verified_values['current_price'] = verified_price

        # Check for price mentions in content
        price_pattern = r'(?:current|stock|share)\s+price[:\s]+(?:HKD|USD|CNY)?\s*([\d.]+)'
        price_mentions = re.findall(price_pattern, content, re.IGNORECASE)

        if price_mentions:
            for mentioned_price in price_mentions:
                try:
                    price = float(mentioned_price)
                    if verified_price:
                        deviation = abs(price - verified_price) / verified_price
                        if deviation > 0.05:
                            report.warnings.append(
                                f"Price {price} differs from verified {verified_price} by {deviation:.0%}"
                            )
                except:
                    pass

        # Check for verified price usage
        if 'VERIFIED_CURRENT_PRICE' in content or 'CURRENT PRICE USED:' in content:
            report.checks_passed += 1
        else:
            report.warnings.append("Debate output may not be using verified price")

        # Check for required sections
        required_sections = ['bull', 'bear', 'argument', 'point']
        sections_found = sum(1 for s in required_sections if s.lower() in content.lower())

        if sections_found >= 3:
            report.checks_passed += 1
        else:
            report.warnings.append("Debate may be missing bull/bear arguments")

        return report

    async def validate_research_output(
        self,
        ticker: str,
        content: str
    ) -> ValidationReport:
        """
        Validate research output for data accuracy.

        Args:
            ticker: Stock ticker
            content: AI-generated research output

        Returns:
            ValidationReport
        """
        report = ValidationReport(
            ticker=ticker,
            validated_at=datetime.now(),
            content_type='research'
        )

        # Fetch actual data
        package_data = await self.market_api.get_quote(ticker)

        if package_data:
            report.verified_values['price'] = package_data.price
            report.verified_values['market_cap'] = package_data.market_cap

            # Check market cap mentions
            mcap_pattern = r'market\s+cap[a-z]*[:\s]+(?:\$|HKD|USD)?\s*([\d.]+)\s*(billion|B|million|M|trillion|T)?'
            mcap_matches = re.findall(mcap_pattern, content, re.IGNORECASE)

            if mcap_matches:
                for value, unit in mcap_matches:
                    try:
                        mcap = float(value)
                        unit = unit.lower() if unit else ''

                        if 'trillion' in unit or unit == 't':
                            mcap *= 1e12
                        elif 'billion' in unit or unit == 'b':
                            mcap *= 1e9
                        elif 'million' in unit or unit == 'm':
                            mcap *= 1e6

                        # Compare to actual
                        if package_data.market_cap > 0:
                            deviation = abs(mcap - package_data.market_cap) / package_data.market_cap
                            if deviation > 0.2:
                                report.warnings.append(
                                    f"Market cap {mcap:,.0f} differs from actual {package_data.market_cap:,.0f}"
                                )
                    except:
                        pass

        # Check for company name consistency
        # This would require knowing the expected company name

        return report

    async def validate_full_workflow(
        self,
        ticker: str,
        workflow_result: Dict
    ) -> Dict[str, ValidationReport]:
        """
        Validate complete workflow output.

        Args:
            ticker: Stock ticker
            workflow_result: Complete workflow result dict

        Returns:
            Dict mapping node_id to ValidationReport
        """
        reports = {}

        node_outputs = workflow_result.get('node_outputs', {})

        for node_id, outputs in node_outputs.items():
            content = '\n'.join(o.get('content', '') for o in outputs)

            if 'Financial Modeler' in node_id or 'DCF' in node_id:
                reports[node_id] = await self.validate_dcf_output(ticker, content)
            elif 'Advocate' in node_id or 'Debate' in node_id:
                reports[node_id] = await self.validate_debate_output(ticker, content)
            elif 'Data' in node_id or 'Research' in node_id:
                reports[node_id] = await self.validate_research_output(ticker, content)

        return reports

    def _extract_dcf_values(self, content: str) -> Dict[str, Any]:
        """Extract numerical values from DCF content"""
        values = {}

        patterns = {
            'current_price': [
                r'CURRENT_PRICE_USED:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
                r'CURRENT_PRICE:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            ],
            'target_price': [
                r'FINAL_DCF_TARGET:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
                r'FINAL_APPROVED_TARGET:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            ],
            'wacc': [
                r'BASE_WACC:\s*([\d.]+)%',
                r'WACC[:\s]+([\d.]+)%',
            ],
            'risk_free_rate': [
                r'RISK_FREE_RATE:\s*([\d.]+)%',
            ],
            'beta': [
                r'BETA:\s*([\d.]+)',
            ],
            'equity_risk_premium': [
                r'EQUITY_RISK_PREMIUM:\s*([\d.]+)%',
            ],
            'terminal_growth': [
                r'TERMINAL_GROWTH:\s*([\d.]+)%',
            ],
        }

        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        # Convert percentages to decimals
                        if '%' in pattern and key != 'current_price' and key != 'target_price':
                            value = value / 100
                        values[key] = value
                        break
                    except:
                        pass

        # Extract scenarios
        scenarios = {}
        table_pattern = r'\|\s*(\w+[\w\s]*?)\s*\|\s*([\d.]+)%\s*\|\s*([\d.]+)%?\s*\|\s*[\w$]+\s*([\d.]+)'

        for match in re.finditer(table_pattern, content):
            name = match.group(1).strip().lower().replace(' ', '_')
            if name in ['super_bear', 'bear', 'base', 'bull', 'super_bull']:
                scenarios[name] = {
                    'probability': float(match.group(2)) / 100,
                    'target': float(match.group(4))
                }

        if scenarios:
            values['scenarios'] = scenarios

        return values

    def format_validation_summary(self, reports: Dict[str, ValidationReport]) -> str:
        """Format validation reports into summary string"""
        total_passed = sum(r.checks_passed for r in reports.values())
        total_failed = sum(r.checks_failed for r in reports.values())
        all_valid = all(r.is_valid for r in reports.values())

        output = f"""
============================================
VALIDATION SUMMARY
============================================
Total Checks Passed: {total_passed}
Total Checks Failed: {total_failed}
Overall Valid: {'YES' if all_valid else 'NO'}
============================================

"""

        for node_id, report in reports.items():
            status = 'VALID' if report.is_valid else 'INVALID'
            output += f"\n{node_id}: {status}\n"

            if report.critical_failures:
                output += "  CRITICAL:\n"
                for cf in report.critical_failures:
                    output += f"    - {cf}\n"

            if report.warnings:
                output += "  WARNINGS:\n"
                for w in report.warnings:
                    output += f"    - {w}\n"

            if report.corrections_needed:
                output += "  CORRECTIONS NEEDED:\n"
                for k, v in report.corrections_needed.items():
                    output += f"    - {k}: use {v}\n"

        return output
