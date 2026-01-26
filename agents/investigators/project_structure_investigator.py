#!/usr/bin/env python3
"""
Project Structure Investigator

A project-level agent that understands the entire project structure
and can identify orphaned code, missing connections, and architectural issues.
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field


@dataclass
class FileInfo:
    """Information about a Python file"""
    path: str
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    is_entry_point: bool = False
    is_imported_by: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


@dataclass
class InvestigationReport:
    """Report from project investigation"""
    total_files: int
    entry_points: List[str]
    orphaned_files: List[str]
    missing_imports: List[Dict[str, str]]
    circular_dependencies: List[List[str]]
    unused_agents: List[str]
    workflow_issues: List[str]
    recommendations: List[str]


class ProjectStructureInvestigator:
    """
    Investigates the entire project structure to identify issues.

    Responsibilities:
    1. Map all Python files and their dependencies
    2. Identify orphaned code that's never imported
    3. Find missing imports that would cause runtime errors
    4. Detect circular dependencies
    5. Identify agents defined but never used in workflows
    6. Check workflow YAML files for undefined agents
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.files: Dict[str, FileInfo] = {}
        self.import_graph: Dict[str, Set[str]] = {}

    def investigate(self) -> InvestigationReport:
        """Run full project investigation"""
        print("="*60)
        print("PROJECT STRUCTURE INVESTIGATION")
        print("="*60)

        # Step 1: Scan all Python files
        print("\n[1/6] Scanning Python files...")
        self._scan_python_files()

        # Step 2: Build import graph
        print("[2/6] Building import graph...")
        self._build_import_graph()

        # Step 3: Find entry points
        print("[3/6] Identifying entry points...")
        entry_points = self._find_entry_points()

        # Step 4: Find orphaned files
        print("[4/6] Finding orphaned files...")
        orphaned = self._find_orphaned_files(entry_points)

        # Step 5: Check for missing imports
        print("[5/6] Checking for missing imports...")
        missing = self._check_missing_imports()

        # Step 6: Analyze workflows
        print("[6/6] Analyzing workflow definitions...")
        workflow_issues = self._analyze_workflows()

        # Generate report
        report = InvestigationReport(
            total_files=len(self.files),
            entry_points=entry_points,
            orphaned_files=orphaned,
            missing_imports=missing,
            circular_dependencies=self._find_circular_deps(),
            unused_agents=self._find_unused_agents(),
            workflow_issues=workflow_issues,
            recommendations=self._generate_recommendations()
        )

        self._print_report(report)
        return report

    def _scan_python_files(self):
        """Scan all Python files in project"""
        exclude_dirs = {'.venv', 'venv', '__pycache__', '.git', 'chatdev_reference', '_archive'}

        for py_file in self.project_root.rglob("*.py"):
            # Skip excluded directories
            if any(ex in py_file.parts for ex in exclude_dirs):
                continue

            rel_path = str(py_file.relative_to(self.project_root))

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                info = FileInfo(path=rel_path)

                # Extract imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            info.imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            info.imports.append(node.module)
                    elif isinstance(node, ast.ClassDef):
                        info.classes.append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        if node.name != '__init__':
                            info.functions.append(node.name)

                # Check if entry point
                if 'if __name__ ==' in content or 'argparse' in content:
                    info.is_entry_point = True

                self.files[rel_path] = info

            except SyntaxError as e:
                self.files[rel_path] = FileInfo(
                    path=rel_path,
                    issues=[f"Syntax error: {e}"]
                )
            except Exception as e:
                self.files[rel_path] = FileInfo(
                    path=rel_path,
                    issues=[f"Parse error: {e}"]
                )

        print(f"  Scanned {len(self.files)} Python files")

    def _build_import_graph(self):
        """Build graph of imports between project files"""
        for file_path, info in self.files.items():
            self.import_graph[file_path] = set()

            for imp in info.imports:
                # Convert import to potential file path
                potential_paths = [
                    imp.replace('.', '/') + '.py',
                    imp.replace('.', '/') + '/__init__.py',
                ]

                for pot_path in potential_paths:
                    if pot_path in self.files:
                        self.import_graph[file_path].add(pot_path)
                        self.files[pot_path].is_imported_by.append(file_path)

    def _find_entry_points(self) -> List[str]:
        """Find all entry point files"""
        entry_points = []

        # Known entry points
        known_entries = [
            'main.py', 'scheduler.py', 'run_workflow_live.py',
            'run_portfolio_live.py', 'run_debates.py', 'run_validation.py',
            'run_monitoring.py'
        ]

        for file_path, info in self.files.items():
            if info.is_entry_point or Path(file_path).name in known_entries:
                entry_points.append(file_path)

        return entry_points

    def _find_orphaned_files(self, entry_points: List[str]) -> List[str]:
        """Find files that are never imported from entry points"""
        # BFS from entry points
        reachable = set(entry_points)
        queue = list(entry_points)

        while queue:
            current = queue.pop(0)
            for imported in self.import_graph.get(current, set()):
                if imported not in reachable:
                    reachable.add(imported)
                    queue.append(imported)

        # Find orphaned
        orphaned = []
        for file_path in self.files:
            if file_path not in reachable:
                # Exclude __init__.py files
                if not file_path.endswith('__init__.py'):
                    orphaned.append(file_path)

        return orphaned

    def _check_missing_imports(self) -> List[Dict[str, str]]:
        """Check for imports that would fail"""
        missing = []

        for file_path, info in self.files.items():
            for imp in info.imports:
                # Check if it's a project import that doesn't exist
                if imp.startswith('agents') or imp.startswith('workflow') or imp.startswith('utils'):
                    pot_path = imp.replace('.', '/') + '.py'
                    pot_init = imp.replace('.', '/') + '/__init__.py'

                    if pot_path not in self.files and pot_init not in self.files:
                        # Check if it's a submodule
                        parts = imp.split('.')
                        found = False
                        for i in range(len(parts)):
                            check_path = '/'.join(parts[:i+1]) + '.py'
                            if check_path in self.files:
                                found = True
                                break

                        if not found:
                            missing.append({
                                'file': file_path,
                                'missing_import': imp
                            })

        return missing

    def _find_circular_deps(self) -> List[List[str]]:
        """Find circular dependencies"""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.import_graph.get(node, set()):
                if neighbor not in visited:
                    result = dfs(neighbor, path.copy())
                    if result:
                        cycles.append(result)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(node)
            return None

        for node in self.files:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _find_unused_agents(self) -> List[str]:
        """Find agent classes that aren't used in workflows"""
        # Collect all agent classes
        agent_classes = []
        for file_path, info in self.files.items():
            if 'agent' in file_path.lower():
                for cls in info.classes:
                    if 'Agent' in cls or 'Advocate' in cls or 'Critic' in cls:
                        agent_classes.append(cls)

        # Check workflow YAML files for agent usage
        used_in_workflows = set()
        workflows_dir = self.project_root / 'workflows'

        if workflows_dir.exists():
            for yaml_file in workflows_dir.glob('*.yaml'):
                try:
                    content = yaml_file.read_text()
                    for cls in agent_classes:
                        if cls.lower().replace('agent', '').replace('_', ' ') in content.lower():
                            used_in_workflows.add(cls)
                except:
                    pass

        # Find unused
        unused = [cls for cls in agent_classes if cls not in used_in_workflows]
        return unused

    def _analyze_workflows(self) -> List[str]:
        """Analyze workflow YAML files for issues"""
        issues = []
        workflows_dir = self.project_root / 'workflow' / 'definitions'

        if not workflows_dir.exists():
            issues.append("workflow/definitions/ directory not found")
            return issues

        import yaml

        for yaml_file in workflows_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)

                graph = config.get('graph', {})
                nodes = {n['id'] for n in graph.get('nodes', [])}
                edges = graph.get('edges', [])

                # Check edges reference valid nodes
                for edge in edges:
                    if edge.get('from') not in nodes:
                        issues.append(f"{yaml_file.name}: Edge from unknown node '{edge.get('from')}'")
                    if edge.get('to') not in nodes:
                        issues.append(f"{yaml_file.name}: Edge to unknown node '{edge.get('to')}'")

                # Check for unreachable nodes
                start_nodes = set(graph.get('start', []))
                reachable = set(start_nodes)

                changed = True
                while changed:
                    changed = False
                    for edge in edges:
                        if edge.get('from') in reachable and edge.get('to') not in reachable:
                            reachable.add(edge.get('to'))
                            changed = True

                unreachable = nodes - reachable
                if unreachable:
                    issues.append(f"{yaml_file.name}: Unreachable nodes: {unreachable}")

            except Exception as e:
                issues.append(f"{yaml_file.name}: Parse error - {e}")

        return issues

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations"""
        recs = []

        # Based on findings
        if self._find_orphaned_files([]):
            recs.append("Review orphaned files - either integrate or remove them")

        if self._check_missing_imports():
            recs.append("Fix missing imports before running workflows")

        if self._find_circular_deps():
            recs.append("Resolve circular dependencies to prevent import errors")

        # General recommendations
        recs.extend([
            "Always use equity_research_v4.yaml (not v3) for complete quality gates",
            "Always prefetch prices with prefetch_data.py before running workflows",
            "Verify Market Data Collector actually executes web searches",
            "Test each workflow node individually before full pipeline"
        ])

        return recs

    def _print_report(self, report: InvestigationReport):
        """Print investigation report"""
        print("\n" + "="*60)
        print("INVESTIGATION REPORT")
        print("="*60)

        print(f"\nTotal Python files: {report.total_files}")

        print(f"\nEntry Points ({len(report.entry_points)}):")
        for ep in report.entry_points:
            print(f"  - {ep}")

        if report.orphaned_files:
            print(f"\nOrphaned Files ({len(report.orphaned_files)}):")
            for of in report.orphaned_files[:10]:
                print(f"  - {of}")
            if len(report.orphaned_files) > 10:
                print(f"  ... and {len(report.orphaned_files) - 10} more")

        if report.missing_imports:
            print(f"\nMissing Imports ({len(report.missing_imports)}):")
            for mi in report.missing_imports[:5]:
                print(f"  - {mi['file']}: cannot import '{mi['missing_import']}'")

        if report.circular_dependencies:
            print(f"\nCircular Dependencies ({len(report.circular_dependencies)}):")
            for cd in report.circular_dependencies[:3]:
                print(f"  - {' -> '.join(cd)}")

        if report.workflow_issues:
            print(f"\nWorkflow Issues ({len(report.workflow_issues)}):")
            for wi in report.workflow_issues:
                print(f"  - {wi}")

        print(f"\nRecommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")

        print("\n" + "="*60)


# CLI interface
if __name__ == "__main__":
    investigator = ProjectStructureInvestigator()
    report = investigator.investigate()

    # Save report as JSON
    report_path = Path("context/investigation_report.json")
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump({
            'total_files': report.total_files,
            'entry_points': report.entry_points,
            'orphaned_files': report.orphaned_files,
            'missing_imports': report.missing_imports,
            'circular_dependencies': report.circular_dependencies,
            'unused_agents': report.unused_agents,
            'workflow_issues': report.workflow_issues,
            'recommendations': report.recommendations
        }, f, indent=2)

    print(f"\nReport saved to: {report_path}")
