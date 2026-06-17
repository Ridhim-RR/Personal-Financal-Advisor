from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.llm import call_llm
from src.utils.progress import progress


class AdvisorContext(BaseModel):
    risk_profile: str = Field(description="Conservative / Moderate / Aggressive")
    recommended_strategy: str = Field(description="Strategy summary")
    constraints: dict[str, str] = Field(description="Key constraints for other agents")
    reasoning: str = Field(description="Why this advice fits the user")


def personal_financial_advisor_agent(state: AgentState, agent_id: str = "personal_financial_advisor_agent"):
    """Analyzes the user profile, portfolio, semantic memories, and conversation
    history to produce personalized context that downstream agents use.

    Receives from state:
      - user_profile:       from PostgreSQL
      - portfolio:          from PostgreSQL
      - memory:             semantic memories from ChromaDB
      - conversation_context: recent conversation from ChromaDB
      - question:           user's current question
    """
    profile = state.get("user_profile", {})
    portfolio = state.get("portfolio", {})
    memories = state.get("memory", [])
    conversation = state.get("conversation_context", [])
    question = state.get("question", "")

    progress.update_status(agent_id, None, "Analyzing user profile + memories")

    context_brief = {
        "risk_appetite": profile.get("risk_appetite", "moderate"),
        "investment_goal": profile.get("investment_goal", "growth"),
        "investment_horizon": profile.get("investment_horizon", "medium"),
        "preferred_sectors": profile.get("preferred_sectors", []),
        "excluded_sectors": profile.get("excluded_sectors", []),
        "current_positions": portfolio.get("positions", {}),
        "target_allocation": portfolio.get("target_allocation", {}),
        "semantic_memories": memories,
        "conversation_history": conversation,
        "user_question": question,
    }

    progress.update_status(agent_id, None, "Generating personalized context")

    output = _generate_advisor_context(context_brief, state, agent_id)

    advisor_context = {
        "risk_profile": output.risk_profile,
        "recommended_strategy": output.recommended_strategy,
        "constraints": output.constraints,
        "reasoning": output.reasoning,
    }

    state["data"]["advisor_context"] = advisor_context

    message = HumanMessage(content=json.dumps(advisor_context), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(advisor_context, "Personal Financial Advisor")

    progress.update_status(agent_id, None, "Done")

    return {
        "messages": state["messages"] + [message],
        "data": state["data"],
    }


def _generate_advisor_context(context: dict, state: AgentState, agent_id: str) -> AdvisorContext:
    """LLM generates personalized context from hybrid memory inputs."""

    template = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a personal financial advisor. Your job is to analyze the user's "
            "profile, portfolio, semantic memories, and conversation history to produce "
            "a concise context brief that guides other analyst agents.\n\n"
            "Consider:\n"
            "1. Risk appetite → acceptable volatility and position sizing\n"
            "2. Investment goal → growth, income, or preservation\n"
            "3. Investment horizon → short/medium/long-term focus\n"
            "4. Current holdings → avoid over-concentration\n"
            "5. Target allocation → maintain balance\n"
            "6. Semantic memories → what the system knows about the user\n"
            "7. Conversation history → recent user questions and concerns\n"
            "8. Current question → what the user is asking right now\n\n"
            "Output clear constraints. Return JSON only.",
        ),
        (
            "human",
            "User Profile:\n"
            "- Risk: {risk}\n- Goal: {goal}\n- Horizon: {horizon}\n"
            "- Preferred sectors: {sectors}\n- Excluded sectors: {excluded}\n\n"
            "Portfolio:\n{positions}\n\n"
            "Semantic memories:\n{memories}\n\n"
            "Recent conversation:\n{conversation}\n\n"
            "Current question: {question}\n\n"
            "Return:\n"
            '{{\n'
            '  "risk_profile": "...",\n'
            '  "recommended_strategy": "...",\n'
            '  "constraints": {{"sector": "...", "position_sizing": "...", "volatility": "..."}},\n'
            '  "reasoning": "..."\n'
            "}}",
        ),
    ])

    positions_str = json.dumps(context.get("current_positions", {}), indent=2)
    memories_str = "\n".join(context.get("semantic_memories", [])) or "None"
    conversation_str = "\n".join(context.get("conversation_history", [])) or "None"

    prompt = template.invoke({
        "risk": context.get("risk_appetite", "moderate"),
        "goal": context.get("investment_goal", "growth"),
        "horizon": context.get("investment_horizon", "medium"),
        "sectors": ", ".join(context.get("preferred_sectors", [])) or "any",
        "excluded": ", ".join(context.get("excluded_sectors", [])) or "none",
        "positions": positions_str,
        "memories": memories_str,
        "conversation": conversation_str,
        "question": context.get("user_question", ""),
    })

    def default():
        return AdvisorContext(
            risk_profile="Moderate",
            recommended_strategy="Diversified growth",
            constraints={"sector": "any", "position_sizing": "medium"},
            reasoning="Default — no profile data",
        )

    return call_llm(
        prompt=prompt,
        pydantic_model=AdvisorContext,
        agent_name=agent_id,
        state=state,
        default_factory=default,
    )
