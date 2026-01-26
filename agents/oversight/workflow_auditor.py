"""
Workflow Auditor Agent - Sub-agent for auditing workflow definitions and execution.

Spawned by Chief Engineer to validate workflow YAML definitions,
check edge connectivity, and audit workflow execution logs.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..core.spawnable_agent import SpawnableAgent


@dataclass
class WorkflowAuditReport:
    """Comprehensive workflow audit report"""
    workflow_name: str
    audited_at: datetime

    # Structure validation
    node_count: int = 0
    edge_count: int = 0
    orphan_nodes: List[str] = field(default_factory=list)
    unreachable_nodes: List[str] = field(default_factory=list)
    missing_nodes: List[str] = field(default_factory=list)

    # Connectivity
    start_nodes: List[str] = field(default_factory=list)
    end_nodes: List[str] = field(default_factory=list)
    cycles_detected: List[List[str]] = field(default_factory=list)

    # Provider analysis
    providers_used: Dict[str, int] = field(default_factory=dict)
    nodes_per_tier: Dict[str, int] = field(default_factory=dict)

    # Issues and recommendations
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Validation status
    is_valid: bool = True

    def to_dict(self) -> Dict:
        return {
            'workflow_name': self.workflow_name,
            'audited_at': self.audited_at.isoformat(),
            'structure': {
                'node_count': self.node_count,
                'edge_count': self.edge_count,
                'orphan_nodes': self.orphan_nodes,
                'unreachable_nodes': self.unreachable_nodes,
                'missing_nodes': self.missing_nodes
            },
            'connectivity': {
                'start_nodes': self.start_nodes,
                'end_nodes': self.end_nodes,
                'cycles_detected': self.cycles_detected
            },
            'analysis': {
                'providers_used': self.providers_used,
                'nodes_per_tier': self.nodes_per_tier
            },
            'issues': {
                'critical': self.critical_issues,
                'warnings': self.warnings
            },
            'recommendations': self.recommendations,
            'is_valid': self.is_valid
        }


class WorkflowAuditorAgent(SpawnableAgent):
    """
    Workflow Auditor - Deep workflow analysis sub-agent.

    Tools available:
    - parse_workflow: Parse YAML workflow definition
    - validate_connectivity: Check node connectivity
    - detect_cycles: Find cycles in workflow graph
    - analyze_providers: Analyze AI provider distribution
    - check_conditions: Validate edge conditions
    - audit_execution: Audit workflow execution logs
    """

    # Required nodes for equity research workflow
    REQUIRED_NODES = [
        'START',
        'Research Supervisor',
        'Market Data Collector',
        'Data Checkpoint',
        'Debate Moderator',
        'Financial Modeler',
        'Valuation Committee',
        'Synthesizer'
    ]

    # Valid providers
    VALID_PROVIDERS = ['openai', 'google', 'gemini', 'xai', 'grok', 'dashscope', 'qwen', 'deepseek']

    def __init__(
        self,
        name: str,
        project_root: str,
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="Workflow Auditor",
            tier=1,
            parent=parent_agent
        )

        self.project_root = Path(project_root)
        self.audit_history: List[WorkflowAuditReport] = []

    # ==================== TOOLS ====================

    async def tool_parse_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        Tool: Parse YAML workflow and extract structure.
        """
        full_path = self.project_root / workflow_path

        if not full_path.exists():
            return {'success': False, 'error': f'Workflow not found: {workflow_path}'}

        try:
            import yaml

            with open(full_path, 'r', encoding='utf-8') as f:
                workflow = yaml.safe_load(f)

            graph = workflow.get('graph', {})
            nodes = graph.get('nodes', [])
            edges = graph.get('edges', [])

            # Extract node info
            node_info = {}
            for node in nodes:
                node_id = node.get('id')
                if node_id:
                    config = node.get('config', {})
                    node_info[node_id] = {
                        'type': node.get('type', 'agent'),
                        'provider': config.get('provider', 'unknown'),
                        'model': config.get('name', 'unknown'),
                        'has_tools': 'tooling' in config,
                        'context_window': node.get('context_window', 0)
                    }

            # Extract edge info
            edge_info = []
            for edge in edges:
                edge_info.append({
                    'from': edge.get('from'),
                    'to': edge.get('to'),
                    'trigger': edge.get('trigger', False),
                    'carry_data': edge.get('carry_data', False),
                    'condition': edge.get('condition')
                })

            return {
                'success': True,
                'workflow_id': graph.get('id'),
                'description': graph.get('description'),
                'max_iterations': graph.get('max_iterations', 20),
                'nodes': node_info,
                'edges': edge_info,
                'node_count': len(nodes),
                'edge_count': len(edges)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def tool_validate_connectivity(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Tool: Validate node connectivity - find orphans and unreachable nodes.
        """
        nodes = set(workflow_data.get('nodes', {}).keys())
        edges = workflow_data.get('edges', [])

        # Build adjacency lists
        outgoing = {node: [] for node in nodes}
        incoming = {node: [] for node in nodes}

        referenced_nodes = set()

        for edge in edges:
            from_node = edge.get('from')
            to_node = edge.get('to')

            referenced_nodes.add(from_node)
            referenced_nodes.add(to_node)

            if from_node in outgoing:
                outgoing[from_node].append(to_node)
            if to_node in incoming:
                incoming[to_node].append(from_node)

        # Find nodes with no outgoing edges (potential end nodes)
        end_nodes = [n for n in nodes if not outgoing.get(n)]

        # Find nodes with no incoming edges (potential start nodes)
        start_nodes = [n for n in nodes if not incoming.get(n)]

        # Find orphan nodes (no connections at all)
        orphan_nodes = [n for n in nodes if not outgoing.get(n) and not incoming.get(n)]

        # Find unreachable nodes (can't be reached from START)
        reachable = set()
        queue = ['START'] if 'START' in nodes else list(start_nodes)

        while queue:
            node = queue.pop(0)
            if node not in reachable:
                reachable.add(node)
                queue.extend(outgoing.get(node, []))

        unreachable = [n for n in nodes if n not in reachable and n != 'START']

        # Find missing nodes (referenced in edges but not defined)
        missing_nodes = list(referenced_nodes - nodes)

        return {
            'success': True,
            'start_nodes': start_nodes,
            'end_nodes': end_nodes,
            'orphan_nodes': orphan_nodes,
            'unreachable_nodes': unreachable,
            'missing_nodes': missing_nodes,
            'reachable_count': len(reachable),
            'total_nodes': len(nodes)
        }

    async def tool_detect_cycles(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Tool: Detect cycles in the workflow graph.
        """
        nodes = set(workflow_data.get('nodes', {}).keys())
        edges = workflow_data.get('edges', [])

        # Build adjacency list
        graph = {node: [] for node in nodes}
        for edge in edges:
            if edge.get('from') in graph:
                graph[edge.get('from')].append(edge.get('to'))

        # DFS-based cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in nodes}
        cycles = []

        def dfs(node, path):
            color[node] = GRAY
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in color:
                    continue

                if color[neighbor] == GRAY:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path.copy())

            color[node] = BLACK

        for node in nodes:
            if color[node] == WHITE:
                dfs(node, [])

        return {
            'success': True,
            'has_cycles': len(cycles) > 0,
            'cycles': cycles,
            'cycle_count': len(cycles)
        }

    async def tool_analyze_providers(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Tool: Analyze AI provider distribution across workflow.
        """
        nodes = workflow_data.get('nodes', {})

        providers = {}
        models = {}
        nodes_with_tools = []

        for node_id, node_info in nodes.items():
            provider = node_info.get('provider', 'unknown').lower()
            model = node_info.get('model', 'unknown')

            if provider not in providers:
                providers[provider] = []
            providers[provider].append(node_id)

            if model not in models:
                models[model] = []
            models[model].append(node_id)

            if node_info.get('has_tools'):
                nodes_with_tools.append(node_id)

        # Calculate distribution
        total_nodes = len(nodes)
        provider_distribution = {
            p: {'nodes': n, 'percentage': len(n) / total_nodes * 100}
            for p, n in providers.items()
        }

        # Check for over-reliance on single provider
        warnings = []
        for provider, data in provider_distribution.items():
            if data['percentage'] > 50:
                warnings.append(f"Over-reliance on {provider} ({data['percentage']:.1f}% of nodes)")

        return {
            'success': True,
            'providers': provider_distribution,
            'models': {m: len(n) for m, n in models.items()},
            'nodes_with_tools': nodes_with_tools,
            'tool_enabled_count': len(nodes_with_tools),
            'warnings': warnings
        }

    async def tool_check_conditions(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Tool: Validate edge conditions for correctness.
        """
        edges = workflow_data.get('edges', [])

        issues = []
        condition_stats = {
            'always_true': 0,
            'keyword_based': 0,
            'complex': 0
        }

        for i, edge in enumerate(edges):
            condition = edge.get('condition')
            from_node = edge.get('from')
            to_node = edge.get('to')

            if condition == 'true' or condition is True:
                condition_stats['always_true'] += 1
            elif isinstance(condition, dict):
                condition_stats['complex'] += 1

                # Check keyword conditions
                cond_type = condition.get('type')
                if cond_type == 'keyword':
                    keywords = condition.get('config', {}).get('any', [])
                    if not keywords:
                        issues.append(f"Edge {from_node} -> {to_node}: Empty keyword condition")
            elif condition is None:
                issues.append(f"Edge {from_node} -> {to_node}: Missing condition")

        # Check for potential routing issues
        nodes_with_conditions = {}
        for edge in edges:
            from_node = edge.get('from')
            if from_node not in nodes_with_conditions:
                nodes_with_conditions[from_node] = []
            nodes_with_conditions[from_node].append(edge)

        for node, node_edges in nodes_with_conditions.items():
            conditional_edges = [e for e in node_edges if e.get('condition') not in ['true', True, None]]
            if len(conditional_edges) > 1:
                # Check if conditions could overlap or be mutually exclusive
                pass  # Complex logic - simplified for now

        return {
            'success': True,
            'condition_stats': condition_stats,
            'issues': issues,
            'total_edges': len(edges)
        }

    async def tool_audit_execution(self, execution_log_path: str) -> Dict[str, Any]:
        """
        Tool: Audit workflow execution log for issues.
        """
        full_path = self.project_root / execution_log_path

        if not full_path.exists():
            return {'success': False, 'error': 'Execution log not found'}

        try:
            with open(full_path, 'r') as f:
                execution_data = json.load(f)

            log = execution_data.get('execution_log', [])
            node_outputs = execution_data.get('node_outputs', {})

            # Analyze execution
            nodes_executed = set()
            errors = []
            warnings = []
            execution_times = {}

            for entry in log:
                event = entry.get('event')
                node_id = entry.get('node_id')
                details = entry.get('details', {})

                if event == 'node_complete':
                    nodes_executed.add(node_id)
                elif event == 'node_error':
                    errors.append({
                        'node': node_id,
                        'error': details.get('error')
                    })
                elif event == 'error_output_detected':
                    warnings.append({
                        'node': node_id,
                        'issue': 'Error output detected',
                        'content': details.get('error_content', '')[:100]
                    })

            # Check for price verification issues
            price_issues = []
            for node_id, outputs in node_outputs.items():
                for output in outputs:
                    content = output.get('content', '')
                    if 'VERIFIED_CURRENT_PRICE' not in content and 'Financial Modeler' in node_id:
                        price_issues.append(f"{node_id}: May not have used verified price")

            return {
                'success': True,
                'nodes_executed': list(nodes_executed),
                'execution_count': len(nodes_executed),
                'errors': errors,
                'warnings': warnings,
                'price_issues': price_issues,
                'iterations': execution_data.get('iterations', 0)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== AUDIT METHODS ====================

    async def audit_workflow(
        self,
        workflow_path: str = "workflow/definitions/equity_research_v4.yaml"
    ) -> WorkflowAuditReport:
        """
        Perform comprehensive workflow audit.
        """
        report = WorkflowAuditReport(
            workflow_name=workflow_path,
            audited_at=datetime.now()
        )

        # Parse workflow
        parse_result = await self.tool_parse_workflow(workflow_path)

        if not parse_result.get('success'):
            report.critical_issues.append(f"Could not parse workflow: {parse_result.get('error')}")
            report.is_valid = False
            return report

        report.node_count = parse_result.get('node_count', 0)
        report.edge_count = parse_result.get('edge_count', 0)

        # Validate connectivity
        connectivity = await self.tool_validate_connectivity(parse_result)
        if connectivity.get('success'):
            report.start_nodes = connectivity.get('start_nodes', [])
            report.end_nodes = connectivity.get('end_nodes', [])
            report.orphan_nodes = connectivity.get('orphan_nodes', [])
            report.unreachable_nodes = connectivity.get('unreachable_nodes', [])
            report.missing_nodes = connectivity.get('missing_nodes', [])

            if report.orphan_nodes:
                report.warnings.append(f"Orphan nodes found: {report.orphan_nodes}")
            if report.unreachable_nodes:
                report.critical_issues.append(f"Unreachable nodes: {report.unreachable_nodes}")
            if report.missing_nodes:
                report.critical_issues.append(f"Missing node definitions: {report.missing_nodes}")

        # Detect cycles
        cycles = await self.tool_detect_cycles(parse_result)
        if cycles.get('success'):
            report.cycles_detected = cycles.get('cycles', [])
            if report.cycles_detected:
                report.warnings.append(f"Cycles detected (may be intentional for feedback loops)")

        # Analyze providers
        providers = await self.tool_analyze_providers(parse_result)
        if providers.get('success'):
            report.providers_used = {
                p: len(d['nodes'])
                for p, d in providers.get('providers', {}).items()
            }
            for warning in providers.get('warnings', []):
                report.warnings.append(warning)

        # Check conditions
        conditions = await self.tool_check_conditions(parse_result)
        if conditions.get('success'):
            for issue in conditions.get('issues', []):
                report.warnings.append(issue)

        # Check for required nodes
        nodes = set(parse_result.get('nodes', {}).keys())
        for required in self.REQUIRED_NODES:
            if required not in nodes:
                report.critical_issues.append(f"Missing required node: {required}")

        # Generate recommendations
        if 'openai' in report.providers_used:
            openai_count = report.providers_used['openai']
            if openai_count > report.node_count * 0.5:
                report.recommendations.append(
                    "Consider diversifying AI providers to reduce single-point-of-failure risk"
                )

        if not report.cycles_detected:
            report.recommendations.append(
                "No feedback loops detected - consider adding quality gate loop-backs"
            )

        # Set validity
        report.is_valid = len(report.critical_issues) == 0

        self.audit_history.append(report)
        return report

    async def validate_execution(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Validate a specific workflow execution.
        """
        log_path = f"context/{ticker.replace(' ', '_')}_workflow_result.json"

        audit_result = await self.tool_audit_execution(log_path)

        if not audit_result.get('success'):
            return {
                'valid': False,
                'error': audit_result.get('error')
            }

        issues = []

        # Check for errors
        if audit_result.get('errors'):
            issues.extend([f"Node error: {e['node']} - {e['error']}" for e in audit_result['errors']])

        # Check for price issues
        if audit_result.get('price_issues'):
            issues.extend(audit_result['price_issues'])

        # Check iteration count
        iterations = audit_result.get('iterations', 0)
        if iterations >= 20:
            issues.append(f"Hit max iterations ({iterations}) - possible infinite loop")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'nodes_executed': audit_result.get('execution_count', 0),
            'errors': audit_result.get('errors', []),
            'warnings': audit_result.get('warnings', [])
        }
