"""
Housekeeper Main - Hook entry point for Claude Code

This is the script that runs as a PreToolUse hook.
It checks files before they are written for:
1. Duplicate/similar function names
2. Duplicate/similar class names
3. Wrong file locations
4. Deprecated imports
"""

import ast
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.housekeeper.config import (
    EMBEDDING_SIMILARITY_THRESHOLD,
    NAME_SIMILARITY_THRESHOLD,
    BLOCKED_FILENAME_PATTERNS,
    ALLOWED_ENTRY_POINTS,
    OVERRIDE_MARKER,
)
import fnmatch
from scripts.housekeeper.similarity import (
    find_similar_functions,
    find_similar_classes,
    find_exact_name_match,
    find_similar_files,
    check_deprecated_imports,
)
from scripts.housekeeper.llm_checker import (
    check_semantic_similarity,
    get_existing_code,
)
from scripts.housekeeper.indexer import load_index, rebuild_index


class CodeAnalyzer:
    """Analyzes code to extract functions and classes."""

    def __init__(self, code: str):
        self.code = code
        self.functions = []
        self.classes = []
        self._parse()

    def _parse(self):
        """Parse the code and extract functions/classes."""
        try:
            tree = ast.parse(self.code)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip methods inside classes (they'll be part of class)
                    self.functions.append({
                        "name": node.name,
                        "lineno": node.lineno,
                        "code": self._get_node_code(node),
                    })
                elif isinstance(node, ast.ClassDef):
                    self.classes.append({
                        "name": node.name,
                        "lineno": node.lineno,
                        "code": self._get_node_code(node),
                    })
        except SyntaxError:
            pass  # Invalid Python, skip parsing

    def _get_node_code(self, node) -> str:
        """Extract code for a specific AST node."""
        lines = self.code.split('\n')
        start = node.lineno - 1
        end = node.end_lineno if node.end_lineno else start + 20
        return '\n'.join(lines[start:end])


def check_blocked_filename(file_path: str) -> tuple[bool, str]:
    """
    Check if a filename matches blocked patterns.

    Only blocks files in the project root directory (not subdirectories).
    This prevents new entry points while allowing legitimate files like
    agents/run_helper.py or utils/server_utils.py.

    Args:
        file_path: Full path to the file

    Returns:
        Tuple of (should_block: bool, message: str)
    """
    path = Path(file_path)
    filename = path.name

    # Check if it's in the allowed whitelist
    if filename in ALLOWED_ENTRY_POINTS:
        return False, ""

    # Determine if this is a root-level file
    is_root_file = False
    try:
        relative = path.relative_to(PROJECT_ROOT)
        is_root_file = len(relative.parts) == 1
    except ValueError:
        pass

    # Check against blocked patterns (only for root-level files)
    if is_root_file:
        for pattern in BLOCKED_FILENAME_PATTERNS:
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                msg = [
                    "",
                    "=" * 60,
                    "HOUSEKEEPER BLOCK: Suspicious entry-point filename",
                    "=" * 60,
                    "",
                    f"You are creating: {filename}",
                    f"Matched pattern: {pattern}",
                    "",
                    "This filename pattern suggests a new entry point.",
                    "Per CLAUDE.md: 'main.py - Primary entry point for all workflows'",
                    "               'Avoid creating new run_*.py files'",
                    "",
                    "ALLOWED ENTRY POINTS:",
                ]
                for allowed in ALLOWED_ENTRY_POINTS:
                    msg.append(f"  - {allowed}")
                msg.extend([
                    "",
                    "ACTION REQUIRED:",
                    "  1. Use the existing main.py entry point, OR",
                    "  2. Get explicit user approval to create a new entry point",
                    "",
                    "=" * 60,
                ])
                return True, '\n'.join(msg)

    # Check for semantically similar existing files
    # This runs for ALL files, not just root
    similar_files = find_similar_files(filename, threshold=0.80)
    # Filter out exact same filename (we're creating/overwriting it)
    similar_files = [s for s in similar_files if s['similarity'] < 1.0]

    if similar_files:
        top_match = similar_files[0]

        # High similarity (>=90%) = BLOCK
        if top_match['similarity'] >= 0.90:
            msg = [
                "",
                "=" * 60,
                "HOUSEKEEPER BLOCK: Very similar filename exists",
                "=" * 60,
                "",
                f"You are creating: {filename}",
                "",
                "Existing similar files:",
            ]
            for sim in similar_files:
                msg.append(f"  - {sim['name']} ({sim['similarity']:.0%} similar)")
                msg.append(f"    Location: {sim['file']}")
            msg.extend([
                "",
                "ACTION REQUIRED:",
                "  1. Modify the existing file instead, OR",
                "  2. Get explicit user approval to create duplicate",
                "",
                "=" * 60,
            ])
            return True, '\n'.join(msg)

        # Moderate similarity (80-89%) = warning only (won't show in IDE)
        msg = [
            "",
            "-" * 60,
            "HOUSEKEEPER WARNING: Similar filename exists",
            "-" * 60,
            "",
            f"You are creating: {filename}",
            "",
            "Similar existing files:",
        ]
        for sim in similar_files:
            msg.append(f"  - {sim['name']} ({sim['similarity']:.0%} similar)")
            msg.append(f"    Location: {sim['file']}")
        msg.extend([
            "",
            "Consider: Is this file duplicating existing functionality?",
            "-" * 60,
        ])
        return False, '\n'.join(msg)

    return False, ""


def format_block_message(
    item_type: str,
    new_name: str,
    matches: List[Dict[str, Any]],
    verdict: str = None,
    explanation: str = None,
) -> str:
    """Format a block message for Claude to see."""
    msg = [
        "",
        "=" * 60,
        f"HOUSEKEEPER BLOCK: Similar {item_type} exists",
        "=" * 60,
        "",
        f"You are creating: {new_name}",
        "",
        "Existing similar code found:",
    ]

    for match in matches[:3]:  # Show top 3
        msg.append(f"  - {match['name']}")
        msg.append(f"    File: {match['file']}:{match['line']}")
        msg.append(f"    Similarity: {match['combined_score']:.0%} ({match['match_type']} match)")
        if match.get('signature'):
            msg.append(f"    Signature: {match['signature']}")
        msg.append("")

    if verdict:
        msg.append(f"LLM Verdict: {verdict}")
        if explanation:
            msg.append(f"Reason: {explanation}")
        msg.append("")

    msg.extend([
        "ACTION REQUIRED:",
        "  1. Modify the existing code instead of creating new, OR",
        "  2. Get explicit user approval to create duplicate",
        "",
        "=" * 60,
    ])

    return '\n'.join(msg)


def format_warning_message(warnings: List[str]) -> str:
    """Format a warning message."""
    msg = [
        "",
        "-" * 60,
        "HOUSEKEEPER WARNING:",
        "-" * 60,
    ]
    for warning in warnings:
        msg.append(f"  ! {warning}")
    msg.append("-" * 60)

    return '\n'.join(msg)


def check_file(file_path: str, content: str) -> tuple[bool, str]:
    """
    Check a file before it's written.

    Args:
        file_path: Path where file will be written
        content: Content to be written

    Returns:
        Tuple of (should_block: bool, message: str)
    """
    # Skip non-Python files
    if not file_path.endswith('.py'):
        return False, ""

    # Skip housekeeper's own files
    if 'housekeeper' in file_path:
        return False, ""

    # Check for override marker - if present, skip all checks
    if OVERRIDE_MARKER in content:
        return False, ""

    # Check for blocked filename patterns (entry points)
    filename_blocked, filename_msg = check_blocked_filename(file_path)
    if filename_blocked:
        return True, filename_msg

    warnings = []
    blocks = []

    # Check for deprecated imports
    deprecated = check_deprecated_imports(content)
    for old, new in deprecated:
        warnings.append(f"Deprecated import: '{old}' -> use '{new}'")

    # Parse the new code
    analyzer = CodeAnalyzer(content)

    # Check each function
    for func in analyzer.functions:
        # Skip private/dunder functions
        if func["name"].startswith('_'):
            continue

        # Check for exact name match first
        exact = find_exact_name_match(func["name"], "function")
        if exact:
            blocks.append({
                "type": "function",
                "new_name": func["name"],
                "matches": [{
                    "name": exact["name"],
                    "file": exact["file"],
                    "line": exact["line"],
                    "signature": exact.get("signature", ""),
                    "combined_score": 1.0,
                    "match_type": "exact",
                }],
            })
            continue

        # Check for similar functions
        similar = find_similar_functions(func["code"], func["name"])
        if similar:
            top_match = similar[0]

            # If embedding similarity is high, confirm with LLM
            if top_match["embedding_similarity"] >= EMBEDDING_SIMILARITY_THRESHOLD:
                existing_code = get_existing_code(
                    top_match["file"],
                    top_match["line"],
                    num_lines=30
                )

                verdict, explanation = check_semantic_similarity(
                    func["code"],
                    existing_code,
                    func["name"],
                    top_match["name"],
                )

                if verdict == "SAME":
                    blocks.append({
                        "type": "function",
                        "new_name": func["name"],
                        "matches": similar,
                        "verdict": verdict,
                        "explanation": explanation,
                    })
                elif verdict == "SIMILAR":
                    warnings.append(
                        f"Function '{func['name']}' is similar to "
                        f"'{top_match['name']}' in {top_match['file']}:{top_match['line']} "
                        f"- consider reusing or extending"
                    )

    # Check each class
    for cls in analyzer.classes:
        # Check for exact name match
        exact = find_exact_name_match(cls["name"], "class")
        if exact:
            blocks.append({
                "type": "class",
                "new_name": cls["name"],
                "matches": [{
                    "name": exact["name"],
                    "file": exact["file"],
                    "line": exact["line"],
                    "combined_score": 1.0,
                    "match_type": "exact",
                }],
            })
            continue

        # Check for similar classes
        similar = find_similar_classes(cls["code"], cls["name"])
        if similar:
            top_match = similar[0]

            if top_match["embedding_similarity"] >= EMBEDDING_SIMILARITY_THRESHOLD:
                existing_code = get_existing_code(
                    top_match["file"],
                    top_match["line"],
                    num_lines=50
                )

                verdict, explanation = check_semantic_similarity(
                    cls["code"],
                    existing_code,
                    cls["name"],
                    top_match["name"],
                )

                if verdict == "SAME":
                    blocks.append({
                        "type": "class",
                        "new_name": cls["name"],
                        "matches": similar,
                        "verdict": verdict,
                        "explanation": explanation,
                    })
                elif verdict == "SIMILAR":
                    warnings.append(
                        f"Class '{cls['name']}' is similar to "
                        f"'{top_match['name']}' in {top_match['file']}:{top_match['line']} "
                        f"- consider extending"
                    )

    # Build output message
    messages = []

    # Blocks first (these prevent the write)
    for block in blocks:
        messages.append(format_block_message(
            block["type"],
            block["new_name"],
            block["matches"],
            block.get("verdict"),
            block.get("explanation"),
        ))

    # Warnings (informational, don't block)
    if warnings:
        messages.append(format_warning_message(warnings))

    should_block = len(blocks) > 0

    return should_block, '\n'.join(messages)


def check_bash_command(command: str) -> tuple[bool, str]:
    """
    Check a bash command before it's executed.

    Currently checks for:
    - mkdir creating new package directories (need __init__.py)
    """
    warnings = []

    # Check for mkdir commands
    if 'mkdir' in command:
        # Check if it's creating a Python package directory
        for scan_dir in ['agents', 'utils', 'workflow', 'scripts']:
            if scan_dir in command:
                warnings.append(
                    f"Creating directory in {scan_dir}/ - "
                    f"remember to add __init__.py with proper exports"
                )
                break

    if warnings:
        return False, format_warning_message(warnings)

    return False, ""


def handle_claude_code_hook():
    """
    Handle Claude Code PreToolUse hook format.

    Claude Code passes tool input as JSON via stdin with format:
    {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/path/to/file.py",
            "content": "file content..."
        }
    }

    Response:
    - Exit code 0: Allow the operation
    - Exit code 2: Block the operation (message via stderr)
    """
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            # No input, allow by default
            sys.exit(0)

        data = json.loads(stdin_data)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        # Only check Write and Edit tools for Python files
        if tool_name not in ["Write", "Edit"]:
            sys.exit(0)

        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")

        # For Edit tool, we need the new_string as content
        if tool_name == "Edit":
            content = tool_input.get("new_string", "")

        # Skip non-Python files
        if not file_path.endswith('.py'):
            sys.exit(0)

        should_block, message = check_file(file_path, content)

        if should_block:
            # Exit code 2 = block, message to stderr
            print(message, file=sys.stderr)
            sys.exit(2)
        else:
            # Print warnings to stderr but don't block
            if message:
                print(message, file=sys.stderr)
            sys.exit(0)

    except json.JSONDecodeError:
        # Not JSON input, allow
        sys.exit(0)
    except Exception as e:
        # On error, allow but warn
        print(f"Housekeeper error: {str(e)}", file=sys.stderr)
        sys.exit(0)


def main():
    """CLI entry point for the housekeeper hook."""
    parser = argparse.ArgumentParser(description="Housekeeper - Code duplication checker")
    parser.add_argument("--check", help="Check a file before writing")
    parser.add_argument("--content", help="Content to be written (for --check)")
    parser.add_argument("--check-bash", help="Check a bash command")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild the function index")
    parser.add_argument("--hook", action="store_true", help="Run as Claude Code hook (reads JSON from stdin)")

    args = parser.parse_args()

    if args.rebuild_index:
        rebuild_index(verbose=True)
        return

    if args.hook:
        handle_claude_code_hook()
        return

    if args.check:
        # Read content from stdin if not provided
        content = args.content
        if not content:
            content = sys.stdin.read()

        should_block, message = check_file(args.check, content)

        if message:
            print(message)

        # Exit code 1 = block, 0 = allow
        sys.exit(1 if should_block else 0)

    if args.check_bash:
        should_block, message = check_bash_command(args.check_bash)

        if message:
            print(message)

        sys.exit(1 if should_block else 0)

    # No arguments - check if stdin has JSON (Claude Code hook mode)
    if not sys.stdin.isatty():
        handle_claude_code_hook()
        return

    # No arguments - print usage
    parser.print_help()


if __name__ == "__main__":
    main()
