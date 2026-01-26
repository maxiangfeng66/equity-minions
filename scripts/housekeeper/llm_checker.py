"""
LLM Checker - Uses AI providers for semantic similarity confirmation

Calls the existing ai_providers to determine if two code pieces
are semantically equivalent.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
_SCRIPT_DIR = Path(__file__).parent

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.housekeeper.config import LLM_COMPARISON_PROMPT, LLM_SYSTEM_PROMPT
except ImportError:
    from config import LLM_COMPARISON_PROMPT, LLM_SYSTEM_PROMPT


def get_ai_provider_manager():
    """Get the AI provider manager from the project."""
    try:
        from config import API_KEYS
        from agents.ai_providers import AIProviderManager

        return AIProviderManager(API_KEYS)
    except ImportError as e:
        print(f"[Housekeeper] Could not import AI providers: {e}")
        return None


async def check_semantic_similarity_async(
    new_code: str,
    existing_code: str,
    new_name: str,
    existing_name: str,
) -> Tuple[str, str]:
    """
    Use LLM to check if two code pieces are semantically equivalent.

    Args:
        new_code: The new function/class code
        existing_code: The existing function/class code
        new_name: Name of the new code
        existing_name: Name of the existing code

    Returns:
        Tuple of (verdict: "SAME"|"SIMILAR"|"DIFFERENT", explanation: str)
    """
    manager = get_ai_provider_manager()
    if not manager:
        return "UNKNOWN", "Could not load AI providers"

    # Prepare the prompt
    prompt = LLM_COMPARISON_PROMPT.format(
        new_code=new_code[:2000],  # Limit code length
        existing_code=existing_code[:2000],
    )

    try:
        response = await manager.generate_with_fallback(prompt, LLM_SYSTEM_PROMPT)

        # Parse response
        lines = response.strip().split('\n')
        verdict = lines[0].strip().upper()

        # Normalize verdict
        if "SAME" in verdict:
            verdict = "SAME"
        elif "SIMILAR" in verdict:
            verdict = "SIMILAR"
        else:
            verdict = "DIFFERENT"

        explanation = lines[1].strip() if len(lines) > 1 else ""

        return verdict, explanation

    except Exception as e:
        print(f"[Housekeeper] LLM check failed: {e}")
        return "UNKNOWN", str(e)


def check_semantic_similarity(
    new_code: str,
    existing_code: str,
    new_name: str = "",
    existing_name: str = "",
) -> Tuple[str, str]:
    """
    Synchronous wrapper for semantic similarity check.

    Returns:
        Tuple of (verdict: "SAME"|"SIMILAR"|"DIFFERENT"|"UNKNOWN", explanation: str)
    """
    try:
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                check_semantic_similarity_async(
                    new_code, existing_code, new_name, existing_name
                )
            )
        finally:
            loop.close()
    except Exception as e:
        return "UNKNOWN", str(e)


def get_existing_code(file_path: str, line_number: int, num_lines: int = 30) -> str:
    """
    Read existing code from a file.

    Args:
        file_path: Path to the file (relative to project root)
        line_number: Starting line number
        num_lines: Number of lines to read

    Returns:
        The code snippet
    """
    full_path = PROJECT_ROOT / file_path

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start = max(0, line_number - 1)
        end = min(len(lines), start + num_lines)

        return ''.join(lines[start:end])
    except Exception as e:
        print(f"[Housekeeper] Could not read {file_path}: {e}")
        return ""


if __name__ == "__main__":
    # Test the LLM checker
    code1 = """
def validate_dcf(cashflows, discount_rate):
    '''Validate DCF calculation inputs'''
    if not cashflows:
        return False
    if discount_rate <= 0:
        return False
    return True
"""

    code2 = """
def check_cashflow_validity(flows, rate):
    '''Check if cashflow data is valid for DCF'''
    if len(flows) == 0:
        return False
    if rate < 0:
        return False
    return True
"""

    verdict, explanation = check_semantic_similarity(code1, code2)
    print(f"Verdict: {verdict}")
    print(f"Explanation: {explanation}")
