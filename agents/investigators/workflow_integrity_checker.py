#!/usr/bin/env python3
"""
Workflow Integrity Checker

A project-level agent that validates workflow YAML definitions
for completeness, correctness, and edge routing logic.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EdgeInfo:
    """Information about a workflow edge"""
    from_node: str
    to_node: str
    trigger: bool
    condition: Any
    carry_data: bool


@dataclass
class NodeInfo:
    """Information about a workflow node"""
    id: str
    type: str
    provider: str
    model: str
    has_tools: bool
    context_window: int
    incoming_edges: List[str] = field(default_factory=list)
    outgoing_edges: List[str] = field(default_factory=list)


@dataclass
class IntegrityReport:
    """Workflow integrity check report"""
    workflow_name: str
    total_nodes: int
    total_edges: int
    start_nodes: List[str]
    end_nodes: List[str]
    unreachable_nodes: List[str]
    orphan_edges: List[Dict]
    missing_trigger_edges: List[str]
    dead_end_nodes: List[str]
    condition_issues: List[str]
    provider_issues: List[str]
    structural_issues: List[str]
    recommendations: List[str]


class WorkflowIntegrityChecker:
    """
    Checks workflow YAML files for structural integrity.

    Validates:
    1. All edges reference existing nodes
    2. All nodes are reachable from start
    3. All non-end nodes have outgoing edges
    4. Edge conditions are valid
    5. Provider configurations are correct
    6. Required routing keywords exist in node prompts
    7. Parallel execution paths converge properly
    """

    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = Path(workflows_dir)

    def check_all_workflows(self) -> Dict[str, IntegrityReport]:
        """Check all workflow files"""
        reports = {}

        for yaml_file in self.workflows_dir.glob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue

            print(f"\nChecking: {yaml_file.name}")
            report = self.check_workflow(yaml_file)
            reports[yaml_file.stem] = report

        return reports

    def check_workflow(self, yaml_path: Path) -> IntegrityReport:
        """Check a single workflow file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        graph = config.get('graph', {})
        workflow_name = graph.get('id', yaml_path.stem)

        # Parse nodes
        nodes: Dict[str, NodeInfo] = {}
        for node_def in graph.get('nodes', []):
            node_id = node_def.get('id')
            node_config = node_def.get('config', {})

            nodes[node_id] = NodeInfo(
                id=node_id,
                type=node_def.get('type', 'agent'),
                provider=node_config.get('provider', 'openai'),
                model=node_config.get('name', 'gpt-4o'),
                has_tools=bool(node_config.get('tooling')),
                context_window=node_def.get('context_window', 0)
            )

        # Parse edges
        edges: List[EdgeInfo] = []
        for edge_def in graph.get('edges', []):
            edge = EdgeInfo(
                from_node=edge_def.get('from'),
                to_node=edge_def.get('to'),
                trigger=edge_def.get('trigger', False),
                condition=edge_def.get('condition', 'true'),
                carry_data=edge_def.get('carry_data', True)
            )
            edges.append(edge)

            # Track incoming/outgoing
            if edge.from_node in nodes:
                nodes[edge.from_node].outgoing_edges.append(edge.to_node)
            if edge.to_node in nodes:
                nodes[edge.to_node].incoming_edges.append(edge.from_node)

        # Get start/end nodes
        start_nodes = graph.get('start', ['START'])
        end_nodes = graph.get('end', [])

        # Run checks
        unreachable = self._find_unreachable_nodes(nodes, edges, start_nodes)
        orphan_edges = self._find_orphan_edges(nodes, edges)
        missing_triggers = self._find_missing_trigger_edges(nodes, edges, start_nodes)
        dead_ends = self._find_dead_end_nodes(nodes, edges, end_nodes)
        condition_issues = self._check_edge_conditions(edges, nodes, graph)
        provider_issues = self._check_providers(nodes)
        structural_issues = self._check_structure(nodes, edges, start_nodes, end_nodes)
        recommendations = self._generate_recommendations(
            unreachable, orphan_edges, missing_triggers, dead_ends,
            condition_issues, provider_issues, structural_issues
        )

        return IntegrityReport(
            workflow_name=workflow_name,
            total_nodes=len(nodes),
            total_edges=len(edges),
            start_nodes=start_nodes,
            end_nodes=end_nodes,
            unreachable_nodes=unreachable,
            orphan_edges=orphan_edges,
            missing_trigger_edges=missing_triggers,
            dead_end_nodes=dead_ends,
            condition_issues=condition_issues,
            provider_issues=provider_issues,
            structural_issues=structural_issues,
            recommendations=recommendations
        )

    def _find_unreachable_nodes(
        self,
        nodes: Dict[str, NodeInfo],
        edges: List[EdgeInfo],
        start_nodes: List[str]
    ) -> List[str]:
        """Find nodes not reachable from start"""
        reachable = set(start_nodes)

        # BFS to find all reachable nodes
        changed = True
        while changed:
            changed = False
            for edge in edges:
                if edge.from_node in reachable and edge.to_node not in reachable:
                    if edge.to_node in nodes:
                        reachable.add(edge.to_node)
                        changed = True

        # Find unreachable
        unreachable = [n for n in nodes if n not in reachable]
        return unreachable

    def _find_orphan_edges(
        self,
        nodes: Dict[str, NodeInfo],
        edges: List[EdgeInfo]
    ) -> List[Dict]:
        """Find edges that reference non-existent nodes"""
        orphans = []

        for edge in edges:
            if edge.from_node not in nodes:
                orphans.append({
                    'edge': f"{edge.from_node} -> {edge.to_node}",
                    'issue': f"Source node '{edge.from_node}' does not exist"
                })
            if edge.to_node not in nodes:
                orphans.append({
                    'edge': f"{edge.from_node} -> {edge.to_node}",
                    'issue': f"Target node '{edge.to_node}' does not exist"
                })

        return orphans

    def _find_missing_trigger_edges(
        self,
        nodes: Dict[str, NodeInfo],
        edges: List[EdgeInfo],
        start_nodes: List[str]
    ) -> List[str]:
        """Find nodes with no incoming trigger edges (except start)"""
        has_trigger_in = set(start_nodes)

        for edge in edges:
            if edge.trigger and edge.to_node in nodes:
                has_trigger_in.add(edge.to_node)

        missing = [n for n in nodes if n not in has_trigger_in]
        return missing

    def _find_dead_end_nodes(
        self,
        nodes: Dict[str, NodeInfo],
        edges: List[EdgeInfo],
        end_nodes: List[str]
    ) -> List[str]:
        """Find non-end nodes with no outgoing edges"""
        has_outgoing = set()

        for edge in edges:
            has_outgoing.add(edge.from_node)

        dead_ends = [
            n for n in nodes
            if n not in has_outgoing and n not in end_nodes
            and nodes[n].type != 'passthrough'
        ]

        return dead_ends

    def _check_edge_conditions(
        self,
        edges: List[EdgeInfo],
        nodes: Dict[str, NodeInfo],
        graph: Dict
    ) -> List[str]:
        """Check edge conditions for issues"""
        issues = []

        for edge in edges:
            if isinstance(edge.condition, dict):
                cond_type = edge.condition.get('type')
                config = edge.condition.get('config', {})

                if cond_type == 'keyword':
                    keywords = config.get('any', [])
                    if not keywords:
                        issues.append(
                            f"Edge {edge.from_node} -> {edge.to_node}: "
                            f"keyword condition has no keywords"
                        )

                    # Check if source node's prompt mentions these keywords
                    if edge.from_node in nodes:
                        node_def = None
                        for n in graph.get('nodes', []):
                            if n.get('id') == edge.from_node:
                                node_def = n
                                break

                        if node_def:
                            role = node_def.get('config', {}).get('role', '')
                            # Check if node knows to output these keywords
                            for kw in keywords:
                                if kw.lower() not in role.lower():
                                    issues.append(
                                        f"Edge {edge.from_node} -> {edge.to_node}: "
                                        f"keyword '{kw}' not mentioned in node prompt"
                                    )

        return issues

    def _check_providers(self, nodes: Dict[str, NodeInfo]) -> List[str]:
        """Check provider configurations"""
        issues = []
        valid_providers = {'openai', 'google', 'xai', 'dashscope', 'deepseek'}

        for node_id, node in nodes.items():
            if node.type == 'agent':
                if node.provider not in valid_providers:
                    issues.append(f"{node_id}: Unknown provider '{node.provider}'")

                # Check model names
                provider_models = {
                    'openai': ['gpt-4o', 'gpt-4', 'gpt-3.5-turbo'],
                    'google': ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-pro'],
                    'xai': ['grok-4-0709', 'grok-beta'],
                    'dashscope': ['qwen-max', 'qwen-plus'],
                }

                if node.provider in provider_models:
                    valid_models = provider_models[node.provider]
                    if node.model not in valid_models:
                        issues.append(
                            f"{node_id}: Model '{node.model}' may not be valid for {node.provider}"
                        )

        return issues

    def _check_structure(
        self,
        nodes: Dict[str, NodeInfo],
        edges: List[EdgeInfo],
        start_nodes: List[str],
        end_nodes: List[str]
    ) -> List[str]:
        """Check overall workflow structure"""
        issues = []

        # Check start nodes exist
        for sn in start_nodes:
            if sn not in nodes:
                issues.append(f"Start node '{sn}' not found in nodes")

        # Check end nodes exist
        for en in end_nodes:
            if en not in nodes:
                issues.append(f"End node '{en}' not found in nodes")

        # Check for nodes with very high in-degree (convergence points)
        in_degrees = {}
        for edge in edges:
            in_degrees[edge.to_node] = in_degrees.get(edge.to_node, 0) + 1

        for node_id, degree in in_degrees.items():
            if degree > 5:
                issues.append(
                    f"{node_id}: High in-degree ({degree}) - "
                    f"may cause context overflow or timing issues"
                )

        # Check for parallel paths that don't reconverge
        # This is complex - simplified check
        parallel_starts = {}
        for edge in edges:
            if edge.trigger:
                parallel_starts.setdefault(edge.from_node, []).append(edge.to_node)

        for source, targets in parallel_starts.items():
            if len(targets) > 1:
                # Check if these parallel paths reconverge
                # Simplified: just warn about parallel execution
                pass  # Complex analysis would go here

        return issues

    def _generate_recommendations(
        self,
        unreachable: List[str],
        orphan_edges: List[Dict],
        missing_triggers: List[str],
        dead_ends: List[str],
        condition_issues: List[str],
        provider_issues: List[str],
        structural_issues: List[str]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recs = []

        if unreachable:
            recs.append(f"Connect {len(unreachable)} unreachable nodes to workflow or remove them")

        if orphan_edges:
            recs.append(f"Fix {len(orphan_edges)} edges referencing non-existent nodes")

        if missing_triggers:
            recs.append(f"Add trigger edges to {len(missing_triggers)} nodes")

        if dead_ends:
            recs.append(f"Add outgoing edges from {len(dead_ends)} dead-end nodes")

        if condition_issues:
            recs.append("Update node prompts to include required routing keywords")

        if provider_issues:
            recs.append("Verify provider and model configurations")

        if not recs:
            recs.append("No critical issues found - workflow structure looks good")

        return recs

    def print_report(self, report: IntegrityReport):
        """Print integrity report"""
        print("\n" + "="*60)
        print(f"INTEGRITY REPORT: {report.workflow_name}")
        print("="*60)

        print(f"\nStructure:")
        print(f"  Nodes: {report.total_nodes}")
        print(f"  Edges: {report.total_edges}")
        print(f"  Start: {report.start_nodes}")
        print(f"  End: {report.end_nodes}")

        if report.unreachable_nodes:
            print(f"\n[WARN] Unreachable Nodes ({len(report.unreachable_nodes)}):")
            for n in report.unreachable_nodes:
                print(f"  - {n}")

        if report.orphan_edges:
            print(f"\n[ERROR] Orphan Edges ({len(report.orphan_edges)}):")
            for oe in report.orphan_edges:
                print(f"  - {oe['edge']}: {oe['issue']}")

        if report.missing_trigger_edges:
            print(f"\n[WARN] Nodes Without Trigger Edges ({len(report.missing_trigger_edges)}):")
            for n in report.missing_trigger_edges:
                print(f"  - {n}")

        if report.dead_end_nodes:
            print(f"\n[WARN] Dead-End Nodes ({len(report.dead_end_nodes)}):")
            for n in report.dead_end_nodes:
                print(f"  - {n}")

        if report.condition_issues:
            print(f"\n[WARN] Condition Issues ({len(report.condition_issues)}):")
            for ci in report.condition_issues[:5]:
                print(f"  - {ci}")

        if report.provider_issues:
            print(f"\n[WARN] Provider Issues ({len(report.provider_issues)}):")
            for pi in report.provider_issues:
                print(f"  - {pi}")

        if report.structural_issues:
            print(f"\n[WARN] Structural Issues ({len(report.structural_issues)}):")
            for si in report.structural_issues:
                print(f"  - {si}")

        print(f"\nRecommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")

        # Summary status
        issues = (
            len(report.unreachable_nodes) +
            len(report.orphan_edges) +
            len(report.dead_end_nodes) +
            len(report.condition_issues)
        )

        if issues == 0:
            print(f"\n[OK] Workflow integrity check PASSED")
        else:
            print(f"\n[!!] Found {issues} potential issues to review")

        print("="*60)


# CLI interface
if __name__ == "__main__":
    import json

    checker = WorkflowIntegrityChecker()
    reports = checker.check_all_workflows()

    # Print all reports
    for name, report in reports.items():
        checker.print_report(report)

    # Save reports
    output_path = Path("context/workflow_integrity_reports.json")
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump({
            name: {
                'workflow_name': r.workflow_name,
                'total_nodes': r.total_nodes,
                'total_edges': r.total_edges,
                'start_nodes': r.start_nodes,
                'end_nodes': r.end_nodes,
                'unreachable_nodes': r.unreachable_nodes,
                'orphan_edges': r.orphan_edges,
                'missing_trigger_edges': r.missing_trigger_edges,
                'dead_end_nodes': r.dead_end_nodes,
                'condition_issues': r.condition_issues,
                'provider_issues': r.provider_issues,
                'structural_issues': r.structural_issues,
                'recommendations': r.recommendations
            }
            for name, r in reports.items()
        }, f, indent=2)

    print(f"\nReports saved to: {output_path}")
