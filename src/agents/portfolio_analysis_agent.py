from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.llm import call_llm
from src.utils.progress import progress


class PortfolioAnalysisSignal(BaseModel):
    signal: Literal["healthy", "needs_rebalancing", "overweight", "underweight", "risky"]
    confidence: int = Field(description="Confidence 0-100")
    reasoning: str = Field(description="Analysis reasoning")
    suggested_actions: list[str] = Field(default_factory=list)


def portfolio_analysis_agent(state: AgentState, agent_id: str = "portfolio_analysis_agent"):
    """Analyzes portfolio composition, risk exposure, and allocation."""
    portfolio = state["data"].get("portfolio", {})
    tickers = state["data"].get("tickers", [])
    question = state.get("question", "")
    user_profile = state.get("user_profile", {})
    advisor_context = state["data"].get("advisor_context", {})

    progress.update_status(agent_id, None, "Analyzing portfolio")

    positions = portfolio.get("positions", {})
    cash = portfolio.get("cash", 0)
    total_value = cash + sum(
        pos.get("long", 0) * pos.get("avg_cost", 0) for pos in positions.values()
    )

    template = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a portfolio analysis agent. Evaluate the user's portfolio "
            "for risk, diversification, and alignment with their profile. "
            "Return JSON only.",
        ),
        (
            "human",
            "User request: {question}\n"
            "Advisor context: {advisor_context}\n"
            "User profile: {profile}\n\n"
            "Portfolio:\n"
            "Cash: ${cash:.2f}\n"
            "Total value: ${total_value:.2f}\n"
            "Positions: {positions}\n\n"
            'Return: {{"signal": "healthy"|"needs_rebalancing"|"overweight"|"underweight"|"risky", '
            '"confidence": int, "reasoning": "...", "suggested_actions": [...]}}',
        ),
    ])

    prompt = template.invoke({
        "question": question or "Analyze my portfolio",
        "advisor_context": json.dumps(advisor_context) if advisor_context else "None",
        "profile": json.dumps(user_profile) if user_profile else "None",
        "cash": cash,
        "total_value": total_value,
        "positions": json.dumps(positions, default=str),
    })

    def default():
        return PortfolioAnalysisSignal(
            signal="needs_rebalancing", confidence=0, reasoning="Analysis error",
            suggested_actions=["Review portfolio manually"],
        )

    output: PortfolioAnalysisSignal = call_llm(
        prompt=prompt,
        pydantic_model=PortfolioAnalysisSignal,
        agent_name=agent_id,
        state=state,
        default_factory=default,
    )

    analysis = {
        "portfolio": {
            "signal": output.signal,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
            "suggested_actions": output.suggested_actions,
        }
    }

    state["data"]["analyst_signals"][agent_id] = analysis

    message = HumanMessage(content=json.dumps(analysis), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(analysis, agent_id)

    progress.update_status(agent_id, None, "Done")

    return {"messages": state["messages"] + [message], "data": state["data"]}
