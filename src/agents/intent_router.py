"""Intent Router Agent — classifies user questions and routes to the right workflow."""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from langsmith import traceable
from src.utils.llm import call_llm
from src.graph.state import AgentState


class RoutingDecision(BaseModel):
    intent: Literal[
        "portfolio_analysis",
        "stock_analysis",
        "stock_discovery",
        "strategy_advice",
        "general_finance",
    ]
    tickers: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


ROUTER_PROMPT = """You are a routing classifier for an AI investment advisor.

Classify the user's question into ONE of these intents:

- portfolio_analysis: User asks about their existing portfolio — risk, performance, rebalancing, diversification, allocation. Usually mentions "my portfolio", "my holdings", "my positions".
- stock_analysis: User asks about specific stocks — buy/sell/hold recommendations, analysis of a company, "should I buy/sell X". Always extract ticker symbols.
- stock_discovery: User asks for stock suggestions, ideas, or screening — "find me stocks that...", "suggest some...", "what are good...", stock screening criteria.
- strategy_advice: User asks for general financial planning advice — saving, retirement, goal setting, "what should I do with my money".
- general_finance: User asks educational questions — "what is a PE ratio", "how does the market work", definitional questions, financial concepts.

Rules:
1. Extract ticker symbols only for stock_analysis intent. For all other intents, return an empty list.
2. If the user mentions a company name but no ticker, convert it to a ticker (e.g., "Apple" → "AAPL", "Microsoft" → "MSFT", "NVIDIA" → "NVDA").
3. Return the tickers as a list of uppercase strings.
4. Confidence should reflect how sure you are about the classification.

Respond in JSON format:
{{
    "intent": "...",
    "tickers": ["NVDA"],
    "confidence": 0.95,
    "reasoning": "User asks about buying NVIDIA stock"
}}

User question: {question}"""


def _default_routing():
    return RoutingDecision(
        intent="general_finance",
        tickers=[],
        confidence=0.0,
        reasoning="Failed to classify intent, defaulting to general_finance",
    )


@traceable(name="intent_router", run_type="chain")
def intent_router_agent(state: AgentState) -> AgentState:
    """Analyze the user question and determine which workflow to route to.

    Only uses the user question — does NOT load portfolio, memory, or market data.
    """
    question = state.get("question", "")

    print(f"\n{'='*60}")
    print(f"▶ Running: Intent Router")
    print(f"   Question: {question}")
    print(f"{'='*60}")

    prompt = ROUTER_PROMPT.format(question=question)

    decision: RoutingDecision = call_llm(
        prompt=prompt,
        pydantic_model=RoutingDecision,
        agent_name="intent_router",
        state=state,
        default_factory=_default_routing,
    )

    print(f"\n{'='*34}")
    print(f"  Intent: {decision.intent}")
    print(f"  Confidence: {decision.confidence}")
    print(f"  Tickers: {decision.tickers}")
    print(f"  Reasoning: {decision.reasoning}")
    print(f"{'='*34}")

    # Replace state tickers with router-extracted tickers (or empty list)
    # This prevents dummy frontend-supplied tickers from polluting the workflow
    state["data"]["tickers"] = decision.tickers if decision.tickers else []
    print(f"   Set tickers to: {state['data']['tickers']}")

    # Store the routing decision as a dict for downstream use
    state["routing_decision"] = decision.model_dump()

    print(f"\n{'='*60}")
    print(f"◀ Finished: Intent Router")
    print(f"{'='*60}\n")

    return state
