from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json

from src.graph.state import AgentState, show_agent_reasoning
from app.backend.services.market_data_provider import get_financial_metrics, get_market_cap, search_line_items
from src.utils.llm import call_llm
from src.utils.progress import progress


class FundamentalAnalystSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int = Field(description="Confidence 0-100")
    reasoning: str = Field(description="Reasoning for the decision")


def fundamental_analyst_agent(state: AgentState, agent_id: str = "fundamental_analyst_agent"):
    """Analyzes a company's fundamentals — profitability, growth, efficiency, and valuation
    — and generates a trading signal with LLM-powered reasoning.
    """
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]

    analysis_data = {}
    fundamental_analysis = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching financial metrics")

        metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=5)

        progress.update_status(agent_id, ticker, "Gathering financial line items")
        line_items = search_line_items(
            ticker,
            [
                "revenue",
                "net_income",
                "free_cash_flow",
                "total_assets",
                "total_liabilities",
                "shareholders_equity",
                "outstanding_shares",
            ],
            end_date,
            period="ttm",
            limit=5,
        )

        progress.update_status(agent_id, ticker, "Getting market cap")
        market_cap = get_market_cap(ticker, end_date)

        progress.update_status(agent_id, ticker, "Analyzing profitability")
        profitability = _analyze_profitability(metrics)

        progress.update_status(agent_id, ticker, "Analyzing growth trends")
        growth = _analyze_growth(metrics)

        progress.update_status(agent_id, ticker, "Analyzing financial health")
        health = _analyze_financial_health(metrics, line_items)

        progress.update_status(agent_id, ticker, "Analyzing valuation")
        valuation = _analyze_valuation(metrics, market_cap)

        score = sum([
            profitability.get("score", 0),
            growth.get("score", 0),
            health.get("score", 0),
            valuation.get("score", 0),
        ])
        max_score = 20

        analysis_data[ticker] = {
            "score": score,
            "max_score": max_score,
            "profitability": profitability,
            "growth": growth,
            "financial_health": health,
            "valuation": valuation,
        }

        progress.update_status(agent_id, ticker, "Generating fundamental analysis")
        output = _generate_output(ticker, analysis_data, state, agent_id)

        fundamental_analysis[ticker] = {
            "signal": output.signal,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
        }

        progress.update_status(agent_id, ticker, "Done", analysis=output.reasoning)

    message = HumanMessage(content=json.dumps(fundamental_analysis), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(fundamental_analysis, agent_id)

    state["data"]["analyst_signals"][agent_id] = fundamental_analysis

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": state["data"]}


def _analyze_profitability(metrics: list) -> dict:
    """Score profitability based on ROE, net margin, and operating margin."""
    if not metrics:
        return {"score": 0, "details": "No data"}

    m = metrics[0]
    score = 0
    details = []

    if m.return_on_equity and m.return_on_equity > 0.15:
        score += 3
        details.append(f"Strong ROE: {m.return_on_equity:.1%}")
    elif m.return_on_equity:
        details.append(f"ROE: {m.return_on_equity:.1%}")

    if m.net_margin and m.net_margin > 0.15:
        score += 2
        details.append(f"Healthy net margin: {m.net_margin:.1%}")
    elif m.net_margin:
        details.append(f"Net margin: {m.net_margin:.1%}")

    if m.operating_margin and m.operating_margin > 0.15:
        score += 2
        details.append(f"Strong operating margin: {m.operating_margin:.1%}")
    elif m.operating_margin:
        details.append(f"Operating margin: {m.operating_margin:.1%}")

    return {"score": score, "details": "; ".join(details)}


def _analyze_growth(metrics: list) -> dict:
    """Score growth based on revenue and earnings growth rates."""
    if not metrics:
        return {"score": 0, "details": "No data"}

    m = metrics[0]
    score = 0
    details = []

    if m.revenue_growth and m.revenue_growth > 0.10:
        score += 3
        details.append(f"Revenue growth: {m.revenue_growth:.1%}")
    elif m.revenue_growth:
        details.append(f"Revenue growth: {m.revenue_growth:.1%}")

    if m.earnings_growth and m.earnings_growth > 0.10:
        score += 3
        details.append(f"Earnings growth: {m.earnings_growth:.1%}")
    elif m.earnings_growth:
        details.append(f"Earnings growth: {m.earnings_growth:.1%}")

    if m.free_cash_flow_growth and m.free_cash_flow_growth > 0.10:
        score += 2
        details.append(f"FCF growth: {m.free_cash_flow_growth:.1%}")
    elif m.free_cash_flow_growth:
        details.append(f"FCF growth: {m.free_cash_flow_growth:.1%}")

    return {"score": score, "details": "; ".join(details)}


def _analyze_financial_health(metrics: list, line_items: list) -> dict:
    """Score financial health based on debt levels and liquidity."""
    score = 0
    details = []

    if metrics:
        m = metrics[0]
        if m.debt_to_equity is not None and m.debt_to_equity < 0.5:
            score += 3
            details.append(f"Low debt/equity: {m.debt_to_equity:.1f}")
        elif m.debt_to_equity is not None:
            details.append(f"Debt/equity: {m.debt_to_equity:.1f}")

        if m.current_ratio is not None and m.current_ratio > 1.5:
            score += 2
            details.append(f"Strong current ratio: {m.current_ratio:.1f}")
        elif m.current_ratio is not None:
            details.append(f"Current ratio: {m.current_ratio:.1f}")

    if not details:
        if line_items and len(line_items) >= 2:
            latest = line_items[0]
            prev = line_items[1]
            if (latest.total_liabilities and latest.total_assets and latest.total_assets > 0 and
                    prev.total_liabilities and prev.total_assets and prev.total_assets > 0):
                curr_ratio = latest.total_liabilities / latest.total_assets
                prev_ratio = prev.total_liabilities / prev.total_assets
                if curr_ratio < prev_ratio:
                    score += 1
                    details.append("Liabilities/assets ratio improving")

    return {"score": score, "details": "; ".join(details) if details else "Insufficient data"}


def _analyze_valuation(metrics: list, market_cap: float) -> dict:
    """Score valuation based on P/E, P/B, and FCF yield."""
    if not metrics or not market_cap:
        return {"score": 0, "details": "No valuation data"}

    m = metrics[0]
    score = 0
    details = []

    if m.price_to_earnings_ratio and m.price_to_earnings_ratio < 20:
        score += 3
        details.append(f"P/E: {m.price_to_earnings_ratio:.1f}")
    elif m.price_to_earnings_ratio:
        details.append(f"P/E: {m.price_to_earnings_ratio:.1f}")

    if m.price_to_book_ratio and m.price_to_book_ratio < 3:
        score += 2
        details.append(f"P/B: {m.price_to_book_ratio:.1f}")
    elif m.price_to_book_ratio:
        details.append(f"P/B: {m.price_to_book_ratio:.1f}")

    if m.free_cash_flow_yield and m.free_cash_flow_yield > 0.05:
        score += 2
        details.append(f"FCF yield: {m.free_cash_flow_yield:.1%}")
    elif m.free_cash_flow_yield:
        details.append(f"FCF yield: {m.free_cash_flow_yield:.1%}")

    return {"score": score, "details": "; ".join(details)}


def _generate_output(
    ticker: str,
    analysis_data: dict,
    state: AgentState,
    agent_id: str,
) -> FundamentalAnalystSignal:
    """Generate final signal using the LLM."""
    question = state.get("question", "")
    advisor_context = state.get("data", {}).get("advisor_context", {})

    template = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a fundamental analyst. Evaluate the company's financial health, "
            "profitability, growth, and valuation. Be concise.\n\n"
            "Signal rules:\n"
            "- Bullish: strong metrics across all categories\n"
            "- Bearish: weak fundamentals or overvalued\n"
            "- Neutral: mixed signals\n\n"
            "Return JSON only.",
        ),
        (
            "human",
            "User request: {question}\n"
            "Advisor context: {advisor_context}\n\n"
            "Analyze {ticker}:\n{analysis_data}\n\n"
            'Return: {{"signal": "bullish"|"bearish"|"neutral", "confidence": int, "reasoning": "..."}}',
        ),
    ])

    prompt = template.invoke({
        "analysis_data": json.dumps(analysis_data, indent=2),
        "ticker": ticker,
        "question": question or "No specific request",
        "advisor_context": json.dumps(advisor_context) if advisor_context else "No advisor context",
    })

    def default():
        return FundamentalAnalystSignal(signal="neutral", confidence=0, reasoning="Analysis error")

    return call_llm(prompt=prompt, pydantic_model=FundamentalAnalystSignal, agent_name=agent_id, state=state, default_factory=default)
