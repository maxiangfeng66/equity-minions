#!/usr/bin/env python3
"""
Node Function Validator

A project-level agent that tests each workflow node individually
to ensure it functions correctly before running the full pipeline.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Import workflow components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.workflow_loader import WorkflowLoader, NodeConfig
from workflow.node_executor import NodeExecutor, Message
from config import API_KEYS


@dataclass
class NodeTestResult:
    """Result of testing a single node"""
    node_id: str
    success: bool
    output_length: int
    execution_time: float
    has_expected_content: bool
    issues: List[str] = field(default_factory=list)
    output_preview: str = ""


@dataclass
class ValidationReport:
    """Full validation report"""
    workflow_name: str
    total_nodes: int
    nodes_tested: int
    nodes_passed: int
    nodes_failed: int
    results: Dict[str, NodeTestResult]
    critical_issues: List[str]
    timestamp: str


class NodeFunctionValidator:
    """
    Validates that each workflow node functions correctly.

    Tests:
    1. Node can execute without errors
    2. Node produces non-empty output
    3. Output contains expected content based on node role
    4. Data collectors actually fetch data (not just ask for input)
    5. Quality gates produce proper PASS/FAIL responses
    6. Routing keywords are present where needed
    """

    def __init__(self, workflow_name: str = "equity_research_v4"):
        self.workflow_name = workflow_name
        self.loader = WorkflowLoader()
        self.config = self.loader.load(workflow_name)
        self.api_keys = {
            "OPENAI_API_KEY": API_KEYS.get("openai", ""),
            "GOOGLE_API_KEY": API_KEYS.get("google", ""),
            "XAI_API_KEY": API_KEYS.get("xai", ""),
            "DASHSCOPE_API_KEY": API_KEYS.get("dashscope", ""),
        }
        self.results: Dict[str, NodeTestResult] = {}

    async def validate_all_nodes(self, test_ticker: str = "6682 HK") -> ValidationReport:
        """Validate all nodes in the workflow"""
        print("="*60)
        print(f"NODE FUNCTION VALIDATION: {self.workflow_name}")
        print("="*60)
        print(f"Test ticker: {test_ticker}")
        print(f"Total nodes: {len(self.config.nodes)}")
        print()

        # Test each node
        for node_id, node_config in self.config.nodes.items():
            if node_config.type == "passthrough":
                print(f"[SKIP] {node_id} (passthrough)")
                continue

            print(f"[TEST] {node_id}...", end=" ", flush=True)
            result = await self._test_node(node_id, node_config, test_ticker)
            self.results[node_id] = result

            if result.success:
                print(f"PASS ({result.output_length} chars, {result.execution_time:.1f}s)")
            else:
                print(f"FAIL - {', '.join(result.issues)}")

        # Generate report
        passed = sum(1 for r in self.results.values() if r.success)
        failed = sum(1 for r in self.results.values() if not r.success)

        report = ValidationReport(
            workflow_name=self.workflow_name,
            total_nodes=len(self.config.nodes),
            nodes_tested=len(self.results),
            nodes_passed=passed,
            nodes_failed=failed,
            results=self.results,
            critical_issues=self._identify_critical_issues(),
            timestamp=datetime.now().isoformat()
        )

        self._print_summary(report)
        return report

    async def validate_single_node(self, node_id: str, test_ticker: str = "6682 HK") -> NodeTestResult:
        """Validate a single node"""
        if node_id not in self.config.nodes:
            return NodeTestResult(
                node_id=node_id,
                success=False,
                output_length=0,
                execution_time=0,
                has_expected_content=False,
                issues=[f"Node '{node_id}' not found in workflow"]
            )

        node_config = self.config.nodes[node_id]
        return await self._test_node(node_id, node_config, test_ticker)

    async def _test_node(self, node_id: str, node_config: NodeConfig, ticker: str) -> NodeTestResult:
        """Test a single node"""
        start_time = datetime.now()
        issues = []

        try:
            # Create test input message
            test_input = self._create_test_input(node_id, ticker)

            # Create executor
            executor = NodeExecutor(node_config, self.api_keys)

            # Execute with timeout
            result = await asyncio.wait_for(
                executor.execute([test_input]),
                timeout=120  # 2 minute timeout
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            output_length = len(result.content)

            # Validate output
            has_expected = self._validate_output(node_id, node_config, result.content)

            if not has_expected:
                issues.append("Output missing expected content")

            # Check for common problems
            if output_length < 100:
                issues.append("Output too short")

            if self._is_asking_for_input(result.content):
                issues.append("Node asking for input instead of executing")

            if node_config.type == "agent" and "web_search" in str(node_config.config):
                if not self._has_search_results(result.content):
                    issues.append("Web search may not have executed")

            return NodeTestResult(
                node_id=node_id,
                success=len(issues) == 0,
                output_length=output_length,
                execution_time=execution_time,
                has_expected_content=has_expected,
                issues=issues,
                output_preview=result.content[:500]
            )

        except asyncio.TimeoutError:
            return NodeTestResult(
                node_id=node_id,
                success=False,
                output_length=0,
                execution_time=120,
                has_expected_content=False,
                issues=["Timeout after 120 seconds"]
            )
        except Exception as e:
            return NodeTestResult(
                node_id=node_id,
                success=False,
                output_length=0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                has_expected_content=False,
                issues=[f"Exception: {str(e)[:100]}"]
            )

    def _create_test_input(self, node_id: str, ticker: str) -> Message:
        """Create appropriate test input for a node"""
        # Generic context that most nodes would receive
        base_context = f"""
============================================================
VERIFIED MARKET DATA (Pre-fetched and Cross-Validated)
============================================================
TICKER: {ticker}
VERIFIED CURRENT PRICE: HKD 52.30
DATA CONFIDENCE: HIGH
============================================================

Conduct equity research on:
Ticker: {ticker}
Company: Beijing Fourth Paradigm Technology
Sector: Technology
Industry: AI/Machine Learning

This is a TEST run to validate node functionality.
"""

        # Node-specific inputs
        node_inputs = {
            "Research Supervisor": base_context,
            "Market Data Collector": f"{base_context}\n\nCollect comprehensive market data for {ticker}.",
            "Industry Deep Dive": f"{base_context}\n\nProvide deep industry analysis for AI/Machine Learning sector.",
            "Company Deep Dive": f"{base_context}\n\nProvide comprehensive company analysis.",
            "Data Verifier": f"{base_context}\n\nVerify the current price and market cap.",
            "Data Checkpoint": f"{base_context}\n\nCollector Price: HKD 52.30\nVerifier Price: HKD 52.30\n\nValidate data consistency.",
            "Debate Moderator": f"{base_context}\n\nIndustry analysis and company analysis completed. Frame the debate.",
            "Bull Advocate R1": f"{base_context}\n\nPresent your strongest bull case arguments.",
            "Bear Advocate R1": f"{base_context}\n\nPresent your strongest bear case arguments.",
            "Devils Advocate": f"{base_context}\n\nBull argues growth, Bear argues competition. Challenge both.",
            "Bull Advocate R2": f"{base_context}\n\nRespond to bear arguments and provide DCF inputs.",
            "Bear Advocate R2": f"{base_context}\n\nRespond to bull arguments and provide DCF inputs.",
            "Debate Critic": f"{base_context}\n\nEvaluate the debate and synthesize DCF inputs.",
            "Pre-Model Validator": f"{base_context}\n\nValidate: Growth 15%, Margin 20%, WACC 10%.",
            "Financial Modeler": f"{base_context}\n\nBuild DCF with base growth 15%, margin 20%.",
            "Assumption Challenger": f"{base_context}\n\nDCF shows target HKD 65. Challenge assumptions.",
            "Comparable Validator": f"{base_context}\n\nCompare valuation to peers in AI sector.",
            "Sensitivity Auditor": f"{base_context}\n\nTest DCF sensitivity to WACC and growth.",
            "Valuation Committee": f"{base_context}\n\nReview DCF. No critical issues found.",
            "Data Verification Gate": f"{base_context}\n\nPrice: HKD 52.30, Market Cap: HKD 30B.",
            "Logic Verification Gate": f"{base_context}\n\nRecommendation: BUY, Target: HKD 65, Upside: 24%.",
            "Birds Eye Reviewer": f"{base_context}\n\nFull research complete. Review holistically.",
            "Quality Supervisor": f"{base_context}\n\nData Gate: PASS, Logic Gate: PASS, Bird's Eye: APPROVED.",
            "Synthesizer": f"{base_context}\n\nCreate final research report.",
        }

        content = node_inputs.get(node_id, base_context)
        return Message(role="user", content=content, source="test_validator")

    def _validate_output(self, node_id: str, node_config: NodeConfig, output: str) -> bool:
        """Validate that output contains expected content"""
        output_lower = output.lower()

        # Node-specific expected content
        expectations = {
            "Research Supervisor": ["research", "plan"],
            "Market Data Collector": ["price", "market cap"],
            "Industry Deep Dive": ["market", "industry", "tam"],
            "Company Deep Dive": ["company", "business"],
            "Data Verifier": ["verify", "price"],
            "Data Checkpoint": ["data:", "verified", "pass"],
            "Debate Moderator": ["debate", "bull", "bear"],
            "Bull Advocate R1": ["bull", "growth", "upside"],
            "Bear Advocate R1": ["bear", "risk", "downside"],
            "Devils Advocate": ["challenge", "weakness"],
            "Bull Advocate R2": ["rebuttal", "respond"],
            "Bear Advocate R2": ["rebuttal", "respond"],
            "Debate Critic": ["score", "synthesis"],
            "Pre-Model Validator": ["inputs:", "validated"],
            "Financial Modeler": ["dcf", "scenario", "wacc"],
            "Assumption Challenger": ["assumption", "challenge"],
            "Comparable Validator": ["peer", "comparable"],
            "Sensitivity Auditor": ["sensitivity", "wacc"],
            "Valuation Committee": ["valuation:", "approved"],
            "Data Verification Gate": ["data", "gate", "pass"],
            "Logic Verification Gate": ["logic", "gate", "pass"],
            "Birds Eye Reviewer": ["review", "quality"],
            "Quality Supervisor": ["route:", "synthesizer"],
            "Synthesizer": ["executive", "recommendation"],
        }

        expected = expectations.get(node_id, [])
        if not expected:
            return len(output) > 100  # Default: just check non-empty

        # Check if at least half of expected keywords are present
        found = sum(1 for kw in expected if kw in output_lower)
        return found >= len(expected) / 2

    def _is_asking_for_input(self, output: str) -> bool:
        """Check if node is asking for input instead of executing"""
        asking_patterns = [
            "please provide",
            "please specify",
            "what is the ticker",
            "i need more information",
            "could you provide",
            "i understand. i will act as",
        ]
        output_lower = output.lower()
        return any(p in output_lower for p in asking_patterns)

    def _has_search_results(self, output: str) -> bool:
        """Check if web search appears to have executed"""
        # If output contains specific numbers or dates, likely searched
        has_numbers = bool(re.search(r'\$[\d,]+|\d+\.\d+%|\d{4}', output))
        has_sources = any(s in output.lower() for s in ['source', 'according to', 'reports', 'data shows'])
        return has_numbers or has_sources

    def _identify_critical_issues(self) -> List[str]:
        """Identify critical issues from test results"""
        critical = []

        for node_id, result in self.results.items():
            if not result.success:
                if "Timeout" in str(result.issues):
                    critical.append(f"{node_id}: Timeout - may be stuck or rate limited")
                elif "asking for input" in str(result.issues):
                    critical.append(f"{node_id}: Not executing - asking for input instead")
                elif "Web search" in str(result.issues):
                    critical.append(f"{node_id}: Web search tool not working")

        # Check for flow-breaking issues
        critical_nodes = ["Data Checkpoint", "Pre-Model Validator", "Valuation Committee"]
        for cn in critical_nodes:
            if cn in self.results and not self.results[cn].success:
                critical.append(f"{cn}: Gate node failing will break workflow flow")

        return critical

    def _print_summary(self, report: ValidationReport):
        """Print validation summary"""
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"Workflow: {report.workflow_name}")
        print(f"Nodes Tested: {report.nodes_tested}/{report.total_nodes}")
        print(f"Passed: {report.nodes_passed}")
        print(f"Failed: {report.nodes_failed}")

        if report.critical_issues:
            print(f"\nCRITICAL ISSUES ({len(report.critical_issues)}):")
            for issue in report.critical_issues:
                print(f"  [!] {issue}")

        print("\nDETAILED RESULTS:")
        for node_id, result in report.results.items():
            status = "PASS" if result.success else "FAIL"
            print(f"  [{status}] {node_id}")
            if result.issues:
                for issue in result.issues:
                    print(f"        - {issue}")

        print("="*60)


# CLI interface
if __name__ == "__main__":
    import sys

    workflow = sys.argv[1] if len(sys.argv) > 1 else "equity_research_v4"
    ticker = sys.argv[2] if len(sys.argv) > 2 else "6682 HK"

    validator = NodeFunctionValidator(workflow)

    async def main():
        report = await validator.validate_all_nodes(ticker)

        # Save report
        report_path = Path(f"context/node_validation_{workflow}.json")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump({
                'workflow_name': report.workflow_name,
                'total_nodes': report.total_nodes,
                'nodes_tested': report.nodes_tested,
                'nodes_passed': report.nodes_passed,
                'nodes_failed': report.nodes_failed,
                'critical_issues': report.critical_issues,
                'results': {
                    k: {
                        'success': v.success,
                        'output_length': v.output_length,
                        'execution_time': v.execution_time,
                        'issues': v.issues,
                        'output_preview': v.output_preview
                    }
                    for k, v in report.results.items()
                },
                'timestamp': report.timestamp
            }, f, indent=2)

        print(f"\nReport saved to: {report_path}")

    asyncio.run(main())
