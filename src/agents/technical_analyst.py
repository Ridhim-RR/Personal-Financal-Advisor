from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json
import numpy as np
import pandas as pd

from src.graph.state import AgentState, show_agent_reasoning
from src.tools.api import prices_to_df
from app.backend.services.market_data_provider import get_prices
from src.utils.llm import call_llm
from src.utils.progress import progress


class TechnicalAnalystSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int = Field(description="Confidence 0-100")
    reasoning: str = Field(description="Reasoning")


def technical_analyst_agent(state: AgentState, agent_id: str = "technical_analyst_agent"):
    """Analyzes price and volume data using technical indicators and generates a signal."""
    data = state["data"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    tickers = data["tickers"]

    analysis_data = {}
    technical_analysis = {}

    print(f"   [Technical] start_date={start_date!r}, end_date={end_date!r}")
    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching price data")

        prices = get_prices(ticker, start_date, end_date)
        print(f"   [Technical] {ticker}: got {len(prices) if prices else 0} prices")
        if not prices or len(prices) < 50:
            print(f"   [Technical] {ticker}: SKIPPING — only {len(prices) if prices else 0} prices, need >= 50")
            progress.update_status(agent_id, ticker, "Insufficient price data")
            continue

        df = prices_to_df(prices)

        progress.update_status(agent_id, ticker, "Computing technical indicators")

        trend = _analyze_trend(df)
        momentum = _analyze_momentum(df)
        volume = _analyze_volume(df)
        volatility = _analyze_volatility(df)

        score = sum([trend.get("score", 0), momentum.get("score", 0), volume.get("score", 0)])
        details = "; ".join(filter(None, [
            trend.get("details", ""),
            momentum.get("details", ""),
            volume.get("details", ""),
            volatility.get("details", ""),
        ]))

        analysis_data[ticker] = {
            "score": score,
            "max_score": 15,
            "current_price": float(df["close"].iloc[-1]) if not df.empty else 0,
            "sma_50": trend.get("sma_50"),
            "sma_200": trend.get("sma_200"),
            "rsi": momentum.get("rsi"),
            "details": details,
        }

        progress.update_status(agent_id, ticker, "Generating technical analysis")
        output = _generate_output(ticker, analysis_data, state, agent_id)

        technical_analysis[ticker] = {
            "signal": output.signal,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
        }

        progress.update_status(agent_id, ticker, "Done", analysis=output.reasoning)

    message = HumanMessage(content=json.dumps(technical_analysis), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(technical_analysis, agent_id)

    state["data"]["analyst_signals"][agent_id] = technical_analysis

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": state["data"]}


def _safe(val, default=0.0):
    try:
        return float(val) if not (pd.isna(val) or np.isnan(val)) else default
    except (ValueError, TypeError):
        return default


def _analyze_trend(df: pd.DataFrame) -> dict:
    """Analyze trend using SMA crossovers and price position."""
    if len(df) < 200:
        return {"score": 0, "details": "Insufficient data for trend analysis"}

    closes = df["close"].astype(float)
    sma_50 = closes.rolling(50).mean()
    sma_200 = closes.rolling(200).mean()

    current_price = _safe(closes.iloc[-1])
    current_sma_50 = _safe(sma_50.iloc[-1])
    current_sma_200 = _safe(sma_200.iloc[-1])
    prev_sma_50 = _safe(sma_50.iloc[-2])
    prev_sma_200 = _safe(sma_200.iloc[-2])

    score = 0
    details = []

    # Price vs SMA
    if current_price > current_sma_50:
        score += 2
        details.append("Price above 50-day SMA")
    if current_price > current_sma_200:
        score += 2
        details.append("Price above 200-day SMA")

    # Golden cross / death cross
    if prev_sma_50 <= prev_sma_200 and current_sma_50 > current_sma_200:
        score += 3
        details.append("Golden cross (50-day crossed above 200-day)")
    elif prev_sma_50 >= prev_sma_200 and current_sma_50 < current_sma_200:
        score -= 2
        details.append("Death cross (50-day crossed below 200-day)")

    return {"score": max(score, 0), "details": "; ".join(details), "sma_50": current_sma_50, "sma_200": current_sma_200}


def _analyze_momentum(df: pd.DataFrame) -> dict:
    """Analyze momentum using RSI and rate of change."""
    if len(df) < 20:
        return {"score": 0, "details": "Insufficient data for momentum"}

    closes = df["close"].astype(float)
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    current_rsi = _safe(rsi.iloc[-1])
    score = 0
    details = []

    if current_rsi < 30:
        score += 3
        details.append(f"Oversold (RSI: {current_rsi:.0f})")
    elif current_rsi < 40:
        score += 1
        details.append(f"Near oversold (RSI: {current_rsi:.0f})")
    elif current_rsi > 70:
        score -= 1
        details.append(f"Overbought (RSI: {current_rsi:.0f})")
    elif current_rsi > 60:
        details.append(f"RSI: {current_rsi:.0f}")
    else:
        details.append(f"RSI: {current_rsi:.0f}")

    # Rate of change
    roc = (closes.iloc[-1] / closes.iloc[-20] - 1) * 100
    if roc > 5:
        score += 2
        details.append(f"Strong 20-day ROC: {roc:.1f}%")
    elif roc < -5:
        score -= 1
        details.append(f"Weak 20-day ROC: {roc:.1f}%")

    return {"score": max(score, 0), "details": "; ".join(details), "rsi": current_rsi}


def _analyze_volume(df: pd.DataFrame) -> dict:
    """Analyze volume trends for confirmation."""
    if len(df) < 20:
        return {"score": 0, "details": "Insufficient volume data"}

    volume = df["volume"].astype(float)
    avg_vol = volume.rolling(20).mean()
    current_vol = _safe(volume.iloc[-1])
    current_avg = _safe(avg_vol.iloc[-1])
    price_change = _safe(df["close"].astype(float).pct_change().iloc[-1])

    score = 0
    details = []

    if current_avg > 0 and current_vol > current_avg * 1.5:
        if price_change > 0:
            score += 2
            details.append("High volume on up day (bullish confirmation)")
        elif price_change < 0:
            score -= 1
            details.append("High volume on down day (bearish)")
        else:
            details.append("High volume, flat price")

    return {"score": max(score, 0), "details": "; ".join(details)}


def _analyze_volatility(df: pd.DataFrame) -> dict:
    """Measure recent volatility for context."""
    if len(df) < 20:
        return {"score": 0, "details": "Insufficient data"}

    closes = df["close"].astype(float)
    returns = closes.pct_change().dropna()
    recent_vol = returns.tail(20).std() * (252 ** 0.5)

    if recent_vol > 0.4:
        return {"score": 0, "details": f"High annualized vol: {recent_vol:.1%}"}
    elif recent_vol > 0.2:
        return {"score": 0, "details": f"Moderate annualized vol: {recent_vol:.1%}"}
    else:
        return {"score": 1, "details": f"Low annualized vol: {recent_vol:.1%}"}


def _generate_output(
    ticker: str,
    analysis_data: dict,
    state: AgentState,
    agent_id: str,
) -> TechnicalAnalystSignal:
    question = state.get("question", "")
    advisor_context = state.get("data", {}).get("advisor_context", {})

    template = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a technical analyst. Evaluate price trends, momentum, "
            "and volume patterns to make a recommendation.\n\n"
            "Signal rules:\n"
            "- Bullish: uptrend, positive momentum, volume confirmation\n"
            "- Bearish: downtrend, negative momentum, distribution\n"
            "- Neutral: mixed or sideways\n\n"
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
        return TechnicalAnalystSignal(signal="neutral", confidence=0, reasoning="Analysis error")

    return call_llm(prompt=prompt, pydantic_model=TechnicalAnalystSignal, agent_name=agent_id, state=state, default_factory=default)
