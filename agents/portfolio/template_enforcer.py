"""
Template Enforcer Agent

Ensures all HTML reports follow the canonical template with consistent
styling, structure, and content. Performs pre-generation and post-generation
validation.
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class IssueSeverity(Enum):
    CRITICAL = "critical"  # Blocks publication
    WARNING = "warning"    # Should fix
    INFO = "info"          # Nice to fix


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a report"""
    section: str
    issue_type: str  # 'missing', 'empty', 'malformed', 'inconsistent'
    description: str
    severity: IssueSeverity
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of template validation"""
    is_valid: bool
    ticker: str
    issues: List[ValidationIssue] = field(default_factory=list)
    placeholder_coverage: float = 0.0  # 0-100%
    section_completeness: Dict[str, float] = field(default_factory=dict)
    consistency_score: float = 0.0  # 0-100
    template_compliance: float = 0.0  # 0-100%

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    @property
    def warning_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]


class TemplateEnforcer:
    """
    Enforces template consistency across all equity research reports.

    Two validation modes:
    1. Pre-generation: Validates context has required data fields
    2. Post-generation: Validates HTML output matches template
    """

    # Required sections in detailed_report_template.html
    REQUIRED_SECTIONS = [
        'executive-summary',
        'industry-analysis',
        'company-analysis',
        'financial-data',
        'dcf-valuation',
        'scenarios',
        'risks',
        'recommendation',
        'debate-log'
    ]

    # Required placeholders by section
    REQUIRED_PLACEHOLDERS = {
        'header': [
            'TICKER', 'COMPANY_NAME', 'SECTOR', 'EXCHANGE',
            'RATING', 'RATING_CLASS', 'CURRENT_PRICE', 'CURRENCY'
        ],
        'executive-summary': [
            'EXECUTIVE_SUMMARY_TEXT', 'INVESTMENT_THESIS',
            'KEY_HIGHLIGHTS', 'TARGET_LOW', 'TARGET_BASE', 'TARGET_HIGH'
        ],
        'industry-analysis': [
            'INDUSTRY_NAME', 'MARKET_SIZE_CURRENT', 'MARKET_SIZE_PROJECTED',
            'INDUSTRY_CAGR', 'INDUSTRY_DRIVERS'
        ],
        'company-analysis': [
            'COMPANY_ANALYSIS_CONTENT', 'COMPETITIVE_ADVANTAGES'
        ],
        'financial-data': [
            'FINANCIAL_CURRENCY', 'FINANCIAL_YEARS_HEADER',
            'FINANCIAL_DATA_ROWS', 'VALUATION_METRICS'
        ],
        'dcf-valuation': [
            'DCF_METHODOLOGY', 'FORECAST_PERIOD', 'TERMINAL_GROWTH',
            'WACC_RANGE', 'DCF_PROJECTIONS'
        ],
        'scenarios': [
            'SCENARIO_CARDS', 'PWV'
        ],
        'risks': [
            'RISK_SECTIONS'
        ],
        'recommendation': [
            'INVESTMENT_RATIONALE', 'CATALYSTS_ROWS', 'MONITORING_METRICS'
        ],
        'debate-log': [
            'DEBATE_ROUNDS', 'CONSENSUS_POINTS', 'DISAGREEMENT_POINTS'
        ]
    }

    # CSS color scheme requirements (dark theme)
    REQUIRED_COLORS = {
        'background_primary': '#0d1117',
        'background_secondary': '#161b22',
        'background_tertiary': '#21262d',
        'text_primary': '#c9d1d9',
        'text_secondary': '#8b949e',
        'accent_blue': '#58a6ff',
        'accent_green': '#3fb950',
        'accent_red': '#f85149',
        'border': '#30363d'
    }

    # Scenario requirements
    REQUIRED_SCENARIOS = ['super_bear', 'bear', 'base', 'bull', 'super_bull']
    SCENARIO_PROBABILITIES = {
        'super_bear': 0.05,
        'bear': 0.20,
        'base': 0.50,
        'bull': 0.20,
        'super_bull': 0.05
    }

    def __init__(self, template_path: Optional[str] = None):
        self.template_path = Path(template_path) if template_path else None
        self.template_html = ""
        self.all_placeholders = set()

        if self.template_path and self.template_path.exists():
            self._load_template()

    def _load_template(self):
        """Load and parse the canonical template"""
        with open(self.template_path, 'r', encoding='utf-8') as f:
            self.template_html = f.read()
        # Extract all placeholders
        self.all_placeholders = set(re.findall(r'\{\{(\w+)\}\}', self.template_html))

    def validate_pre_generation(self, context: Dict, ticker: str) -> ValidationResult:
        """
        Pre-generation validation: Check if context has all required data.

        Args:
            context: Research context dictionary
            ticker: Equity ticker

        Returns:
            ValidationResult with issues if any
        """
        issues = []
        section_completeness = {}

        # Check each section's required data
        for section, placeholders in self.REQUIRED_PLACEHOLDERS.items():
            section_score = 0
            for placeholder in placeholders:
                key = placeholder.lower()
                # Check multiple possible key formats
                found = (
                    key in context or
                    placeholder in context or
                    self._find_nested_key(context, key)
                )

                if found:
                    section_score += 1
                else:
                    severity = IssueSeverity.CRITICAL if placeholder in [
                        'TICKER', 'COMPANY_NAME', 'CURRENT_PRICE', 'RATING'
                    ] else IssueSeverity.WARNING

                    issues.append(ValidationIssue(
                        section=section,
                        issue_type='missing',
                        description=f"Missing data for {placeholder}",
                        severity=severity,
                        fix_suggestion=f"Ensure research includes {placeholder.lower().replace('_', ' ')}"
                    ))

            section_completeness[section] = (section_score / len(placeholders)) * 100 if placeholders else 100

        # Check scenario data
        scenarios = context.get('scenario_analysis', {}).get('scenarios', {})
        if scenarios:
            total_prob = 0
            for scenario_name in self.REQUIRED_SCENARIOS:
                if scenario_name not in scenarios:
                    issues.append(ValidationIssue(
                        section='scenarios',
                        issue_type='missing',
                        description=f"Missing scenario: {scenario_name}",
                        severity=IssueSeverity.WARNING
                    ))
                else:
                    prob = scenarios[scenario_name].get('probability', 0)
                    total_prob += prob if isinstance(prob, (int, float)) else 0

            # Check probabilities sum to 100%
            if abs(total_prob - 1.0) > 0.01 and abs(total_prob - 100) > 1:
                issues.append(ValidationIssue(
                    section='scenarios',
                    issue_type='inconsistent',
                    description=f"Scenario probabilities sum to {total_prob}, expected 1.0 (100%)",
                    severity=IssueSeverity.WARNING,
                    fix_suggestion="Adjust scenario probabilities to sum to 100%"
                ))

        # Calculate overall coverage
        total_placeholders = sum(len(p) for p in self.REQUIRED_PLACEHOLDERS.values())
        filled = sum(
            1 for section_placeholders in self.REQUIRED_PLACEHOLDERS.values()
            for p in section_placeholders
            if p.lower() in context or p in context or self._find_nested_key(context, p.lower())
        )
        coverage = (filled / total_placeholders) * 100 if total_placeholders else 0

        # Determine validity
        is_valid = len([i for i in issues if i.severity == IssueSeverity.CRITICAL]) == 0

        return ValidationResult(
            is_valid=is_valid,
            ticker=ticker,
            issues=issues,
            placeholder_coverage=coverage,
            section_completeness=section_completeness,
            consistency_score=self._calculate_consistency_score(context),
            template_compliance=coverage
        )

    def validate_post_generation(self, html_content: str, ticker: str) -> ValidationResult:
        """
        Post-generation validation: Check generated HTML.

        Args:
            html_content: Generated HTML string
            ticker: Equity ticker

        Returns:
            ValidationResult with issues if any
        """
        issues = []
        section_completeness = {}

        # Check for unfilled placeholders
        unfilled = re.findall(r'\{\{(\w+)\}\}', html_content)
        for placeholder in unfilled:
            issues.append(ValidationIssue(
                section='general',
                issue_type='empty',
                description=f"Unfilled placeholder: {{{{{placeholder}}}}}",
                severity=IssueSeverity.CRITICAL,
                fix_suggestion=f"Populate {placeholder} with actual data"
            ))

        # Check all required sections exist
        for section_id in self.REQUIRED_SECTIONS:
            # Look for section by ID or class
            section_pattern = rf'(?:id="{section_id}"|class="[^"]*{section_id}[^"]*")'
            section_exists = bool(re.search(section_pattern, html_content, re.IGNORECASE))

            if not section_exists:
                # Also check for section header
                header_pattern = rf'>{section_id.replace("-", " ").title()}</h'
                section_exists = bool(re.search(header_pattern, html_content, re.IGNORECASE))

            if not section_exists:
                issues.append(ValidationIssue(
                    section=section_id,
                    issue_type='missing',
                    description=f"Missing section: #{section_id}",
                    severity=IssueSeverity.CRITICAL,
                    fix_suggestion=f"Add {section_id} section to the report"
                ))
                section_completeness[section_id] = 0
            else:
                section_completeness[section_id] = 100

        # Check sidebar navigation
        if 'class="sidebar"' not in html_content and 'nav' not in html_content.lower():
            issues.append(ValidationIssue(
                section='navigation',
                issue_type='missing',
                description="Missing sidebar navigation",
                severity=IssueSeverity.WARNING,
                fix_suggestion="Add sidebar navigation for section links"
            ))

        # Check scenario cards (should have 5)
        scenario_card_count = len(re.findall(r'class="[^"]*scenario-card[^"]*"', html_content))
        if scenario_card_count < 5:
            issues.append(ValidationIssue(
                section='scenarios',
                issue_type='incomplete',
                description=f"Only {scenario_card_count} scenario cards (expected 5)",
                severity=IssueSeverity.WARNING,
                fix_suggestion="Ensure all 5 scenarios are displayed"
            ))

        # Check dark theme colors
        if '#0d1117' not in html_content and '#161b22' not in html_content:
            issues.append(ValidationIssue(
                section='styling',
                issue_type='inconsistent',
                description="Dark theme colors not detected",
                severity=IssueSeverity.INFO,
                fix_suggestion="Use #0d1117 or #161b22 for dark background"
            ))

        # Calculate scores
        coverage = 100 - (len(unfilled) * 5)  # Deduct 5% per unfilled placeholder
        coverage = max(0, min(100, coverage))

        consistency = self._validate_html_consistency(html_content)

        is_valid = len([i for i in issues if i.severity == IssueSeverity.CRITICAL]) == 0

        return ValidationResult(
            is_valid=is_valid,
            ticker=ticker,
            issues=issues,
            placeholder_coverage=coverage,
            section_completeness=section_completeness,
            consistency_score=consistency,
            template_compliance=coverage
        )

    def validate_portfolio(self, results: List[ValidationResult]) -> Dict:
        """
        Validate consistency across a portfolio of reports.

        Args:
            results: List of ValidationResults from individual reports

        Returns:
            Portfolio-level validation summary
        """
        all_valid = all(r.is_valid for r in results)
        total_issues = sum(len(r.issues) for r in results)
        critical_issues = sum(len(r.critical_issues) for r in results)

        avg_coverage = sum(r.placeholder_coverage for r in results) / len(results) if results else 0
        avg_consistency = sum(r.consistency_score for r in results) / len(results) if results else 0

        return {
            "validation_result": "APPROVED" if all_valid else "REVISION_NEEDED",
            "reports_validated": {
                r.ticker: {
                    "is_valid": r.is_valid,
                    "placeholder_coverage": r.placeholder_coverage,
                    "issues_count": len(r.issues),
                    "critical_issues": len(r.critical_issues)
                }
                for r in results
            },
            "portfolio_summary": {
                "all_valid": all_valid,
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "average_coverage": avg_coverage,
                "average_consistency": avg_consistency
            },
            "issues_by_report": {
                r.ticker: [
                    {
                        "section": i.section,
                        "type": i.issue_type,
                        "description": i.description,
                        "severity": i.severity.value
                    }
                    for i in r.issues
                ]
                for r in results
            }
        }

    def _find_nested_key(self, d: Dict, key: str, max_depth: int = 3) -> bool:
        """Recursively search for a key in nested dict"""
        if max_depth <= 0:
            return False

        if key in d:
            return True

        for v in d.values():
            if isinstance(v, dict):
                if self._find_nested_key(v, key, max_depth - 1):
                    return True

        return False

    def _calculate_consistency_score(self, context: Dict) -> float:
        """Calculate data consistency within context"""
        score = 100.0

        # Check numeric consistency
        try:
            current_price = context.get('current_price')
            fair_value = context.get('fair_value') or context.get('pwv')

            if current_price and fair_value:
                price = float(str(current_price).replace('$', '').replace(',', '').replace('HKD', '').strip())
                fv = float(str(fair_value).replace('$', '').replace(',', '').replace('HKD', '').strip())

                if price > 0:
                    expected_upside = ((fv - price) / price) * 100
                    actual_upside = context.get('upside_pct')

                    if actual_upside:
                        actual = float(str(actual_upside).replace('%', '').strip())
                        if abs(expected_upside - actual) > 5:
                            score -= 10
        except (ValueError, TypeError, AttributeError):
            score -= 5

        # Check scenario probability consistency
        scenarios = context.get('scenario_analysis', {}).get('scenarios', {})
        if scenarios:
            try:
                total_prob = sum(
                    float(s.get('probability', 0))
                    for s in scenarios.values()
                    if isinstance(s, dict)
                )
                if total_prob > 0 and abs(total_prob - 1.0) > 0.01 and abs(total_prob - 100) > 1:
                    score -= 15
            except (ValueError, TypeError):
                score -= 5

        return max(0, score)

    def _validate_html_consistency(self, html_content: str) -> float:
        """Validate HTML structure consistency"""
        score = 100.0

        # Check for common structural elements
        required_elements = [
            ('<!DOCTYPE html', 'Missing DOCTYPE'),
            ('<html', 'Missing html tag'),
            ('<head>', 'Missing head section'),
            ('<body', 'Missing body tag'),
            ('</html>', 'Unclosed html tag'),
        ]

        for element, description in required_elements:
            if element.lower() not in html_content.lower():
                score -= 5

        # Check for proper table structure
        table_count = html_content.lower().count('<table')
        thead_count = html_content.lower().count('<thead')
        if table_count > thead_count:
            score -= 5  # Tables without headers

        # Check for metric cards having both label and value
        metric_cards = re.findall(r'class="[^"]*metric-card[^"]*".*?</div>', html_content, re.DOTALL | re.IGNORECASE)
        for card in metric_cards:
            if 'label' not in card.lower() or 'value' not in card.lower():
                score -= 2

        return max(0, score)

    def generate_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report"""
        lines = [
            "=" * 60,
            f"TEMPLATE VALIDATION REPORT: {result.ticker}",
            "=" * 60,
            f"Status: {'PASS' if result.is_valid else 'FAIL'}",
            f"Placeholder Coverage: {result.placeholder_coverage:.1f}%",
            f"Consistency Score: {result.consistency_score:.1f}%",
            f"Template Compliance: {result.template_compliance:.1f}%",
            "",
            "Section Completeness:",
        ]

        for section, score in result.section_completeness.items():
            bar = "=" * int(score / 10) + "-" * (10 - int(score / 10))
            status = "OK" if score >= 80 else "WARN" if score >= 50 else "FAIL"
            lines.append(f"  {section:25s} [{bar}] {score:5.0f}% {status}")

        if result.issues:
            lines.append("")
            lines.append(f"Issues Found ({len(result.issues)}):")

            for issue in sorted(result.issues, key=lambda x: x.severity.value):
                icon = "X" if issue.severity == IssueSeverity.CRITICAL else "!" if issue.severity == IssueSeverity.WARNING else "i"
                lines.append(f"  [{icon}] [{issue.section}] {issue.description}")
                if issue.fix_suggestion:
                    lines.append(f"      -> {issue.fix_suggestion}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
