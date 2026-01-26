"""
Performance Monitor Agent - Tracks and analyzes system performance.

Monitors API usage, execution times, success rates, and cost metrics
across all workflow executions.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from ..core.spawnable_agent import SpawnableAgent


@dataclass
class APIUsageMetrics:
    """Metrics for a single API provider"""
    provider: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    rate_limit_hits: int = 0
    last_call: Optional[datetime] = None


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution"""
    workflow_id: str
    ticker: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    nodes_executed: int = 0
    nodes_failed: int = 0
    iterations: int = 0
    success: bool = False
    error: Optional[str] = None


@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    generated_at: datetime
    period_start: datetime
    period_end: datetime

    # Workflow metrics
    total_workflows: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    avg_duration_seconds: float = 0.0

    # API metrics by provider
    api_metrics: Dict[str, APIUsageMetrics] = field(default_factory=dict)

    # Cost analysis
    total_cost_usd: float = 0.0
    cost_by_provider: Dict[str, float] = field(default_factory=dict)

    # Performance issues
    slow_workflows: List[str] = field(default_factory=list)
    high_failure_nodes: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'generated_at': self.generated_at.isoformat(),
            'period': {
                'start': self.period_start.isoformat(),
                'end': self.period_end.isoformat()
            },
            'workflows': {
                'total': self.total_workflows,
                'successful': self.successful_workflows,
                'failed': self.failed_workflows,
                'success_rate': self.successful_workflows / self.total_workflows if self.total_workflows else 0,
                'avg_duration_seconds': self.avg_duration_seconds
            },
            'api_metrics': {
                provider: {
                    'total_calls': m.total_calls,
                    'successful_calls': m.successful_calls,
                    'failed_calls': m.failed_calls,
                    'success_rate': m.successful_calls / m.total_calls if m.total_calls else 0,
                    'total_tokens': m.total_tokens,
                    'total_cost_usd': m.total_cost_usd,
                    'avg_latency_ms': m.avg_latency_ms,
                    'rate_limit_hits': m.rate_limit_hits
                }
                for provider, m in self.api_metrics.items()
            },
            'costs': {
                'total_usd': self.total_cost_usd,
                'by_provider': self.cost_by_provider
            },
            'issues': {
                'slow_workflows': self.slow_workflows,
                'high_failure_nodes': self.high_failure_nodes
            },
            'recommendations': self.recommendations
        }


class PerformanceMonitorAgent(SpawnableAgent):
    """
    Performance Monitor - Tracks system performance metrics.

    Capabilities:
    - Track API usage across providers
    - Monitor workflow execution times
    - Calculate costs
    - Identify performance bottlenecks
    - Generate performance reports
    """

    # Cost per 1K tokens (approximate)
    TOKEN_COSTS = {
        'openai': {'input': 0.005, 'output': 0.015},  # GPT-4o
        'google': {'input': 0.00025, 'output': 0.0005},  # Gemini Flash
        'xai': {'input': 0.002, 'output': 0.006},  # Grok
        'dashscope': {'input': 0.001, 'output': 0.002},  # Qwen
        'deepseek': {'input': 0.0005, 'output': 0.001},  # DeepSeek
    }

    def __init__(
        self,
        name: str = "PerformanceMonitor",
        project_root: str = ".",
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="Performance Monitor",
            tier=1,
            parent=parent_agent
        )

        self.project_root = Path(project_root)
        self.metrics_file = self.project_root / "context" / "performance_metrics.json"

        # In-memory metrics
        self.api_metrics: Dict[str, APIUsageMetrics] = {}
        self.workflow_metrics: List[WorkflowMetrics] = []
        self.node_failure_counts: Dict[str, int] = defaultdict(int)

        # Load historical metrics
        self._load_metrics()

    def _load_metrics(self):
        """Load metrics from file"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)

                for provider, metrics in data.get('api_metrics', {}).items():
                    self.api_metrics[provider] = APIUsageMetrics(
                        provider=provider,
                        total_calls=metrics.get('total_calls', 0),
                        successful_calls=metrics.get('successful_calls', 0),
                        failed_calls=metrics.get('failed_calls', 0),
                        total_tokens=metrics.get('total_tokens', 0),
                        total_cost_usd=metrics.get('total_cost_usd', 0),
                        avg_latency_ms=metrics.get('avg_latency_ms', 0),
                        rate_limit_hits=metrics.get('rate_limit_hits', 0)
                    )

                self.node_failure_counts = defaultdict(
                    int,
                    data.get('node_failure_counts', {})
                )

            except Exception as e:
                print(f"[PerformanceMonitor] Could not load metrics: {e}")

    def _save_metrics(self):
        """Save metrics to file"""
        try:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'api_metrics': {
                    provider: {
                        'total_calls': m.total_calls,
                        'successful_calls': m.successful_calls,
                        'failed_calls': m.failed_calls,
                        'total_tokens': m.total_tokens,
                        'total_cost_usd': m.total_cost_usd,
                        'avg_latency_ms': m.avg_latency_ms,
                        'rate_limit_hits': m.rate_limit_hits
                    }
                    for provider, m in self.api_metrics.items()
                },
                'node_failure_counts': dict(self.node_failure_counts),
                'saved_at': datetime.now().isoformat()
            }

            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[PerformanceMonitor] Could not save metrics: {e}")

    # ==================== TRACKING METHODS ====================

    def track_api_call(
        self,
        provider: str,
        success: bool,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: float = 0,
        rate_limited: bool = False
    ):
        """Track an API call"""
        if provider not in self.api_metrics:
            self.api_metrics[provider] = APIUsageMetrics(provider=provider)

        metrics = self.api_metrics[provider]
        metrics.total_calls += 1
        metrics.last_call = datetime.now()

        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1

        if rate_limited:
            metrics.rate_limit_hits += 1

        # Update tokens and cost
        total_tokens = tokens_in + tokens_out
        metrics.total_tokens += total_tokens

        cost = self._calculate_cost(provider, tokens_in, tokens_out)
        metrics.total_cost_usd += cost

        # Update average latency
        if latency_ms > 0:
            n = metrics.total_calls
            metrics.avg_latency_ms = (
                (metrics.avg_latency_ms * (n - 1) + latency_ms) / n
            )

        self._save_metrics()

    def track_workflow(
        self,
        workflow_id: str,
        ticker: str,
        started_at: datetime,
        completed_at: Optional[datetime],
        nodes_executed: int,
        nodes_failed: int,
        iterations: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Track a workflow execution"""
        duration = 0.0
        if completed_at:
            duration = (completed_at - started_at).total_seconds()

        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            ticker=ticker,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            nodes_executed=nodes_executed,
            nodes_failed=nodes_failed,
            iterations=iterations,
            success=success,
            error=error
        )

        self.workflow_metrics.append(metrics)

        # Keep only last 100 workflows in memory
        if len(self.workflow_metrics) > 100:
            self.workflow_metrics = self.workflow_metrics[-100:]

    def track_node_failure(self, node_id: str):
        """Track a node failure"""
        self.node_failure_counts[node_id] += 1
        self._save_metrics()

    def _calculate_cost(self, provider: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate cost for an API call"""
        costs = self.TOKEN_COSTS.get(provider.lower(), {'input': 0.001, 'output': 0.002})
        cost = (tokens_in / 1000 * costs['input']) + (tokens_out / 1000 * costs['output'])
        return cost

    # ==================== ANALYSIS METHODS ====================

    async def analyze_workflow_logs(self) -> Dict[str, Any]:
        """Analyze all workflow execution logs in context folder"""
        context_path = self.project_root / "context"
        workflow_files = list(context_path.glob("*_workflow_result.json"))

        analyzed = []

        for wf_file in workflow_files:
            try:
                with open(wf_file, 'r') as f:
                    data = json.load(f)

                ticker = data.get('ticker', wf_file.stem)
                execution_log = data.get('execution_log', [])
                node_outputs = data.get('node_outputs', {})

                # Extract metrics
                nodes_executed = len(node_outputs)
                iterations = data.get('iterations', 0)

                # Count errors
                errors = [
                    entry for entry in execution_log
                    if entry.get('event') in ['node_error', 'error_output_detected']
                ]

                # Calculate duration from log
                duration = 0.0
                if execution_log:
                    try:
                        start_time = datetime.fromisoformat(execution_log[0].get('timestamp', ''))
                        end_time = datetime.fromisoformat(execution_log[-1].get('timestamp', ''))
                        duration = (end_time - start_time).total_seconds()
                    except:
                        pass

                analyzed.append({
                    'ticker': ticker,
                    'file': str(wf_file),
                    'nodes_executed': nodes_executed,
                    'iterations': iterations,
                    'error_count': len(errors),
                    'duration_seconds': duration,
                    'success': len(errors) == 0
                })

                # Track node failures
                for entry in execution_log:
                    if entry.get('event') == 'node_error':
                        node_id = entry.get('node_id', 'unknown')
                        self.track_node_failure(node_id)

            except Exception as e:
                analyzed.append({
                    'ticker': wf_file.stem,
                    'file': str(wf_file),
                    'error': str(e)
                })

        return {
            'analyzed_count': len(analyzed),
            'workflows': analyzed
        }

    def get_api_usage_summary(self) -> Dict[str, Any]:
        """Get summary of API usage"""
        total_calls = sum(m.total_calls for m in self.api_metrics.values())
        total_cost = sum(m.total_cost_usd for m in self.api_metrics.values())
        total_tokens = sum(m.total_tokens for m in self.api_metrics.values())

        return {
            'total_calls': total_calls,
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost,
            'by_provider': {
                provider: {
                    'calls': m.total_calls,
                    'tokens': m.total_tokens,
                    'cost_usd': m.total_cost_usd,
                    'success_rate': m.successful_calls / m.total_calls if m.total_calls else 0,
                    'avg_latency_ms': m.avg_latency_ms
                }
                for provider, m in self.api_metrics.items()
            }
        }

    def get_high_failure_nodes(self, threshold: int = 3) -> List[Dict]:
        """Get nodes with high failure counts"""
        high_failures = []

        for node_id, count in self.node_failure_counts.items():
            if count >= threshold:
                high_failures.append({
                    'node_id': node_id,
                    'failure_count': count
                })

        return sorted(high_failures, key=lambda x: x['failure_count'], reverse=True)

    # ==================== REPORT GENERATION ====================

    async def generate_report(
        self,
        period_days: int = 7
    ) -> PerformanceReport:
        """Generate comprehensive performance report"""
        now = datetime.now()
        period_start = now - timedelta(days=period_days)

        report = PerformanceReport(
            generated_at=now,
            period_start=period_start,
            period_end=now
        )

        # Analyze workflow logs
        workflow_analysis = await self.analyze_workflow_logs()

        workflows = workflow_analysis.get('workflows', [])
        report.total_workflows = len(workflows)
        report.successful_workflows = sum(1 for w in workflows if w.get('success', False))
        report.failed_workflows = report.total_workflows - report.successful_workflows

        durations = [w.get('duration_seconds', 0) for w in workflows if w.get('duration_seconds', 0) > 0]
        if durations:
            report.avg_duration_seconds = sum(durations) / len(durations)

        # Identify slow workflows (>10 minutes)
        report.slow_workflows = [
            w.get('ticker', 'unknown')
            for w in workflows
            if w.get('duration_seconds', 0) > 600
        ]

        # API metrics
        report.api_metrics = self.api_metrics.copy()

        # Calculate total cost
        report.total_cost_usd = sum(m.total_cost_usd for m in self.api_metrics.values())
        report.cost_by_provider = {
            provider: m.total_cost_usd
            for provider, m in self.api_metrics.items()
        }

        # High failure nodes
        high_failures = self.get_high_failure_nodes()
        report.high_failure_nodes = [f"{n['node_id']} ({n['failure_count']} failures)" for n in high_failures]

        # Generate recommendations
        if report.failed_workflows > report.successful_workflows:
            report.recommendations.append(
                "High workflow failure rate - investigate common failure points"
            )

        if report.slow_workflows:
            report.recommendations.append(
                f"{len(report.slow_workflows)} workflows took >10 minutes - consider optimization"
            )

        for provider, metrics in self.api_metrics.items():
            if metrics.rate_limit_hits > 5:
                report.recommendations.append(
                    f"{provider} hit rate limits {metrics.rate_limit_hits} times - consider reducing concurrency"
                )

            if metrics.total_calls > 0:
                fail_rate = metrics.failed_calls / metrics.total_calls
                if fail_rate > 0.1:
                    report.recommendations.append(
                        f"{provider} has {fail_rate:.0%} failure rate - investigate API issues"
                    )

        if high_failures:
            report.recommendations.append(
                f"Nodes with frequent failures: {', '.join(n['node_id'] for n in high_failures[:3])}"
            )

        return report

    async def save_report(self, report: PerformanceReport):
        """Save performance report to file"""
        report_path = self.project_root / "context" / "performance_report.json"

        try:
            with open(report_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)

            print(f"[PerformanceMonitor] Report saved to {report_path}")

        except Exception as e:
            print(f"[PerformanceMonitor] Could not save report: {e}")
