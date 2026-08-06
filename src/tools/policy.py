from typing import Dict, Any
from src.utils.loader import get_data_loader


def search_policy(query: str) -> Dict[str, Any]:
    """
    Retrieves official Trendly shipping, return, refund, and exchange policy context.
    Currently returns the full policy document; `query` is accepted for future
    keyword-scoped lookups but the document is short enough to return whole today.
    """
    loader = get_data_loader()
    return {
        "found": True,
        "query": query,
        "policy_content": loader.get_policy_text()
    }