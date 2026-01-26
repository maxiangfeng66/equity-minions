"""
Component Inspector Agent - Sub-agent for detailed component inspection.

Spawned by Chief Engineer to perform deep inspection of specific components.
Has tools to read files, check syntax, validate imports, and analyze code.
"""

import ast
import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..core.spawnable_agent import SpawnableAgent


@dataclass
class InspectionReport:
    """Detailed inspection report for a component"""
    component_name: str
    inspection_type: str
    inspected_at: datetime
    files_inspected: List[str]

    # Results
    syntax_valid: bool = True
    imports_valid: bool = True
    structure_valid: bool = True

    # Issues found
    syntax_errors: List[str] = field(default_factory=list)
    import_errors: List[str] = field(default_factory=list)
    structure_issues: List[str] = field(default_factory=list)
    code_smells: List[str] = field(default_factory=list)

    # Metrics
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    function_count: int = 0
    class_count: int = 0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'component_name': self.component_name,
            'inspection_type': self.inspection_type,
            'inspected_at': self.inspected_at.isoformat(),
            'files_inspected': self.files_inspected,
            'syntax_valid': self.syntax_valid,
            'imports_valid': self.imports_valid,
            'structure_valid': self.structure_valid,
            'syntax_errors': self.syntax_errors,
            'import_errors': self.import_errors,
            'structure_issues': self.structure_issues,
            'code_smells': self.code_smells,
            'metrics': {
                'total_lines': self.total_lines,
                'code_lines': self.code_lines,
                'comment_lines': self.comment_lines,
                'function_count': self.function_count,
                'class_count': self.class_count
            },
            'recommendations': self.recommendations
        }


class ComponentInspectorAgent(SpawnableAgent):
    """
    Component Inspector - Deep inspection sub-agent.

    Tools available:
    - read_file: Read and analyze file contents
    - check_syntax: Validate Python syntax
    - check_imports: Validate import statements
    - analyze_structure: Analyze code structure
    - find_patterns: Search for code patterns
    - measure_complexity: Estimate code complexity
    """

    def __init__(
        self,
        name: str,
        project_root: str,
        parent_agent: Optional[SpawnableAgent] = None
    ):
        super().__init__(
            name=name,
            role="Component Inspector",
            tier=1,
            parent=parent_agent
        )

        self.project_root = Path(project_root)
        self.inspection_results: List[InspectionReport] = []

    # ==================== TOOLS ====================

    async def tool_read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Tool: Read and return file contents with basic analysis.
        """
        full_path = self.project_root / file_path

        if not full_path.exists():
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }

        try:
            content = full_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            return {
                'success': True,
                'file_path': file_path,
                'content': content,
                'line_count': len(lines),
                'size_bytes': len(content),
                'is_python': file_path.endswith('.py'),
                'is_yaml': file_path.endswith(('.yaml', '.yml'))
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def tool_check_syntax(self, file_path: str) -> Dict[str, Any]:
        """
        Tool: Check Python file for syntax errors.
        """
        full_path = self.project_root / file_path

        if not full_path.exists():
            return {'success': False, 'error': 'File not found'}

        if not file_path.endswith('.py'):
            return {'success': True, 'message': 'Not a Python file'}

        try:
            content = full_path.read_text(encoding='utf-8')
            ast.parse(content)

            return {
                'success': True,
                'syntax_valid': True,
                'file_path': file_path
            }
        except SyntaxError as e:
            return {
                'success': True,
                'syntax_valid': False,
                'error': str(e),
                'line': e.lineno,
                'offset': e.offset,
                'text': e.text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def tool_check_imports(self, file_path: str) -> Dict[str, Any]:
        """
        Tool: Check imports in a Python file.
        """
        full_path = self.project_root / file_path

        if not full_path.exists() or not file_path.endswith('.py'):
            return {'success': False, 'error': 'Invalid file'}

        try:
            content = full_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            imports = []
            import_errors = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append({
                            'type': 'from',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname
                        })

            # Check for common problematic imports
            for imp in imports:
                module = imp.get('module', '')
                if module.startswith('.') and node.level > 2:
                    import_errors.append(f"Deep relative import: {module}")

            return {
                'success': True,
                'imports': imports,
                'import_count': len(imports),
                'errors': import_errors
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def tool_analyze_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Tool: Analyze code structure - classes, functions, complexity.
        """
        full_path = self.project_root / file_path

        if not full_path.exists() or not file_path.endswith('.py'):
            return {'success': False, 'error': 'Invalid file'}

        try:
            content = full_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            classes = []
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': methods,
                        'method_count': len(methods)
                    })
                elif isinstance(node, ast.FunctionDef):
                    # Check if it's a top-level function
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                        functions.append({
                            'name': node.name,
                            'line': node.lineno,
                            'args': [arg.arg for arg in node.args.args],
                            'is_async': isinstance(node, ast.AsyncFunctionDef)
                        })

            # Count lines
            lines = content.split('\n')
            total_lines = len(lines)
            code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))

            return {
                'success': True,
                'classes': classes,
                'functions': functions,
                'metrics': {
                    'total_lines': total_lines,
                    'code_lines': code_lines,
                    'comment_lines': comment_lines,
                    'class_count': len(classes),
                    'function_count': len(functions)
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def tool_find_patterns(
        self,
        file_path: str,
        patterns: List[str]
    ) -> Dict[str, Any]:
        """
        Tool: Search for code patterns in a file.
        """
        full_path = self.project_root / file_path

        if not full_path.exists():
            return {'success': False, 'error': 'File not found'}

        try:
            content = full_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            findings = {}

            for pattern in patterns:
                matches = []
                regex = re.compile(pattern, re.IGNORECASE)

                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.append({
                            'line_number': i,
                            'line_content': line.strip()[:100]
                        })

                findings[pattern] = {
                    'count': len(matches),
                    'matches': matches[:10]  # Limit to first 10
                }

            return {
                'success': True,
                'findings': findings
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def tool_detect_code_smells(self, file_path: str) -> Dict[str, Any]:
        """
        Tool: Detect common code smells and anti-patterns.
        """
        full_path = self.project_root / file_path

        if not full_path.exists() or not file_path.endswith('.py'):
            return {'success': False, 'error': 'Invalid file'}

        try:
            content = full_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            smells = []

            # Check for long functions
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end_line = getattr(node, 'end_lineno', node.lineno + 50)
                    func_length = end_line - node.lineno
                    if func_length > 50:
                        smells.append({
                            'type': 'long_function',
                            'name': node.name,
                            'line': node.lineno,
                            'length': func_length,
                            'recommendation': f'Consider breaking down {node.name} (>{func_length} lines)'
                        })

            # Check for TODO/FIXME comments
            for i, line in enumerate(lines, 1):
                if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
                    smells.append({
                        'type': 'todo_comment',
                        'line': i,
                        'content': line.strip()[:80],
                        'recommendation': 'Address or create issue for TODO/FIXME'
                    })

            # Check for bare except
            if 'except:' in content:
                smells.append({
                    'type': 'bare_except',
                    'recommendation': 'Avoid bare except clauses - specify exception types'
                })

            # Check for long lines
            long_lines = [(i, len(line)) for i, line in enumerate(lines, 1) if len(line) > 120]
            if long_lines:
                smells.append({
                    'type': 'long_lines',
                    'count': len(long_lines),
                    'examples': long_lines[:5],
                    'recommendation': 'Keep lines under 120 characters'
                })

            # Check for magic numbers
            magic_number_pattern = re.compile(r'(?<![a-zA-Z_])\d{2,}(?![a-zA-Z_\d.])')
            magic_numbers = []
            for i, line in enumerate(lines, 1):
                if not line.strip().startswith('#'):
                    matches = magic_number_pattern.findall(line)
                    if matches:
                        magic_numbers.append((i, matches))
            if magic_numbers:
                smells.append({
                    'type': 'magic_numbers',
                    'count': len(magic_numbers),
                    'recommendation': 'Consider using named constants for magic numbers'
                })

            return {
                'success': True,
                'code_smells': smells,
                'smell_count': len(smells)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== INSPECTION METHODS ====================

    async def inspect_component(
        self,
        component_name: str,
        file_paths: List[str],
        deep_inspection: bool = False
    ) -> InspectionReport:
        """
        Perform full inspection of a component.
        """
        report = InspectionReport(
            component_name=component_name,
            inspection_type='deep' if deep_inspection else 'standard',
            inspected_at=datetime.now(),
            files_inspected=file_paths
        )

        for file_path in file_paths:
            # Check syntax
            syntax_result = await self.tool_check_syntax(file_path)
            if syntax_result.get('success') and not syntax_result.get('syntax_valid', True):
                report.syntax_valid = False
                report.syntax_errors.append(
                    f"{file_path}: {syntax_result.get('error')}"
                )

            # Check imports
            import_result = await self.tool_check_imports(file_path)
            if import_result.get('success'):
                errors = import_result.get('errors', [])
                if errors:
                    report.imports_valid = False
                    report.import_errors.extend(
                        f"{file_path}: {err}" for err in errors
                    )

            # Analyze structure
            structure_result = await self.tool_analyze_structure(file_path)
            if structure_result.get('success'):
                metrics = structure_result.get('metrics', {})
                report.total_lines += metrics.get('total_lines', 0)
                report.code_lines += metrics.get('code_lines', 0)
                report.comment_lines += metrics.get('comment_lines', 0)
                report.function_count += metrics.get('function_count', 0)
                report.class_count += metrics.get('class_count', 0)

            # Deep inspection: code smells
            if deep_inspection:
                smell_result = await self.tool_detect_code_smells(file_path)
                if smell_result.get('success'):
                    smells = smell_result.get('code_smells', [])
                    for smell in smells:
                        report.code_smells.append(
                            f"{file_path}: {smell.get('type')} - {smell.get('recommendation', '')}"
                        )

        # Generate recommendations
        if report.syntax_errors:
            report.recommendations.append("Fix syntax errors before deployment")
        if report.import_errors:
            report.recommendations.append("Review and fix import issues")
        if report.code_smells:
            report.recommendations.append("Address code smells for maintainability")
        if report.code_lines > 0:
            comment_ratio = report.comment_lines / report.code_lines
            if comment_ratio < 0.05:
                report.recommendations.append("Consider adding more documentation")

        self.inspection_results.append(report)
        return report

    async def quick_health_check(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Quick health check - just syntax and basic structure.
        """
        results = {
            'healthy': True,
            'files_checked': len(file_paths),
            'errors': []
        }

        for file_path in file_paths:
            syntax_result = await self.tool_check_syntax(file_path)
            if syntax_result.get('success') and not syntax_result.get('syntax_valid', True):
                results['healthy'] = False
                results['errors'].append({
                    'file': file_path,
                    'error': syntax_result.get('error')
                })

        return results
