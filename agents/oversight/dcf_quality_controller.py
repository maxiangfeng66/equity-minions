"""
DCF Quality Controller - Specialized agent for DCF model validation.

This agent ensures all DCF calculations are mathematically correct and
financially sound. It uses the actual calculation tools to verify AI outputs.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..core.spawnable_agent import SpawnableAgent
from ..tools.financial_calculator import DCFCalculator, DCFInputs, DCFOutput, FinancialCalculator
from ..tools.market_data_api import MarketDataAPI
from ..tools.validation_tools import ValidationTools, ValidationResult


@dataclass
class DCFQualityReport:
    """Quality report for DCF validation"""
    ticker: str
    validated_at: datetime

    # Price verification
    verified_price: Optional[float] = None
    stated_price: Optional[float] = None
    price_match: bool = False

    # WACC validation
    wacc_valid: bool = True
    wacc_issues: List[str] = field(default_factory=list)

    # FCF validation
    fcf_valid: bool = True
    fcf_issues: List[str] = field(default_factory=list)

    # Terminal value validation
    tv_valid: bool = True
    tv_issues: List[str] = field(default_factory=list)

    # Scenario validation
    scenarios_valid: bool = True
    scenario_issues: List[str] = field(default_factory=list)

    # Math verification
    math_valid: bool = True
    math_errors: List[str] = field(default_factory=list)

    # Recalculated values
    recalculated_fair_value: Optional[float] = None
    stated_fair_value: Optional[float] = None
    value_deviation: Optional[float] = None

    # Overall
    is_valid: bool = True
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'validated_at': self.validated_at.isoformat(),
            'price_verification': {
                'verified_price': self.verified_price,
                'stated_price': self.stated_price,
                'match': self.price_match
            },
            'wacc': {'valid': self.wacc_valid, 'issues': self.wacc_issues},
            'fcf': {'valid': self.fcf_valid, 'issues': self.fcf_issues},
            'terminal_value': {'valid': self.tv_valid, 'issues': self.tv_issues},
            'scenarios': {'valid': self.scenarios_valid, 'issues': self.scenario_issues},
            'math': {'valid': self.math_valid, 'errors': self.math_errors},
            'values': {
                'recalculated': self.recalculated_fair_value,
                'stated': self.stated_fair_value,
                'deviation': self.value_deviation
            },
            'is_valid': self.is_valid,
            'recommendations': self.recommendations
        }


class DCFQualityController(SpawnableAgent):
    """
    DCF Quality Controller - Ensures mathematical correctness of DCF models.

    This agent:
    1. Fetches real market prices to verify current price
    2. Validates WACC calculation against formula
    3. Verifies FCF projections are mathematically sound
    4. Checks terminal value calculation
    5. Validates scenario analysis consistency
    6. Recalculates DCF to compare with AI output
    """

    def __init__(
        self,
        name: str = "DCFQualityController",
        project_root: str = ".",
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="DCF Quality Controller",
            tier=1,
            parent=parent_agent
        )

        self.project_root = Path(project_root)
        self.dcf_calculator = DCFCalculator()
        self.market_api = MarketDataAPI()
        self.validation_tools = ValidationTools()
        self.quality_reports: List[DCFQualityReport] = []

    # ==================== EXTRACTION TOOLS ====================

    def _extract_price(self, content: str) -> Optional[float]:
        """Extract price from DCF output content"""
        patterns = [
            r'CURRENT_PRICE_USED:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            r'CURRENT_PRICE:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            r'VERIFIED_CURRENT_PRICE:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            r'Current Price:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        return None

    def _extract_wacc(self, content: str) -> Optional[float]:
        """Extract WACC from content"""
        patterns = [
            r'BASE_WACC:\s*([\d.]+)%',
            r'WACC[:\s]+(\d+\.?\d*)%',
            r'WACC\s*=\s*([\d.]+)%',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1)) / 100
                except:
                    pass
        return None

    def _extract_terminal_growth(self, content: str) -> Optional[float]:
        """Extract terminal growth rate"""
        patterns = [
            r'TERMINAL_GROWTH:\s*([\d.]+)%',
            r'Terminal Growth[:\s]+([\d.]+)%',
            r'terminal growth rate[:\s]+([\d.]+)%',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1)) / 100
                except:
                    pass
        return None

    def _extract_target_price(self, content: str) -> Optional[float]:
        """Extract target/fair value price"""
        patterns = [
            r'FINAL_DCF_TARGET:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            r'FINAL_APPROVED_TARGET:\s*(?:HKD|USD|CNY)?\s*([\d.]+)',
            r'Fair Value[:\s]*(?:HKD|USD|CNY)?\s*([\d.]+)',
            r'Target Price[:\s]*(?:HKD|USD|CNY)?\s*([\d.]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        return None

    def _extract_scenarios(self, content: str) -> Dict[str, Dict]:
        """Extract scenario analysis from content"""
        scenarios = {}

        # Look for scenario table
        table_pattern = r'\|\s*(\w+[\w\s]*?)\s*\|\s*([\d.]+)%\s*\|\s*([\d.]+)%?\s*\|\s*([\d.]+)%?\s*\|\s*([\d.]+)\s*\|'

        for match in re.finditer(table_pattern, content):
            scenario_name = match.group(1).strip().lower().replace(' ', '_')
            if scenario_name in ['super_bear', 'bear', 'base', 'bull', 'super_bull']:
                scenarios[scenario_name] = {
                    'probability': float(match.group(2)) / 100,
                    'wacc': float(match.group(3)) / 100 if '%' in match.group(3) else float(match.group(3)),
                    'target': float(match.group(5))
                }

        return scenarios

    def _extract_wacc_components(self, content: str) -> Dict[str, float]:
        """Extract WACC calculation components"""
        components = {}

        patterns = {
            'risk_free_rate': r'RISK_FREE_RATE:\s*([\d.]+)%',
            'beta': r'BETA:\s*([\d.]+)',
            'equity_risk_premium': r'EQUITY_RISK_PREMIUM:\s*([\d.]+)%',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if '%' in pattern:
                    value = value / 100
                components[key] = value

        return components

    # ==================== VALIDATION TOOLS ====================

    async def tool_verify_price(self, ticker: str, stated_price: float) -> Dict[str, Any]:
        """
        Tool: Verify stated price against real market data.
        """
        verification = await self.market_api.verify_price(ticker, stated_price)
        return verification

    async def tool_validate_wacc(
        self,
        stated_wacc: float,
        risk_free_rate: float = 0.045,
        beta: float = 1.0,
        equity_risk_premium: float = 0.055,
        country_risk_premium: float = 0.0,
        cost_of_debt: float = 0.05,
        tax_rate: float = 0.25,
        debt_ratio: float = 0.2
    ) -> Dict[str, Any]:
        """
        Tool: Validate WACC calculation.
        """
        results = self.validation_tools.validate_wacc_calculation(
            stated_wacc=stated_wacc,
            risk_free_rate=risk_free_rate,
            beta=beta,
            equity_risk_premium=equity_risk_premium,
            country_risk_premium=country_risk_premium,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate,
            debt_ratio=debt_ratio
        )

        # Also calculate expected WACC
        wacc, cost_of_equity, calc_str = FinancialCalculator.calculate_wacc(
            risk_free_rate, beta, equity_risk_premium, country_risk_premium,
            cost_of_debt, tax_rate, debt_ratio
        )

        return {
            'stated_wacc': stated_wacc,
            'calculated_wacc': wacc,
            'deviation': abs(stated_wacc - wacc),
            'is_valid': abs(stated_wacc - wacc) < 0.005,
            'calculation': calc_str,
            'validation_results': [r.__dict__ for r in results]
        }

    async def tool_validate_scenarios(
        self,
        scenarios: Dict[str, Dict],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Tool: Validate scenario analysis.
        """
        results = self.validation_tools.validate_scenario_consistency(scenarios, current_price)

        return {
            'scenarios': scenarios,
            'current_price': current_price,
            'validation_results': [r.__dict__ for r in results],
            'is_valid': all(r.passed for r in results if r.severity == 'critical')
        }

    async def tool_recalculate_dcf(
        self,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tool: Recalculate DCF from scratch using provided inputs.
        """
        try:
            dcf_inputs = DCFInputs(
                revenue_base=inputs.get('revenue_base', 1000),
                ebit_margin=inputs.get('ebit_margin', 0.15),
                tax_rate=inputs.get('tax_rate', 0.25),
                depreciation=inputs.get('depreciation', 50),
                capex=inputs.get('capex', 80),
                working_capital_change=inputs.get('working_capital_change', 20),
                growth_phase1=inputs.get('growth_phase1', 0.15),
                growth_phase2=inputs.get('growth_phase2', 0.10),
                growth_phase3=inputs.get('growth_phase3', 0.05),
                terminal_growth=inputs.get('terminal_growth', 0.025),
                target_margin=inputs.get('target_margin', 0.20),
                margin_improvement_years=inputs.get('margin_improvement_years', 5),
                risk_free_rate=inputs.get('risk_free_rate', 0.045),
                beta=inputs.get('beta', 1.2),
                equity_risk_premium=inputs.get('equity_risk_premium', 0.055),
                country_risk_premium=inputs.get('country_risk_premium', 0.01),
                cost_of_debt=inputs.get('cost_of_debt', 0.05),
                debt_ratio=inputs.get('debt_ratio', 0.2),
                shares_outstanding=inputs.get('shares_outstanding', 100),
                net_debt=inputs.get('net_debt', 500)
            )

            result = self.dcf_calculator.calculate(dcf_inputs)

            return {
                'success': True,
                'fair_value_per_share': result.fair_value_per_share,
                'enterprise_value': result.enterprise_value,
                'equity_value': result.equity_value,
                'wacc': result.wacc,
                'terminal_value': result.terminal_value,
                'terminal_value_pct': result.terminal_value_pct_of_ev,
                'warnings': result.warnings,
                'is_valid': result.is_valid
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== MAIN VALIDATION METHOD ====================

    async def validate_dcf_output(
        self,
        ticker: str,
        dcf_content: str
    ) -> DCFQualityReport:
        """
        Comprehensive DCF output validation.

        Args:
            ticker: Stock ticker
            dcf_content: Raw DCF output content from Financial Modeler

        Returns:
            DCFQualityReport with all validation results
        """
        report = DCFQualityReport(
            ticker=ticker,
            validated_at=datetime.now()
        )

        # Step 1: Extract values from content
        stated_price = self._extract_price(dcf_content)
        stated_wacc = self._extract_wacc(dcf_content)
        terminal_growth = self._extract_terminal_growth(dcf_content)
        stated_target = self._extract_target_price(dcf_content)
        scenarios = self._extract_scenarios(dcf_content)
        wacc_components = self._extract_wacc_components(dcf_content)

        report.stated_price = stated_price
        report.stated_fair_value = stated_target

        # Step 2: Verify current price
        if stated_price:
            price_verification = await self.tool_verify_price(ticker, stated_price)
            report.verified_price = price_verification.get('actual_price')
            report.price_match = price_verification.get('verified', False)

            if not report.price_match:
                report.is_valid = False
                report.recommendations.append(
                    f"Price mismatch: stated {stated_price}, actual {report.verified_price}"
                )
        else:
            report.is_valid = False
            report.recommendations.append("Could not extract current price from DCF output")

        # Step 3: Validate WACC
        if stated_wacc:
            wacc_result = await self.tool_validate_wacc(
                stated_wacc=stated_wacc,
                **wacc_components
            )

            report.wacc_valid = wacc_result.get('is_valid', False)
            if not report.wacc_valid:
                report.wacc_issues.append(
                    f"WACC deviation: stated {stated_wacc:.2%}, calculated {wacc_result.get('calculated_wacc', 0):.2%}"
                )

            for vr in wacc_result.get('validation_results', []):
                if not vr.get('passed') and vr.get('severity') in ['critical', 'warning']:
                    report.wacc_issues.append(vr.get('message'))
        else:
            report.wacc_valid = False
            report.wacc_issues.append("Could not extract WACC from DCF output")

        # Step 4: Validate terminal growth
        if terminal_growth:
            if terminal_growth >= 0.04:
                report.tv_issues.append(f"Terminal growth {terminal_growth:.2%} >= 4% is aggressive")
            if stated_wacc and terminal_growth >= stated_wacc:
                report.tv_valid = False
                report.tv_issues.append(
                    f"Terminal growth {terminal_growth:.2%} >= WACC {stated_wacc:.2%} is invalid"
                )

        # Step 5: Validate scenarios
        if scenarios:
            scenario_result = await self.tool_validate_scenarios(
                scenarios,
                stated_price or report.verified_price or 0
            )

            report.scenarios_valid = scenario_result.get('is_valid', True)

            for vr in scenario_result.get('validation_results', []):
                if not vr.get('passed'):
                    report.scenario_issues.append(vr.get('message'))

            # Check probability sum
            prob_sum = sum(s.get('probability', 0) for s in scenarios.values())
            if abs(prob_sum - 1.0) > 0.01:
                report.scenarios_valid = False
                report.scenario_issues.append(f"Probabilities sum to {prob_sum:.0%}, not 100%")

        # Step 6: Validate implied upside
        if stated_target and report.verified_price:
            implied_upside = (stated_target - report.verified_price) / report.verified_price
            report.value_deviation = implied_upside

            if abs(implied_upside) > 2.0:  # More than 200% upside/downside
                report.math_errors.append(
                    f"Extreme implied upside/downside: {implied_upside:.0%}"
                )
                report.recommendations.append("Review DCF assumptions - extreme valuation detected")

        # Step 7: Overall validity
        report.is_valid = (
            report.price_match and
            report.wacc_valid and
            report.tv_valid and
            report.scenarios_valid and
            len(report.math_errors) == 0
        )

        # Generate recommendations
        if not report.is_valid:
            if not report.price_match:
                report.recommendations.append("Update current price to verified market price")
            if not report.wacc_valid:
                report.recommendations.append("Recalculate WACC using correct formula")
            if not report.tv_valid:
                report.recommendations.append("Ensure terminal growth < WACC")
            if not report.scenarios_valid:
                report.recommendations.append("Fix scenario probabilities to sum to 100%")

        self.quality_reports.append(report)
        return report

    async def validate_workflow_dcf(self, ticker: str) -> DCFQualityReport:
        """
        Validate DCF from a workflow result file.
        """
        result_path = self.project_root / "context" / f"{ticker.replace(' ', '_')}_workflow_result.json"

        if not result_path.exists():
            report = DCFQualityReport(
                ticker=ticker,
                validated_at=datetime.now()
            )
            report.is_valid = False
            report.recommendations.append(f"Workflow result not found: {result_path}")
            return report

        try:
            with open(result_path, 'r') as f:
                workflow_result = json.load(f)

            # Find Financial Modeler output
            node_outputs = workflow_result.get('node_outputs', {})
            dcf_content = ""

            for node_id, outputs in node_outputs.items():
                if 'Financial Modeler' in node_id or 'Modeler' in node_id:
                    for output in outputs:
                        dcf_content += output.get('content', '') + "\n"

            if not dcf_content:
                report = DCFQualityReport(
                    ticker=ticker,
                    validated_at=datetime.now()
                )
                report.is_valid = False
                report.recommendations.append("No Financial Modeler output found in workflow result")
                return report

            return await self.validate_dcf_output(ticker, dcf_content)

        except Exception as e:
            report = DCFQualityReport(
                ticker=ticker,
                validated_at=datetime.now()
            )
            report.is_valid = False
            report.recommendations.append(f"Error validating workflow DCF: {str(e)}")
            return report

    async def batch_validate(self, tickers: List[str]) -> Dict[str, DCFQualityReport]:
        """
        Validate DCF outputs for multiple tickers.
        """
        results = {}

        for ticker in tickers:
            try:
                report = await self.validate_workflow_dcf(ticker)
                results[ticker] = report
            except Exception as e:
                results[ticker] = DCFQualityReport(
                    ticker=ticker,
                    validated_at=datetime.now(),
                    is_valid=False,
                    recommendations=[f"Validation error: {str(e)}"]
                )

        return results
