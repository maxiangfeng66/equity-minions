#!/usr/bin/env python3
"""
Data Flow Tracer

A project-level agent that traces data flow through the workflow
to identify where data gets lost, corrupted, or hallucinated.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DataPoint:
    """A tracked data point"""
    name: str
    expected_value: Any
    node_values: Dict[str, Any] = field(default_factory=dict)
    first_appearance: Optional[str] = None
    last_correct: Optional[str] = None
    first_wrong: Optional[str] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class FlowTraceReport:
    """Report from data flow tracing"""
    ticker: str
    workflow_result_path: str
    data_points: Dict[str, DataPoint]
    critical_failures: List[str]
    data_integrity_score: float
    node_reliability: Dict[str, float]
    recommendations: List[str]


class DataFlowTracer:
    """
    Traces how key data points flow through the workflow.

    Tracks:
    1. Current price - from prefetch through to final report
    2. Ticker/company identity - never confused with another company
    3. Market cap - consistent with price * shares
    4. Valuation outputs - scenarios consistent with inputs
    5. Routing keywords - appear where needed

    Identifies:
    - Where data gets lost
    - Where hallucination occurs
    - Where calculations go wrong
    """

    def __init__(self, workflow_result_path: str):
        self.result_path = Path(workflow_result_path)
        self.result = self._load_result()
        self.data_points: Dict[str, DataPoint] = {}

    def _load_result(self) -> Dict:
        """Load workflow result JSON"""
        with open(self.result_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def trace(self, expected_price: float = None) -> FlowTraceReport:
        """Run full data flow trace"""
        ticker = self.result.get('ticker', 'Unknown')

        print("="*60)
        print(f"DATA FLOW TRACE: {ticker}")
        print(f"Result file: {self.result_path}")
        print("="*60)

        # Initialize data points to track
        self._init_data_points(ticker, expected_price)

        # Trace through each node
        node_outputs = self.result.get('node_outputs', {})

        print(f"\nTracing through {len(node_outputs)} nodes...")

        for node_id, messages in node_outputs.items():
            if not messages:
                continue

            content = messages[-1].get('content', '')
            self._trace_node(node_id, content)

        # Analyze results
        critical_failures = self._identify_critical_failures()
        integrity_score = self._calculate_integrity_score()
        node_reliability = self._calculate_node_reliability()
        recommendations = self._generate_recommendations()

        report = FlowTraceReport(
            ticker=ticker,
            workflow_result_path=str(self.result_path),
            data_points=self.data_points,
            critical_failures=critical_failures,
            data_integrity_score=integrity_score,
            node_reliability=node_reliability,
            recommendations=recommendations
        )

        self._print_report(report)
        return report

    def _init_data_points(self, ticker: str, expected_price: float = None):
        """Initialize data points to track"""
        # Determine expected values based on ticker
        expected = self._get_expected_values(ticker)

        if expected_price:
            expected['current_price'] = expected_price

        self.data_points = {
            'ticker': DataPoint(
                name='Ticker',
                expected_value=ticker
            ),
            'current_price': DataPoint(
                name='Current Price',
                expected_value=expected.get('current_price')
            ),
            'currency': DataPoint(
                name='Currency',
                expected_value=expected.get('currency')
            ),
            'company_name': DataPoint(
                name='Company Name',
                expected_value=expected.get('company_name')
            ),
            'data_verified_keyword': DataPoint(
                name='DATA: VERIFIED keyword',
                expected_value='DATA: VERIFIED'
            ),
            'inputs_validated_keyword': DataPoint(
                name='INPUTS: VALIDATED keyword',
                expected_value='INPUTS: VALIDATED'
            ),
            'valuation_approved_keyword': DataPoint(
                name='VALUATION: APPROVED keyword',
                expected_value='VALUATION: APPROVED'
            ),
            'route_synthesizer_keyword': DataPoint(
                name='ROUTE: Synthesizer keyword',
                expected_value='ROUTE: Synthesizer'
            ),
        }

    def _get_expected_values(self, ticker: str) -> Dict:
        """Get expected values for a ticker"""
        # Load from config
        try:
            from config import EQUITIES
            equity_info = EQUITIES.get(ticker, {})
            company_name = equity_info.get('name', ticker)
        except:
            company_name = ticker

        # Determine currency
        if 'HK' in ticker:
            currency = 'HKD'
        elif 'US' in ticker:
            currency = 'USD'
        elif 'CH' in ticker:
            currency = 'CNY'
        else:
            currency = 'USD'

        return {
            'company_name': company_name,
            'currency': currency,
            'current_price': None  # Will be set if provided
        }

    def _trace_node(self, node_id: str, content: str):
        """Trace data points through a single node"""
        content_lower = content.lower()

        # Trace ticker
        ticker_expected = self.data_points['ticker'].expected_value
        if ticker_expected:
            ticker_found = ticker_expected.lower() in content_lower
            if ticker_found:
                if not self.data_points['ticker'].first_appearance:
                    self.data_points['ticker'].first_appearance = node_id
                self.data_points['ticker'].node_values[node_id] = 'present'

        # Trace current price
        price_expected = self.data_points['current_price'].expected_value
        if price_expected:
            # Look for price patterns
            price_patterns = [
                rf'{price_expected}',
                rf'\${price_expected}',
                rf'hkd\s*{price_expected}',
                rf'usd\s*{price_expected}',
            ]

            price_found = None
            for pattern in price_patterns:
                if re.search(pattern, content_lower):
                    price_found = price_expected
                    break

            # Also look for any price mentions to detect wrong prices
            all_prices = re.findall(r'(?:hkd|usd|\$)\s*(\d+\.?\d*)', content_lower)

            if price_found:
                self.data_points['current_price'].node_values[node_id] = price_expected
                if not self.data_points['current_price'].first_appearance:
                    self.data_points['current_price'].first_appearance = node_id
                self.data_points['current_price'].last_correct = node_id
            elif all_prices:
                # Wrong price found
                wrong_price = all_prices[0]
                self.data_points['current_price'].node_values[node_id] = float(wrong_price)
                if not self.data_points['current_price'].first_wrong:
                    self.data_points['current_price'].first_wrong = node_id
                    self.data_points['current_price'].issues.append(
                        f"Wrong price {wrong_price} found at {node_id} (expected {price_expected})"
                    )

        # Trace routing keywords
        routing_keywords = [
            'data_verified_keyword',
            'inputs_validated_keyword',
            'valuation_approved_keyword',
            'route_synthesizer_keyword'
        ]

        for kw_key in routing_keywords:
            expected = self.data_points[kw_key].expected_value
            if expected and expected.lower() in content_lower:
                self.data_points[kw_key].node_values[node_id] = 'present'
                if not self.data_points[kw_key].first_appearance:
                    self.data_points[kw_key].first_appearance = node_id

        # Check for wrong company data
        company_expected = self.data_points['company_name'].expected_value
        if company_expected:
            # Check for common confusion indicators
            wrong_companies = ['apple', 'microsoft', 'amazon', 'google', 'tesla']
            for wrong in wrong_companies:
                if wrong in content_lower and company_expected.lower() not in content_lower:
                    self.data_points['company_name'].issues.append(
                        f"Possible wrong company data ({wrong}) at {node_id}"
                    )

    def _identify_critical_failures(self) -> List[str]:
        """Identify critical data flow failures"""
        failures = []

        # Check if verified price was used
        price_dp = self.data_points.get('current_price')
        if price_dp and price_dp.expected_value:
            if price_dp.first_wrong and not price_dp.last_correct:
                failures.append(
                    f"CRITICAL: Verified price never used - "
                    f"wrong price appeared at {price_dp.first_wrong}"
                )
            elif price_dp.first_wrong:
                failures.append(
                    f"Price diverged from verified value at {price_dp.first_wrong}"
                )

        # Check routing keywords
        routing_checks = [
            ('data_verified_keyword', 'Data Checkpoint'),
            ('inputs_validated_keyword', 'Pre-Model Validator'),
            ('valuation_approved_keyword', 'Valuation Committee'),
            ('route_synthesizer_keyword', 'Quality Supervisor'),
        ]

        for kw_key, expected_node in routing_checks:
            dp = self.data_points.get(kw_key)
            if dp and not dp.first_appearance:
                failures.append(
                    f"Missing '{dp.expected_value}' - {expected_node} may not have executed properly"
                )

        # Check for company confusion
        company_dp = self.data_points.get('company_name')
        if company_dp and company_dp.issues:
            failures.extend(company_dp.issues)

        return failures

    def _calculate_integrity_score(self) -> float:
        """Calculate overall data integrity score (0-100)"""
        scores = []

        for key, dp in self.data_points.items():
            if dp.expected_value:
                if dp.first_appearance and not dp.issues:
                    scores.append(100)
                elif dp.first_appearance and dp.issues:
                    scores.append(50)
                else:
                    scores.append(0)

        return sum(scores) / len(scores) if scores else 0

    def _calculate_node_reliability(self) -> Dict[str, float]:
        """Calculate reliability score for each node"""
        reliability = {}

        node_outputs = self.result.get('node_outputs', {})
        for node_id in node_outputs:
            # Count correct data points at this node
            correct = 0
            total = 0

            for key, dp in self.data_points.items():
                if dp.expected_value:
                    total += 1
                    if node_id in dp.node_values:
                        if dp.node_values[node_id] == dp.expected_value or dp.node_values[node_id] == 'present':
                            correct += 1

            if total > 0:
                reliability[node_id] = (correct / total) * 100

        return reliability

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on trace results"""
        recs = []

        # Price issues
        price_dp = self.data_points.get('current_price')
        if price_dp and price_dp.issues:
            recs.append("Ensure prefetch_data.py runs BEFORE workflow execution")
            recs.append("Verify Data Checkpoint is catching price mismatches")

        # Routing issues
        routing_missing = []
        for key in ['data_verified_keyword', 'inputs_validated_keyword',
                    'valuation_approved_keyword', 'route_synthesizer_keyword']:
            dp = self.data_points.get(key)
            if dp and not dp.first_appearance:
                routing_missing.append(dp.expected_value)

        if routing_missing:
            recs.append(f"Check why routing keywords are missing: {routing_missing}")
            recs.append("Workflow may be taking unexpected paths or terminating early")

        # Company confusion
        company_dp = self.data_points.get('company_name')
        if company_dp and company_dp.issues:
            recs.append("Data collectors may be returning wrong company data")
            recs.append("Strengthen company identity checks in Data Checkpoint")

        if not recs:
            recs.append("Data flow appears intact - verify outputs manually")

        return recs

    def _print_report(self, report: FlowTraceReport):
        """Print trace report"""
        print("\n" + "="*60)
        print("DATA FLOW TRACE REPORT")
        print("="*60)

        print(f"\nTicker: {report.ticker}")
        print(f"Data Integrity Score: {report.data_integrity_score:.1f}/100")

        print("\nData Point Tracking:")
        for key, dp in report.data_points.items():
            status = "OK" if dp.first_appearance and not dp.issues else "ISSUE"
            print(f"  [{status}] {dp.name}")
            if dp.first_appearance:
                print(f"       First seen: {dp.first_appearance}")
            if dp.issues:
                for issue in dp.issues:
                    print(f"       [!] {issue}")

        if report.critical_failures:
            print(f"\nCRITICAL FAILURES ({len(report.critical_failures)}):")
            for failure in report.critical_failures:
                print(f"  [X] {failure}")

        print(f"\nNode Reliability (top 5 lowest):")
        sorted_nodes = sorted(report.node_reliability.items(), key=lambda x: x[1])
        for node_id, score in sorted_nodes[:5]:
            print(f"  {node_id}: {score:.0f}%")

        print(f"\nRecommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")

        print("="*60)


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python data_flow_tracer.py <workflow_result.json> [expected_price]")
        print("Example: python data_flow_tracer.py context/LEGN_US_workflow_result.json 19.34")
        sys.exit(1)

    result_path = sys.argv[1]
    expected_price = float(sys.argv[2]) if len(sys.argv) > 2 else None

    tracer = DataFlowTracer(result_path)
    report = tracer.trace(expected_price)

    # Save report
    output_path = Path(result_path).parent / f"trace_{Path(result_path).stem}.json"

    with open(output_path, 'w') as f:
        json.dump({
            'ticker': report.ticker,
            'workflow_result_path': report.workflow_result_path,
            'data_integrity_score': report.data_integrity_score,
            'critical_failures': report.critical_failures,
            'node_reliability': report.node_reliability,
            'recommendations': report.recommendations,
            'data_points': {
                k: {
                    'name': v.name,
                    'expected_value': v.expected_value,
                    'node_values': v.node_values,
                    'first_appearance': v.first_appearance,
                    'issues': v.issues
                }
                for k, v in report.data_points.items()
            }
        }, f, indent=2)

    print(f"\nTrace report saved to: {output_path}")
