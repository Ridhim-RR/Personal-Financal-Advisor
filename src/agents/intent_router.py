"""Intent Router Agent — classifies user questions and routes to the right workflow.

The Intent Router ONLY classifies intent and extracts company names.
It NEVER generates ticker symbols. Ticker resolution is handled
by the dedicated Ticker Resolver node.
"""

from typing import Literal, Optional
import re
from pydantic import BaseModel, Field
from langsmith import traceable
from src.utils.llm import call_llm
from src.graph.state import AgentState


# Pattern to detect explicit ticker symbols
# US tickers: 2-5 uppercase letters (e.g., AAPL, MSFT, GOOGL)
# Indian tickers: 2-15 uppercase letters with .NS suffix (e.g., RELIANCE.NS, TATAMOTORS.NS)
_EXPLICIT_TICKER_RE = re.compile(r'\b[A-Z]{2,5}(?:\.NS)?\b|\b[A-Z]{2,15}\.NS\b')


def _is_explicit_ticker(word: str) -> bool:
    """Check if a word looks like an explicit ticker symbol."""
    word = word.strip().rstrip(".,!?:;")
    return bool(re.match(r'^[A-Z]{2,5}(\.NS)?$', word)) or bool(re.match(r'^[A-Z]{2,15}\.NS$', word))


class RoutingDecision(BaseModel):
    intent: Literal[
        "portfolio_analysis",
        "stock_analysis",
        "stock_discovery",
        "strategy_advice",
        "general_finance",
    ]
    company_names: list[str] = Field(
        default=[],
        description="Company names extracted from the question (e.g., ['Apple', 'Microsoft']). "
                    "NEVER put ticker symbols here.",
    )
    explicit_tickers: list[str] = Field(
        default=[],
        description="Only populate if the user explicitly typed a ticker symbol "
                    "(e.g., 'AAPL', 'MSFT', 'RELIANCE.NS'). Do NOT convert company names to tickers.",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


ROUTER_PROMPT = """You are a routing classifier for an AI investment advisor.

Classify the user's question into ONE of these intents:

- portfolio_analysis: User asks about their existing portfolio — risk, performance, rebalancing, diversification, allocation. Usually mentions "my portfolio", "my holdings", "my positions".
- stock_analysis: User asks about specific stocks — buy/sell/hold recommendations, analysis of a company, "should I buy/sell X". Always identify which companies are mentioned.
- stock_discovery: User asks for stock suggestions, ideas, or screening — "find me stocks that...", "suggest some...", "what are good...", stock screening criteria.
- strategy_advice: User asks for general financial planning advice — saving, retirement, goal setting, "what should I do with my money".
- general_finance: User asks educational questions — "what is a PE ratio", "how does the market work", definitional questions, financial concepts.

Rules:
1. Extract company NAMES (e.g., "Apple", "Microsoft", "Reliance Industries", "Tata Motors"). Do NOT convert them to ticker symbols.
2. If the user explicitly types a ticker symbol (all-caps, 1-5 letters, optionally with .NS suffix), put it in explicit_tickers.
3. company_names should contain full company names as written by the user, not tickers.
4. For stock_analysis, you MUST identify the company/companies the user is asking about.
5. If the user says "stock" but no company is named, set company_names to an empty list.

Respond in JSON format:
{{
    "intent": "stock_analysis",
    "company_names": ["NVIDIA"],
    "explicit_tickers": ["NVDA"],
    "confidence": 0.95,
    "reasoning": "User asks about buying NVIDIA stock and provided ticker NVDA"
}}

User question: {question}"""


def _default_routing():
    return RoutingDecision(
        intent="general_finance",
        company_names=[],
        explicit_tickers=[],
        confidence=0.0,
        reasoning="Failed to classify intent, defaulting to general_finance",
    )


@traceable(name="intent_router", run_type="chain")
def intent_router_agent(state: AgentState) -> AgentState:
    """Analyze the user question and determine which workflow to route to.

    Only classifies intent and extracts company names.
    NEVER generates ticker symbols.
    """
    question = state.get("question", "")

    print(f"\n{'='*60}")
    print(f"▶ Running: Intent Router")
    print(f"   Question: {question}")
    print(f"{'='*60}")

    # Pre-process: detect explicit tickers in the question before LLM
    pre_detected_tickers = []
    for word in question.split():
        cleaned = word.strip().rstrip(".,!?:;")
        if _is_explicit_ticker(cleaned):
            pre_detected_tickers.append(cleaned)
            print(f"   Pre-detected explicit ticker: {cleaned}")

    prompt = ROUTER_PROMPT.format(question=question)

    decision: RoutingDecision = call_llm(
        prompt=prompt,
        pydantic_model=RoutingDecision,
        agent_name="intent_router",
        state=state,
        default_factory=_default_routing,
    )

    # Merge pre-detected explicit tickers with LLM-extracted ones
    all_explicit = list(dict.fromkeys(pre_detected_tickers + decision.explicit_tickers))

    print(f"\n{'='*34}")
    print(f"  Intent: {decision.intent}")
    print(f"  Confidence: {decision.confidence}")
    print(f"  Company Names: {decision.company_names}")
    print(f"  Explicit Tickers: {all_explicit}")
    print(f"  Reasoning: {decision.reasoning}")
    print(f"{'='*34}")

    # Do NOT set state["data"]["tickers"] here — that's the Ticker Resolver's job.
    # Instead, store company names and explicit tickers for the resolver.
    state["company_names"] = decision.company_names if decision.intent == "stock_analysis" else []
    state["explicit_tickers"] = all_explicit
    state["data"]["tickers"] = []  # clear — resolver will populate

    # Store the routing decision as a dict for downstream use
    routing_dict = decision.model_dump()
    routing_dict["explicit_tickers"] = all_explicit
    state["routing_decision"] = routing_dict

    print(f"\n{'='*60}")
    print(f"◀ Finished: Intent Router")
    print(f"{'='*60}\n")

    return state
