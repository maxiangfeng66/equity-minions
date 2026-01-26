"""
Report Goalkeeper Agent

Final quality control agent that checks generated HTML reports for:
1. Unrealistic numbers (percentages, prices, valuations)
2. Presentation issues (missing sections, broken formatting)
3. Data consistency (prices match throughout, company name consistent)
4. Obvious errors (negative market cap, upside > 1000%, etc.)
5. DATA ALIGNMENT - verifies report pulls correct data from workflow results

This agent runs AFTER the HTML report is generated and can flag issues
or even block publication if critical errors are found.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "CRITICAL"  # Block publication
    HIGH = "HIGH"          # Serious issue, should fix
    MEDIUM = "MEDIUM"      # Notable issue
    LOW = "LOW"            # Minor cosmetic issue


@dataclass
class ValidationIssue:
    severity: Severity
    category: str
    description: str
    location: str = ""
    value: str = ""


@dataclass
class ValidationResult:
    report_path: str
    ticker: str
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: int = 100  # Start at 100, deduct for issues

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)
        # Deduct points based on severity
        deductions = {
            Severity.CRITICAL: 50,
            Severity.HIGH: 20,
            Severity.MEDIUM: 10,
            Severity.LOW: 5
        }
        self.score = max(0, self.score - deductions.get(issue.severity, 5))

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)


class ReportGoalkeeper:
    """
    Final quality control for generated equity research reports.
    Catches naive mistakes before publication.
    """

    def __init__(self):
        self.checks = [
            self._check_unrealistic_percentages,
            self._check_price_consistency,
            self._check_company_identity,
            self._check_required_sections,
            self._check_numeric_sanity,
            self._check_formatting_issues,
            self._check_data_contamination,
            self._check_missing_data,
        ]

    def validate_report(self, report_path: str, workflow_result_path: str = None) -> ValidationResult:
        """Run all validation checks on a report"""
        path = Path(report_path)
        if not path.exists():
            result = ValidationResult(report_path, "", False)
            result.add_issue(ValidationIssue(
                Severity.CRITICAL, "File", "Report file not found", report_path
            ))
            return result

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract ticker from filename
        ticker = path.stem.split('_')[0] + '_' + path.stem.split('_')[1] if '_' in path.stem else path.stem

        result = ValidationResult(report_path, ticker, True)

        # Run all checks
        for check in self.checks:
            check(content, result)

        # If workflow result path is provided, check data alignment
        if workflow_result_path:
            self._check_data_alignment(content, result, workflow_result_path)
        else:
            # Try to find workflow result automatically
            auto_workflow_path = self._find_workflow_result(path, ticker)
            if auto_workflow_path:
                self._check_data_alignment(content, result, auto_workflow_path)

        # Determine pass/fail
        result.passed = result.critical_count == 0 and result.score >= 50

        return result

    def _find_workflow_result(self, report_path: Path, ticker: str) -> Optional[str]:
        """Try to find the workflow result JSON for this report"""
        context_dir = report_path.parent.parent / "context"

        # Try common patterns
        patterns = [
            f"{ticker.replace(' ', '_')}_workflow_result.json",
            f"{ticker.replace('_', ' ').replace(' ', '_')}_workflow_result.json",
        ]

        for pattern in patterns:
            workflow_path = context_dir / pattern
            if workflow_path.exists():
                return str(workflow_path)

        return None

    def _check_data_alignment(self, content: str, result: ValidationResult, workflow_path: str):
        """Check that the report data aligns with workflow results"""
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            result.add_issue(ValidationIssue(
                Severity.MEDIUM,
                "Data Alignment",
                f"Could not load workflow result: {e}",
                location=workflow_path
            ))
            return

        # Get expected ticker from workflow
        expected_ticker = workflow_data.get('ticker', '')

        # Check ticker consistency
        if expected_ticker:
            # Look for ticker mentions in the report
            ticker_in_report = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
            if ticker_in_report:
                report_title = ticker_in_report.group(1)
                # Normalize tickers for comparison
                expected_normalized = expected_ticker.replace('_', ' ').replace('HK', '').replace('US', '').strip()
                if expected_normalized.lower() not in report_title.lower():
                    result.add_issue(ValidationIssue(
                        Severity.CRITICAL,
                        "Data Alignment",
                        f"Ticker mismatch: expected {expected_ticker}, report title is '{report_title}'",
                        value=expected_ticker
                    ))

        # Check if report mentions the correct company from workflow
        node_outputs = workflow_data.get('node_outputs', {})

        # Get company name from Research Supervisor or Company Deep Dive
        company_from_workflow = None
        for node in ['Research Supervisor', 'Company Deep Dive']:
            if node in node_outputs:
                for msg in node_outputs[node]:
                    msg_content = msg.get('content', '')
                    # Look for company name patterns
                    company_match = re.search(r'(?:company|researching|analyzing)[:\s]+([A-Za-z][A-Za-z\s]+(?:Inc|Corp|Ltd|Limited|Technology)?)', msg_content, re.IGNORECASE)
                    if company_match:
                        company_from_workflow = company_match.group(1).strip()
                        break
                if company_from_workflow:
                    break

        # Check verified price alignment
        verified_price_from_workflow = None
        for msg in node_outputs.get('START', []):
            msg_content = msg.get('content', '')
            price_match = re.search(r'VERIFIED CURRENT PRICE:\s*(?:USD|HKD|CNY)?\s*(\d+\.?\d*)', msg_content)
            if price_match:
                try:
                    verified_price_from_workflow = float(price_match.group(1))
                except ValueError:
                    pass
                break

        if verified_price_from_workflow:
            # Check if this price appears in the report's hero section
            hero_price_match = re.search(r'class="hero-price"[^>]*>(?:USD|HKD|CNY)?\s*(\d+\.?\d*)', content)
            if hero_price_match:
                try:
                    report_price = float(hero_price_match.group(1))
                    # Allow small rounding differences
                    if abs(report_price - verified_price_from_workflow) > 0.5:
                        result.add_issue(ValidationIssue(
                            Severity.HIGH,
                            "Data Alignment",
                            f"Price mismatch: workflow has ${verified_price_from_workflow:.2f}, report shows ${report_price:.2f}",
                            value=f"Expected: {verified_price_from_workflow}, Got: {report_price}"
                        ))
                except ValueError:
                    pass

        # Check for valuation committee target alignment
        target_from_workflow = None
        for msg in node_outputs.get('Valuation Committee', []):
            msg_content = msg.get('content', '')
            target_match = re.search(r'(?:CONSENSUS TARGET|TARGET PRICE|PWV)[:\s]*\$?(\d+\.?\d*)', msg_content, re.IGNORECASE)
            if target_match:
                try:
                    target_from_workflow = float(target_match.group(1))
                except ValueError:
                    pass
                break

        if target_from_workflow:
            # Check if target appears reasonably in report
            report_targets = re.findall(r'Target[:\s]*(?:USD|HKD|CNY)?\s*(\d+\.?\d*)', content, re.IGNORECASE)
            if report_targets:
                try:
                    found_match = False
                    for rt in report_targets:
                        report_target = float(rt)
                        # Allow 10% tolerance
                        if abs(report_target - target_from_workflow) / target_from_workflow < 0.1:
                            found_match = True
                            break
                    if not found_match:
                        result.add_issue(ValidationIssue(
                            Severity.MEDIUM,
                            "Data Alignment",
                            f"Target price from workflow (${target_from_workflow:.2f}) not found in report targets",
                            value=f"Expected: {target_from_workflow}"
                        ))
                except (ValueError, ZeroDivisionError):
                    pass

        # Check debate content alignment - verify debate arguments came from workflow
        bull_content_in_workflow = False
        bear_content_in_workflow = False

        for msg in node_outputs.get('Bull Advocate R1', []) + node_outputs.get('Bull Advocate R2', []):
            if msg.get('content', ''):
                bull_content_in_workflow = True
                break

        for msg in node_outputs.get('Bear Advocate R1', []) + node_outputs.get('Bear Advocate R2', []):
            if msg.get('content', ''):
                bear_content_in_workflow = True
                break

        # Check report has debate sections
        has_bull_in_report = bool(re.search(r'Bull|bull case|bullish', content, re.IGNORECASE))
        has_bear_in_report = bool(re.search(r'Bear|bear case|bearish', content, re.IGNORECASE))

        if bull_content_in_workflow and not has_bull_in_report:
            result.add_issue(ValidationIssue(
                Severity.HIGH,
                "Data Alignment",
                "Workflow has bull case arguments but report missing bull section",
                location="Debate Section"
            ))

        if bear_content_in_workflow and not has_bear_in_report:
            result.add_issue(ValidationIssue(
                Severity.HIGH,
                "Data Alignment",
                "Workflow has bear case arguments but report missing bear section",
                location="Debate Section"
            ))

    def _check_unrealistic_percentages(self, content: str, result: ValidationResult):
        """Check for unrealistic percentage values in key presentation areas"""
        # Only check percentages in scenario cards and key metrics - not in debate content
        # These are the areas where upside/downside percentages matter

        # Check scenario card percentages (these have specific HTML structure)
        scenario_pcts = re.findall(r'<span class="(?:positive|negative)">\s*([+-]?\d+\.?\d*)%\s*</span>', content)
        for pct_str in scenario_pcts:
            try:
                pct = float(pct_str)
                if abs(pct) > 500:
                    result.add_issue(ValidationIssue(
                        Severity.CRITICAL,
                        "Scenario Percentage",
                        f"Unrealistic scenario upside/downside: {pct}%",
                        value=f"{pct}%"
                    ))
                elif abs(pct) > 200:
                    result.add_issue(ValidationIssue(
                        Severity.HIGH,
                        "Scenario Percentage",
                        f"Very high scenario percentage: {pct}%",
                        value=f"{pct}%"
                    ))
            except ValueError:
                continue

        # Check upside percentages in hero/summary sections
        upside_matches = re.findall(r'Upside[:\s]*([+-]?\d+\.?\d*)%', content, re.IGNORECASE)
        for pct_str in upside_matches:
            try:
                pct = float(pct_str)
                if abs(pct) > 300:
                    result.add_issue(ValidationIssue(
                        Severity.CRITICAL,
                        "Upside Percentage",
                        f"Unrealistic implied upside: {pct}%",
                        value=f"{pct}%"
                    ))
            except ValueError:
                continue

    def _check_price_consistency(self, content: str, result: ValidationResult):
        """Check that prices are consistent throughout the report"""
        # Extract current prices mentioned - use \d+\.?\d* to require at least one digit
        current_prices = re.findall(r'Current(?:\s+Price)?[:\s]*(?:USD|HKD|CNY)?\s*(\d+\.?\d*)', content, re.IGNORECASE)

        if current_prices:
            # Filter out empty strings and lone dots
            prices = []
            for p in current_prices:
                if p and p != '.' and p.strip():
                    try:
                        prices.append(float(p))
                    except ValueError:
                        continue
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                # Allow some variation due to rounding, but flag large differences
                if max_price > min_price * 1.5:
                    result.add_issue(ValidationIssue(
                        Severity.HIGH,
                        "Price Consistency",
                        f"Inconsistent current prices: range {min_price:.2f} to {max_price:.2f}",
                        value=f"{min_price:.2f} - {max_price:.2f}"
                    ))

    def _check_company_identity(self, content: str, result: ValidationResult):
        """Check for data contamination from wrong companies"""
        # List of companies that shouldn't appear unless they're the subject
        contamination_markers = [
            ('Apple Inc', 'Apple'),
            ('Amazon.com', 'Amazon'),
            ('Microsoft Corporation', 'Microsoft'),
            ('Google LLC', 'Alphabet'),
            ('Meta Platforms', 'Facebook'),
        ]

        # Get the main company from the title
        title_match = re.search(r'<h1>([^<]+)</h1>', content)
        main_company = title_match.group(1) if title_match else ""

        for company, short_name in contamination_markers:
            # Skip if this IS the main company
            if short_name.lower() in main_company.lower():
                continue
            # Check for mentions that might indicate contamination
            mentions = len(re.findall(rf'\b{short_name}\b', content, re.IGNORECASE))
            if mentions > 5:  # More than 5 mentions of unrelated company
                result.add_issue(ValidationIssue(
                    Severity.MEDIUM,
                    "Contamination",
                    f"Possible data contamination: {short_name} mentioned {mentions} times",
                    value=str(mentions)
                ))

    def _check_required_sections(self, content: str, result: ValidationResult):
        """Check that all required sections are present"""
        required_sections = [
            ('Executive Summary', r'Executive Summary'),
            ('Research Scope', r'Research Scope'),
            ('Data Collection', r'Data Collection'),
            ('Debate', r'Debate|Bull.*Bear'),
            ('Valuation', r'Valuation'),
            ('Recommendation', r'Recommendation'),
        ]

        for section_name, pattern in required_sections:
            if not re.search(pattern, content, re.IGNORECASE):
                result.add_issue(ValidationIssue(
                    Severity.HIGH,
                    "Missing Section",
                    f"Required section missing: {section_name}",
                    location=section_name
                ))

    def _check_numeric_sanity(self, content: str, result: ValidationResult):
        """Check for obviously wrong numeric values"""
        # Check market cap - should be positive and reasonable
        market_caps = re.findall(r'Market\s*Cap[:\s]*([\d.,]+)\s*(B|M|billion|million)', content, re.IGNORECASE)
        for value, unit in market_caps:
            try:
                cap = float(value.replace(',', ''))
                if unit.lower() in ['b', 'billion']:
                    cap *= 1e9
                else:
                    cap *= 1e6
                if cap < 0:
                    result.add_issue(ValidationIssue(
                        Severity.CRITICAL,
                        "Numeric",
                        "Negative market cap detected",
                        value=f"{value}{unit}"
                    ))
            except ValueError:
                continue

        # Check for zero prices
        if re.search(r'Current[:\s]*(?:USD|HKD|CNY)?\s*0\.00', content, re.IGNORECASE):
            result.add_issue(ValidationIssue(
                Severity.CRITICAL,
                "Numeric",
                "Zero current price detected",
                value="0.00"
            ))

        # Check for zero target prices
        if re.search(r'Target[:\s]*(?:USD|HKD|CNY)?\s*0\.00', content, re.IGNORECASE):
            result.add_issue(ValidationIssue(
                Severity.CRITICAL,
                "Numeric",
                "Zero target price detected",
                value="0.00"
            ))

    def _check_formatting_issues(self, content: str, result: ValidationResult):
        """Check for HTML/formatting issues"""
        # Check for unfilled placeholders
        placeholders = re.findall(r'\{\{[^}]+\}\}', content)
        if placeholders:
            result.add_issue(ValidationIssue(
                Severity.HIGH,
                "Formatting",
                f"Unfilled placeholders found: {placeholders[:3]}",
                value=str(len(placeholders))
            ))

        # Check for broken HTML tags
        broken_tags = re.findall(r'<\w+[^>]*<', content)
        if broken_tags:
            result.add_issue(ValidationIssue(
                Severity.MEDIUM,
                "Formatting",
                "Possibly broken HTML tags detected",
                value=str(len(broken_tags))
            ))

        # Check for missing closing tags (simple check)
        for tag in ['div', 'section', 'table', 'tr', 'td']:
            opens = len(re.findall(rf'<{tag}[\s>]', content, re.IGNORECASE))
            closes = len(re.findall(rf'</{tag}>', content, re.IGNORECASE))
            if opens != closes and abs(opens - closes) > 3:
                result.add_issue(ValidationIssue(
                    Severity.MEDIUM,
                    "Formatting",
                    f"Mismatched {tag} tags: {opens} opens, {closes} closes",
                    value=f"{opens}/{closes}"
                ))

    def _check_data_contamination(self, content: str, result: ValidationResult):
        """Check for ticker contamination"""
        # Extract the main ticker from the report
        ticker_match = re.search(r'<h1>(\w+(?:_|\s)\w+)</h1>', content)
        if not ticker_match:
            return

        main_ticker = ticker_match.group(1).upper().replace(' ', '_')

        # Common tickers that might contaminate
        common_tickers = ['6682_HK', '9660_HK', 'AAPL', 'MSFT', 'GOOGL', 'AMZN']

        for ticker in common_tickers:
            if ticker == main_ticker or ticker.replace('_', ' ') == main_ticker.replace('_', ' '):
                continue
            mentions = len(re.findall(rf'\b{ticker}\b', content, re.IGNORECASE))
            if mentions > 3:
                result.add_issue(ValidationIssue(
                    Severity.MEDIUM,
                    "Contamination",
                    f"Wrong ticker {ticker} mentioned {mentions} times",
                    value=str(mentions)
                ))

    def _check_missing_data(self, content: str, result: ValidationResult):
        """Check for N/A or missing data markers"""
        na_count = len(re.findall(r'\bN/A\b', content))
        if na_count > 20:
            result.add_issue(ValidationIssue(
                Severity.MEDIUM,
                "Missing Data",
                f"Too many N/A values: {na_count}",
                value=str(na_count)
            ))

        # Check for empty table cells
        empty_cells = len(re.findall(r'<td>\s*</td>', content))
        if empty_cells > 10:
            result.add_issue(ValidationIssue(
                Severity.LOW,
                "Missing Data",
                f"Many empty table cells: {empty_cells}",
                value=str(empty_cells)
            ))


def validate_report(report_path: str, workflow_result_path: str = None) -> ValidationResult:
    """Convenience function to validate a single report"""
    goalkeeper = ReportGoalkeeper()
    return goalkeeper.validate_report(report_path, workflow_result_path)


def validate_all_reports(reports_dir: str = "reports") -> Dict[str, ValidationResult]:
    """Validate all reports in a directory"""
    goalkeeper = ReportGoalkeeper()
    results = {}

    reports_path = Path(reports_dir)
    for report_file in reports_path.glob("*_detailed.html"):
        result = goalkeeper.validate_report(str(report_file))
        results[report_file.name] = result

    return results


def print_validation_summary(results: Dict[str, ValidationResult]):
    """Print a summary of validation results"""
    print("=" * 70)
    print("REPORT GOALKEEPER VALIDATION SUMMARY")
    print("=" * 70)
    print()

    passed = sum(1 for r in results.values() if r.passed)
    failed = len(results) - passed

    print(f"Total Reports: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    for name, result in sorted(results.items()):
        status = "[PASS]" if result.passed else "[FAIL]"
        score = f"Score: {result.score}/100"
        issues = f"Issues: {len(result.issues)}"
        print(f"{status} {name}: {score}, {issues}")

        if not result.passed:
            for issue in result.issues:
                if issue.severity in [Severity.CRITICAL, Severity.HIGH]:
                    print(f"       [{issue.severity.value}] {issue.category}: {issue.description}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Validate specific report
        result = validate_report(sys.argv[1])
        print(f"Report: {result.report_path}")
        print(f"Passed: {result.passed}")
        print(f"Score: {result.score}/100")
        print(f"Issues: {len(result.issues)}")
        for issue in result.issues:
            print(f"  [{issue.severity.value}] {issue.category}: {issue.description}")
    else:
        # Validate all reports
        results = validate_all_reports()
        print_validation_summary(results)
