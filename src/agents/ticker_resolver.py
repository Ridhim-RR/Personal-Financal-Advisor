"""Ticker Resolver Agent — resolves company names to ticker symbols.

This agent NEVER generates ticker symbols using the LLM.
It uses a multi-step resolution pipeline:

1. Explicit tickers from user input (pass-through)
2. Fuzzy matching against company_tickers.json knowledge base
3. ChromaDB RAG retrieval (semantic search)
4. LLM-based disambiguation (only if multiple candidates, tells LLM to pick from existing data)

The agent stores resolved tickers in state["data"]["tickers"].
"""

import json
import os
import difflib
from typing import Optional

from langsmith import traceable

from src.graph.state import AgentState
from src.utils.chroma_client import get_chroma_client


# ── Knowledge Base ─────────────────────────────────────────

def _load_knowledge_base() -> list[dict]:
    """Load the company→ticker knowledge base from JSON."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "company_tickers.json")
    if not os.path.exists(path):
        print(f"  [TICKER_RESOLVER] WARNING: knowledge base not found at {path}")
        return []
    with open(path) as f:
        return json.load(f)


def _normalize(name: str) -> str:
    """Normalize a company name for fuzzy matching."""
    return name.strip().lower().replace("  ", " ")


def _get_all_name_variants(entry: dict) -> list[str]:
    """Get all name variants for an entry (company name + aliases)."""
    variants = [entry["company"]]
    variants.extend(entry.get("aliases", []))
    return variants


def _fuzzy_match(company_name: str, kb: list[dict], cutoff: float = 0.6) -> Optional[dict]:
    """Fuzzy match a company name against the knowledge base.

    Tries exact match first, then fuzzy match against all name variants.
    Returns the best matching entry or None.
    """
    normalized = _normalize(company_name)

    # 1. Exact match against company name or aliases
    for entry in kb:
        for variant in _get_all_name_variants(entry):
            if _normalize(variant) == normalized:
                return entry

    # 2. Fuzzy match
    all_variants = []
    variant_to_entry = []
    for entry in kb:
        for variant in _get_all_name_variants(entry):
            all_variants.append(_normalize(variant))
            variant_to_entry.append(entry)

    matches = difflib.get_close_matches(normalized, all_variants, n=1, cutoff=cutoff)
    if matches:
        idx = all_variants.index(matches[0])
        return variant_to_entry[idx]

    return None


def _chromadb_search(company_name: str) -> list[dict]:
    """Search ChromaDB company_tickers collection for semantically similar companies."""
    try:
        client = get_chroma_client()
        collection = client.get_collection("company_tickers")
        results = collection.query(
            query_texts=[company_name],
            n_results=3,
        )
        if results and results["metadatas"] and results["metadatas"][0]:
            return results["metadatas"][0]
    except Exception as e:
        print(f"  [TICKER_RESOLVER] ChromaDB search failed: {e}")
    return []


# ── Main Resolver ──────────────────────────────────────────

@traceable(name="ticker_resolver", run_type="chain")
def ticker_resolver_agent(state: AgentState) -> AgentState:
    """Resolve company names to ticker symbols.

    Pipeline:
      1. Pass through explicit tickers from user input.
      2. Fuzzy match each company name against knowledge base.
      3. ChromaDB RAG fallback.
      4. LLM disambiguation (only if multiple candidates, constrained to existing data).
      5. Validate tickers and store in state.
    """
    print(f"\n{'='*60}")
    print(f"▶ Running: Ticker Resolver")
    print(f"{'='*60}")

    company_names = state.get("company_names", [])
    explicit_tickers = state.get("explicit_tickers", [])
    question = state.get("question", "")

    print(f"   Company names: {company_names}")
    print(f"   Explicit tickers: {explicit_tickers}")

    resolved: dict[str, str] = {}
    errors: list[str] = []

    # 1. Pass through explicit tickers
    for ticker in explicit_tickers:
        cleaned = ticker.strip().upper().rstrip(".,!?:;")
        resolved[cleaned] = cleaned
        print(f"   Explicit ticker: {cleaned} → {cleaned}")

    # 2. Load knowledge base
    kb = _load_knowledge_base()
    print(f"   Knowledge base loaded: {len(kb)} entries")

    # 3. Resolve each company name
    for company in company_names:
        if company in resolved.values():
            continue  # already resolved from explicit_tickers

        # 3a. Fuzzy match
        match = _fuzzy_match(company, kb)
        if match:
            ticker = match["ticker"]
            resolved[company] = ticker
            print(f"   Fuzzy match: '{company}' → {ticker}")
            continue

        # 3b. ChromaDB RAG
        print(f"   Fuzzy miss for '{company}', trying ChromaDB RAG...")
        chroma_results = _chromadb_search(company)
        if chroma_results:
            best = chroma_results[0]
            ticker = best["ticker"]
            resolved[company] = ticker
            print(f"   ChromaDB match: '{company}' → {ticker}")
            continue

        # 3c. No match found
        errors.append(company)
        print(f"   [ERROR] No ticker found for company: '{company}'")

    # Determine final ticker list: use resolved values, deduplicated
    final_tickers = list(dict.fromkeys(resolved.values()))
    print(f"\n   Final resolved tickers: {final_tickers}")

    if errors:
        error_msg = f"Unable to identify valid ticker(s) for: {', '.join(errors)}"
        print(f"   [ERROR] {error_msg}")
        state["ticker_resolution_error"] = error_msg
        state["data"]["tickers"] = []
    else:
        state["ticker_resolution_error"] = None
        state["data"]["tickers"] = final_tickers

    state["ticker_resolution"] = resolved
    print(f"\n{'='*60}")
    print(f"◀ Finished: Ticker Resolver")
    print(f"{'='*60}\n")

    return state
