"""
Similarity - Finds similar functions/classes in the codebase

Uses embedding similarity and fuzzy name matching.
"""

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Handle both direct execution and module import
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from scripts.housekeeper.config import (
        NAME_SIMILARITY_THRESHOLD,
        EMBEDDING_SIMILARITY_THRESHOLD,
    )
    from scripts.housekeeper.embedder import generate_embedding, cosine_similarity
    from scripts.housekeeper.indexer import load_index
except ImportError:
    from config import (
        NAME_SIMILARITY_THRESHOLD,
        EMBEDDING_SIMILARITY_THRESHOLD,
    )
    from embedder import generate_embedding, cosine_similarity
    from indexer import load_index


def normalize_name(name: str) -> str:
    """
    Normalize a function/class name for comparison.

    Converts camelCase and PascalCase to snake_case,
    removes common prefixes/suffixes.
    """
    # Convert camelCase/PascalCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    normalized = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    # Remove common prefixes/suffixes that don't change meaning
    prefixes = ['get_', 'set_', 'is_', 'has_', 'do_', 'run_', 'execute_', 'perform_']
    suffixes = ['_agent', '_handler', '_manager', '_service', '_helper', '_util']

    for prefix in prefixes:
        if normalized.startswith(prefix) and len(normalized) > len(prefix):
            normalized = normalized[len(prefix):]

    for suffix in suffixes:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            normalized = normalized[:-len(suffix)]

    return normalized


def name_similarity(name1: str, name2: str) -> float:
    """
    Calculate name similarity using normalized forms.

    Returns a score between 0 and 1.
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Exact match after normalization
    if norm1 == norm2:
        return 1.0

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_similar_functions(
    new_code: str,
    new_name: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Find functions similar to the new code.

    Args:
        new_code: The new function code
        new_name: The new function name
        top_k: Number of top matches to return

    Returns:
        List of similar functions with similarity scores
    """
    index = load_index()
    if not index or not index.get("functions"):
        return []

    # Generate embedding for new code
    new_embedding = generate_embedding(f"{new_name}\n{new_code}")

    results = []

    for func in index["functions"]:
        # Calculate name similarity
        name_sim = name_similarity(new_name, func["name"])

        # Calculate embedding similarity
        embedding_sim = 0.0
        if new_embedding and func.get("embedding"):
            embedding_sim = cosine_similarity(new_embedding, func["embedding"])

        # Combined score (weighted average)
        # Name matching is fast confirmation, embedding is semantic
        combined_score = (name_sim * 0.3) + (embedding_sim * 0.7)

        # Check if above any threshold
        if name_sim >= NAME_SIMILARITY_THRESHOLD or embedding_sim >= EMBEDDING_SIMILARITY_THRESHOLD:
            results.append({
                "name": func["name"],
                "file": func["file"],
                "line": func["line"],
                "signature": func["signature"],
                "docstring": func.get("docstring", ""),
                "name_similarity": round(name_sim, 3),
                "embedding_similarity": round(embedding_sim, 3),
                "combined_score": round(combined_score, 3),
                "match_type": "name" if name_sim >= NAME_SIMILARITY_THRESHOLD else "semantic",
            })

    # Sort by combined score
    results.sort(key=lambda x: x["combined_score"], reverse=True)

    return results[:top_k]


def find_similar_classes(
    new_code: str,
    new_name: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Find classes similar to the new code.

    Args:
        new_code: The new class code
        new_name: The new class name
        top_k: Number of top matches to return

    Returns:
        List of similar classes with similarity scores
    """
    index = load_index()
    if not index or not index.get("classes"):
        return []

    # Generate embedding for new code
    new_embedding = generate_embedding(f"{new_name}\n{new_code}")

    results = []

    for cls in index["classes"]:
        # Calculate name similarity
        name_sim = name_similarity(new_name, cls["name"])

        # Calculate embedding similarity
        embedding_sim = 0.0
        if new_embedding and cls.get("embedding"):
            embedding_sim = cosine_similarity(new_embedding, cls["embedding"])

        # Combined score
        combined_score = (name_sim * 0.3) + (embedding_sim * 0.7)

        # Check if above any threshold
        if name_sim >= NAME_SIMILARITY_THRESHOLD or embedding_sim >= EMBEDDING_SIMILARITY_THRESHOLD:
            results.append({
                "name": cls["name"],
                "file": cls["file"],
                "line": cls["line"],
                "bases": cls.get("bases", []),
                "methods": cls.get("methods", []),
                "docstring": cls.get("docstring", ""),
                "name_similarity": round(name_sim, 3),
                "embedding_similarity": round(embedding_sim, 3),
                "combined_score": round(combined_score, 3),
                "match_type": "name" if name_sim >= NAME_SIMILARITY_THRESHOLD else "semantic",
            })

    # Sort by combined score
    results.sort(key=lambda x: x["combined_score"], reverse=True)

    return results[:top_k]


def find_exact_name_match(name: str, item_type: str = "function") -> Optional[Dict[str, Any]]:
    """
    Find an exact name match in the index.

    Args:
        name: The name to search for
        item_type: "function" or "class"

    Returns:
        The matching item or None
    """
    index = load_index()
    if not index:
        return None

    items = index.get("functions" if item_type == "function" else "classes", [])

    for item in items:
        if item["name"] == name:
            return item

    return None


def check_location_violation(file_path: str, item_type: str) -> Optional[str]:
    """
    Check if a file is being created in the wrong location.

    Args:
        file_path: Path to the new file
        item_type: Type of item being created (agent, validator, util, etc.)

    Returns:
        Suggested correct location, or None if location is valid
    """
    try:
        from scripts.housekeeper.config import LOCATION_RULES
    except ImportError:
        from config import LOCATION_RULES

    if item_type not in LOCATION_RULES:
        return None

    allowed_paths = LOCATION_RULES[item_type]
    file_path_normalized = file_path.replace("\\", "/")

    for allowed in allowed_paths:
        if allowed in file_path_normalized:
            return None

    # Location violation - suggest first allowed path
    return allowed_paths[0]


def find_similar_files(
    new_filename: str,
    threshold: float = 0.75,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Find existing files with semantically similar names.

    Args:
        new_filename: The new filename (without path)
        threshold: Minimum similarity score to include
        top_k: Number of top matches to return

    Returns:
        List of similar files with similarity scores
    """
    # Remove .py extension for comparison
    new_name = new_filename.replace('.py', '')

    index = load_index()
    if not index:
        return []

    # Collect unique files from index
    seen_files = set()
    existing_files = []

    for func in index.get("functions", []):
        filepath = func.get("file", "")
        if filepath and filepath not in seen_files:
            seen_files.add(filepath)
            filename = Path(filepath).stem  # filename without extension
            existing_files.append({"file": filepath, "name": filename})

    for cls in index.get("classes", []):
        filepath = cls.get("file", "")
        if filepath and filepath not in seen_files:
            seen_files.add(filepath)
            filename = Path(filepath).stem
            existing_files.append({"file": filepath, "name": filename})

    results = []

    for existing in existing_files:
        # Calculate name similarity
        sim = name_similarity(new_name, existing["name"])

        if sim >= threshold:
            results.append({
                "file": existing["file"],
                "name": existing["name"] + ".py",
                "similarity": round(sim, 3),
            })

    # Sort by similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)

    return results[:top_k]


def check_deprecated_imports(code: str) -> List[Tuple[str, str]]:
    """
    Check for imports from deprecated modules.

    Args:
        code: The source code to check

    Returns:
        List of (deprecated_import, suggested_replacement) tuples
    """
    try:
        from scripts.housekeeper.config import DEPRECATED_IMPORTS
    except ImportError:
        from config import DEPRECATED_IMPORTS

    violations = []

    for deprecated, replacement in DEPRECATED_IMPORTS.items():
        # Check various import patterns
        patterns = [
            f"from {deprecated} import",
            f"import {deprecated}",
            f"from {deprecated.replace('.', '/')}",
        ]

        for pattern in patterns:
            if pattern in code:
                violations.append((deprecated, replacement))
                break

    return violations
