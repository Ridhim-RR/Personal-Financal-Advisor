from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.llm import call_llm
from src.utils.progress import progress


class StockDiscoverySignal(BaseModel):
    signal: Literal["buy", "watch", "pass"]
    confidence: int = Field(description="Confidence 0-100")
    reasoning: str = Field(description="Reasoning for the suggestion")
    suggested_tickers: list[str] = Field(default_factory=list)
    screening_criteria: str = ""


def stock_discovery_agent(state: AgentState, agent_id: str = "stock_discovery_agent"):
    """Discovers stocks based on user-specified criteria."""
    question = state.get("question", "")
    user_profile = state.get("user_profile", {})
    advisor_context = state["data"].get("advisor_context", {})
    portfolio = state["data"].get("portfolio", {})

    progress.update_status(agent_id, None, "Discovering stocks")

    template = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a stock discovery agent. Based on the user's request, "
            "suggest tickers that match their criteria. Be specific with ticker symbols. "
            "Return JSON only.",
        ),
        (
            "human",
            "User request: {question}\n"
            "User profile: {profile}\n"
            "Advisor context: {advisor_context}\n"
            "Current portfolio: {portfolio}\n\n"
            'Return: {{"signal": "buy"|"watch"|"pass", "confidence": int, '
            '"reasoning": "...", "suggested_tickers": ["NVDA", "AMD"], '
            '"screening_criteria": "..."}}',
        ),
    ])

    prompt = template.invoke({
        "question": question,
        "profile": json.dumps(user_profile) if user_profile else "None",
        "advisor_context": json.dumps(advisor_context) if advisor_context else "None",
        "portfolio": json.dumps(portfolio.get("positions", {}), default=str),
    })

    def default():
        return StockDiscoverySignal(
            signal="watch", confidence=0, reasoning="Analysis error",
            suggested_tickers=[],
        )

    output: StockDiscoverySignal = call_llm(
        prompt=prompt,
        pydantic_model=StockDiscoverySignal,
        agent_name=agent_id,
        state=state,
        default_factory=default,
    )

    discovery = {
        "discovery": {
            "signal": output.signal,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
            "suggested_tickers": output.suggested_tickers,
            "screening_criteria": output.screening_criteria,
        }
    }

    state["data"]["analyst_signals"][agent_id] = discovery
    state["data"]["discovered_tickers"] = output.suggested_tickers

    message = HumanMessage(content=json.dumps(discovery), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(discovery, agent_id)

    progress.update_status(agent_id, None, "Done")

    return {"messages": state["messages"] + [message], "data": state["data"]}
