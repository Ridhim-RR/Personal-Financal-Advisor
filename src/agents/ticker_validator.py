"""Ticker Validator Agent — validates ticker symbols against Yahoo Finance.

This agent runs AFTER the Ticker Resolver and BEFORE analyst agents.
It verifies every ticker in state["data"]["tickers"] is a valid symbol
that can return market data.

If validation fails, execution stops — analyst agents are NOT invoked.
"""

from typing import Optional

from langsmith import traceable
import yfinance as yf

from src.graph.state import AgentState


def validate_ticker(ticker: str) -> tuple[bool, Optional[str]]:
    """Validate a ticker symbol by attempting to fetch metadata from Yahoo Finance.

    Returns:
        (is_valid, error_message)
    """
    try:
        yft = yf.Ticker(ticker)
        info = yft.info

        if not info:
            return False, f"No metadata returned by Yahoo Finance for ticker: {ticker}"

        # Check that we got meaningful data
        if info.get("regularMarketPrice") is None and info.get("marketCap") is None:
            # Some tickers return info dict with only a "error" or "message" key
            if "error" in info or info.get("shortName") is None:
                return False, f"Yahoo Finance returned empty data for ticker: {ticker}"

        return True, None

    except Exception as e:
        error_msg = str(e)[:200]
        return False, f"Yahoo Finance validation failed for ticker '{ticker}': {error_msg}"


@traceable(name="ticker_validator", run_type="chain")
def ticker_validator_agent(state: AgentState) -> AgentState:
    """Validate all tickers in state before allowing analyst execution.

    Uses Yahoo Finance to verify each ticker can return market data.
    Sets ticker_resolution_error if any ticker fails validation,
    preventing downstream agents from running.
    """
    print(f"\n{'='*60}")
    print(f"▶ Running: Ticker Validator")
    print(f"{'='*60}")

    tickers = state["data"].get("tickers", [])
    print(f"   Validating tickers: {tickers}")

    failed: list[str] = []

    for ticker in tickers:
        is_valid, error = validate_ticker(ticker)
        if is_valid:
            print(f"   ✓ {ticker}: VALID")
        else:
            print(f"   ✗ {ticker}: INVALID — {error}")
            failed.append(error)

    if failed:
        combined_error = "; ".join(failed)
        print(f"\n   [ERROR] Ticker validation failed: {combined_error}")
        state["ticker_resolution_error"] = combined_error
        # Clear tickers to prevent downstream agents from running on bad data
        state["data"]["tickers"] = []
    else:
        state["ticker_resolution_error"] = None
        print(f"\n   All tickers validated successfully: {tickers}")

    print(f"\n{'='*60}")
    print(f"◀ Finished: Ticker Validator")
    print(f"{'='*60}\n")

    return state
