"""
Semantic Housekeeper - Prevents code duplication through intelligent similarity detection.

Uses a hybrid approach:
1. Exact name matching (instant)
2. Embedding similarity with all-MiniLM-L6-v2 (fast, local)
3. LLM confirmation for semantic equivalence (accurate)
"""

from .main import check_file, check_bash_command
from .indexer import rebuild_index, update_index
from .similarity import find_similar_functions, find_similar_classes

__all__ = [
    'check_file',
    'check_bash_command',
    'rebuild_index',
    'update_index',
    'find_similar_functions',
    'find_similar_classes',
]
