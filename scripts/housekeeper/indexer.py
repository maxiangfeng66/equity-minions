"""
Indexer - Scans project and builds function/class index

Extracts all functions and classes from Python files,
generates embeddings, and stores them for similarity search.
"""

import ast
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Handle both direct execution and module import
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from scripts.housekeeper.config import (
        PROJECT_ROOT,
        INDEX_PATH,
        SCAN_DIRS,
        IGNORE_PATTERNS,
        IGNORE_FILES,
    )
    from scripts.housekeeper.embedder import generate_embeddings_batch, preload_model
except ImportError:
    from config import (
        PROJECT_ROOT,
        INDEX_PATH,
        SCAN_DIRS,
        IGNORE_PATTERNS,
        IGNORE_FILES,
    )
    from embedder import generate_embeddings_batch, preload_model


class CodeExtractor(ast.NodeVisitor):
    """AST visitor to extract functions and classes from Python files."""

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_lines = source_code.split('\n')
        self.functions = []
        self.classes = []

    def visit_FunctionDef(self, node):
        """Extract function definitions."""
        self._extract_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Extract async function definitions."""
        self._extract_function(node, is_async=True)
        self.generic_visit(node)

    def _extract_function(self, node, is_async=False):
        """Extract function info from AST node."""
        # Get function signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Get docstring if present
        docstring = ast.get_docstring(node) or ""

        # Get function body (first 20 lines for embedding)
        start_line = node.lineno - 1
        end_line = min(node.end_lineno or start_line + 20, start_line + 20)
        body_lines = self.source_lines[start_line:end_line]
        body = '\n'.join(body_lines)

        self.functions.append({
            "name": node.name,
            "file": self.file_path,
            "line": node.lineno,
            "signature": f"{'async ' if is_async else ''}def {node.name}({', '.join(args)})",
            "docstring": docstring[:200] if docstring else "",
            "body": body,
            "summary": f"{node.name}: {docstring[:100]}" if docstring else node.name,
        })

    def visit_ClassDef(self, node):
        """Extract class definitions."""
        # Get docstring
        docstring = ast.get_docstring(node) or ""

        # Get class body (first 30 lines for embedding)
        start_line = node.lineno - 1
        end_line = min(node.end_lineno or start_line + 30, start_line + 30)
        body_lines = self.source_lines[start_line:end_line]
        body = '\n'.join(body_lines)

        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        # Get method names
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        self.classes.append({
            "name": node.name,
            "file": self.file_path,
            "line": node.lineno,
            "bases": bases,
            "methods": methods[:10],  # First 10 methods
            "docstring": docstring[:200] if docstring else "",
            "body": body,
            "summary": f"{node.name}({', '.join(bases)}): {docstring[:100]}" if docstring else f"{node.name}({', '.join(bases)})",
        })

        self.generic_visit(node)


def should_ignore(path: Path) -> bool:
    """Check if a path should be ignored."""
    path_str = str(path)

    # Check ignore patterns
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*"):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True

    # Check ignore files
    for ignore in IGNORE_FILES:
        if ignore in path_str:
            return True

    return False


def extract_from_file(file_path: Path) -> tuple[List[Dict], List[Dict]]:
    """Extract functions and classes from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        # Get relative path from project root
        rel_path = str(file_path.relative_to(PROJECT_ROOT))

        extractor = CodeExtractor(rel_path, source_code)
        extractor.visit(tree)

        return extractor.functions, extractor.classes

    except SyntaxError as e:
        print(f"[Housekeeper] Syntax error in {file_path}: {e}")
        return [], []
    except Exception as e:
        print(f"[Housekeeper] Error extracting from {file_path}: {e}")
        return [], []


def scan_directory(directory: Path) -> tuple[List[Dict], List[Dict]]:
    """Scan a directory recursively for Python files."""
    all_functions = []
    all_classes = []

    if not directory.exists():
        return [], []

    for py_file in directory.rglob("*.py"):
        if should_ignore(py_file):
            continue

        functions, classes = extract_from_file(py_file)
        all_functions.extend(functions)
        all_classes.extend(classes)

    return all_functions, all_classes


def rebuild_index(verbose: bool = True) -> Dict[str, Any]:
    """
    Rebuild the complete function/class index.

    This scans all configured directories, extracts functions/classes,
    generates embeddings, and saves to the index file.
    """
    if verbose:
        print("[Housekeeper] Rebuilding index...")

    # Preload embedding model
    preload_model()

    all_functions = []
    all_classes = []

    # Scan all configured directories
    for dir_name in SCAN_DIRS:
        dir_path = PROJECT_ROOT / dir_name
        if verbose:
            print(f"  Scanning {dir_name}/...")

        functions, classes = scan_directory(dir_path)
        all_functions.extend(functions)
        all_classes.extend(classes)

    if verbose:
        print(f"  Found {len(all_functions)} functions, {len(all_classes)} classes")

    # Generate embeddings for all items
    if verbose:
        print("  Generating embeddings...")

    # Prepare texts for embedding (use body + summary for better semantic matching)
    function_texts = [f"{f['summary']}\n{f['body']}" for f in all_functions]
    class_texts = [f"{c['summary']}\n{c['body']}" for c in all_classes]

    # Batch generate embeddings
    function_embeddings = generate_embeddings_batch(function_texts)
    class_embeddings = generate_embeddings_batch(class_texts)

    # Add embeddings to items
    for func, embedding in zip(all_functions, function_embeddings):
        func["embedding"] = embedding
        # Remove body from stored data (too large)
        del func["body"]

    for cls, embedding in zip(all_classes, class_embeddings):
        cls["embedding"] = embedding
        del cls["body"]

    # Build index
    index = {
        "functions": all_functions,
        "classes": all_classes,
        "last_updated": datetime.now().isoformat(),
        "stats": {
            "total_functions": len(all_functions),
            "total_classes": len(all_classes),
        }
    }

    # Ensure .claude directory exists
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save index
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    if verbose:
        print(f"[Housekeeper] Index saved to {INDEX_PATH}")
        print(f"  {len(all_functions)} functions, {len(all_classes)} classes indexed")

    return index


def load_index() -> Optional[Dict[str, Any]]:
    """Load the existing index from disk."""
    if not INDEX_PATH.exists():
        return None

    try:
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Housekeeper] Error loading index: {e}")
        return None


def update_index(file_path: str, content: str = None) -> Dict[str, Any]:
    """
    Update the index with a new or modified file.

    This is more efficient than full rebuild for single file changes.
    """
    index = load_index()
    if index is None:
        return rebuild_index()

    # Get relative path
    try:
        rel_path = str(Path(file_path).relative_to(PROJECT_ROOT))
    except ValueError:
        rel_path = file_path

    # Remove old entries for this file
    index["functions"] = [f for f in index["functions"] if f["file"] != rel_path]
    index["classes"] = [c for c in index["classes"] if c["file"] != rel_path]

    # Extract new entries if file still exists
    full_path = PROJECT_ROOT / rel_path if not Path(file_path).is_absolute() else Path(file_path)

    if full_path.exists():
        functions, classes = extract_from_file(full_path)

        # Generate embeddings
        function_texts = [f"{f['summary']}\n{f['body']}" for f in functions]
        class_texts = [f"{c['summary']}\n{c['body']}" for c in classes]

        function_embeddings = generate_embeddings_batch(function_texts)
        class_embeddings = generate_embeddings_batch(class_texts)

        for func, embedding in zip(functions, function_embeddings):
            func["embedding"] = embedding
            del func["body"]
            index["functions"].append(func)

        for cls, embedding in zip(classes, class_embeddings):
            cls["embedding"] = embedding
            del cls["body"]
            index["classes"].append(cls)

    # Update metadata
    index["last_updated"] = datetime.now().isoformat()
    index["stats"] = {
        "total_functions": len(index["functions"]),
        "total_classes": len(index["classes"]),
    }

    # Save
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    return index


if __name__ == "__main__":
    # CLI: rebuild or update index
    import sys

    if "--rebuild" in sys.argv:
        rebuild_index(verbose=True)
    elif "--update" in sys.argv:
        # Get file path from next argument
        try:
            idx = sys.argv.index("--update")
            file_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
            if file_path:
                update_index(file_path)
                print(f"[Housekeeper] Updated index for {file_path}")
            else:
                print("Usage: python indexer.py --update <file_path>")
        except (ValueError, IndexError):
            print("Usage: python indexer.py --update <file_path>")
    else:
        print("Usage: python indexer.py --rebuild | --update <file_path>")
