import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from colorama import Fore, Style, init
import questionary
from src.agents.portfolio_manager import portfolio_management_agent
from src.agents.risk_manager import risk_management_agent
from src.agents.personal_financial_advisor import personal_financial_advisor_agent
from src.graph.state import AgentState
from src.utils.display import print_trading_output
from src.utils.analysts import ANALYST_ORDER, get_analyst_nodes, DEFAULT_PERSONALIZED_ANALYSTS
from src.utils.progress import progress
from src.utils.visualize import save_graph_as_png
from src.cli.input import (
    parse_cli_inputs,
)

import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

# Load environment variables from .env file
load_dotenv()

init(autoreset=True)


def parse_hedge_fund_response(response):
    """Parses a JSON string and returns a dictionary."""
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}\nResponse: {repr(response)}")
        return None
    except TypeError as e:
        print(f"Invalid response type (expected string, got {type(response).__name__}): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error while parsing response: {e}\nResponse: {repr(response)}")
        return None


##### Run the Hedge Fund #####
def run_hedge_fund(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    show_reasoning: bool = False,
    selected_analysts: list[str] = [],
    model_name: str = "llama-3.3-70b-versatile",
    model_provider: str = "Groq",
):
    # Start progress tracking
    progress.start()

    try:
        # Build workflow (default to all analysts when none provided)
        workflow = create_workflow(selected_analysts if selected_analysts else None)
        agent = workflow.compile()

        final_state = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Make trading decisions based on the provided data.",
                    )
                ],
                "data": {
                    "tickers": tickers,
                    "portfolio": portfolio,
                    "start_date": start_date,
                    "end_date": end_date,
                    "analyst_signals": {},
                },
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": model_name,
                    "model_provider": model_provider,
                },
            },
        )

        return {
            "decisions": parse_hedge_fund_response(final_state["messages"][-1].content),
            "analyst_signals": final_state["data"]["analyst_signals"],
        }
    finally:
        # Stop progress tracking
        progress.stop()


def start(state: AgentState):
    """Initialize the workflow with the input message."""
    return state


def create_workflow(selected_analysts=None):
    """Create the workflow with selected analysts."""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    # Get analyst nodes from the configuration
    analyst_nodes = get_analyst_nodes()

    # Default to all analysts if none selected
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())
    # Add selected analyst nodes
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("start_node", node_name)

    # Always add risk and portfolio management
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_manager", portfolio_management_agent)

    workflow.add_edge("start_node", "risk_management_agent")

    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "portfolio_manager")

    workflow.add_edge("risk_management_agent", "portfolio_manager")
    workflow.add_edge("portfolio_manager", END)

    workflow.set_entry_point("start_node")
    return workflow


##### Personalized Investment Advisor Workflow #####

# ── Services (lazy-init, one instance per process) ────────────
_db_manager = None
_user_service = None
_portfolio_service = None
_recommendation_service = None
_memory_service = None
_conversation_service = None


def _get_db():
    global _db_manager
    if _db_manager is None:
        from src.db.connection import DatabaseManager
        _db_manager = DatabaseManager()
        _db_manager.connect()
    return _db_manager


def _get_user_service():
    global _user_service
    if _user_service is None:
        from src.services.user_profile_service import UserProfileService
        _user_service = UserProfileService
    return _user_service


def _get_portfolio_service():
    global _portfolio_service
    if _portfolio_service is None:
        from src.services.portfolio_service import PortfolioService
        _portfolio_service = PortfolioService
    return _portfolio_service


def _get_recommendation_service():
    global _recommendation_service
    if _recommendation_service is None:
        from src.services.recommendation_service import RecommendationService
        _recommendation_service = RecommendationService
    return _recommendation_service


def _get_memory_service():
    global _memory_service
    if _memory_service is None:
        from src.services.memory_service import MemoryService
        _memory_service = MemoryService()
    return _memory_service


def _get_conversation_service():
    global _conversation_service
    if _conversation_service is None:
        from src.services.conversation_memory_service import ConversationMemoryService
        _conversation_service = ConversationMemoryService()
    return _conversation_service


# ── Onboarding Flow ──────────────────────────────────────────

def run_onboarding(
    email: str,
    password_hash: str = None,
    risk_appetite: str = "moderate",
    investment_goal: str = "growth",
    investment_horizon: str = "medium",
    preferred_sectors: list = None,
    excluded_sectors: list = None,
    initial_message: str = None,
) -> dict:
    """User Signup → Store Profile in PostgreSQL → Seed ChromaDB.

    Returns:
        {"user_id": str, "profile": dict, "status": "onboarded"}
    """
    db = _get_db()
    with db.get_session() as session:
        user_service = _get_user_service()(session)
        memory_service = _get_memory_service()

        user = user_service.create_user(email=email, password_hash=password_hash)

        if risk_appetite or investment_goal or investment_horizon or preferred_sectors:
            user_service.update_profile(
                user.id,
                risk_appetite=risk_appetite,
                investment_goal=investment_goal,
                investment_horizon=investment_horizon,
                preferred_sectors=preferred_sectors or [],
                excluded_sectors=excluded_sectors or [],
            )

        profile = user_service.get_profile_dict(user.id)
        memory_service.onboard_user(user_id=user.id, profile=profile, conversation=initial_message)

        return {"user_id": user.id, "profile": profile, "status": "onboarded"}


# ── Recommendation Flow ──────────────────────────────────────

def create_personalized_workflow(selected_analysts=None):
    """Create a workflow that starts with the Personal Financial Advisor,
    then runs analyst agents, risk manager, and portfolio manager.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)
    workflow.add_node("personal_financial_advisor", personal_financial_advisor_agent)

    analyst_nodes = get_analyst_nodes()

    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())

    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)

    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_manager", portfolio_management_agent)

    workflow.add_edge("start_node", "personal_financial_advisor")

    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge("personal_financial_advisor", node_name)

    workflow.add_edge("personal_financial_advisor", "risk_management_agent")

    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "portfolio_manager")

    workflow.add_edge("risk_management_agent", "portfolio_manager")
    workflow.add_edge("portfolio_manager", END)

    workflow.set_entry_point("start_node")
    return workflow


def run_personalized_advisor(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    user_id: str = None,
    user_message: str = None,
    show_reasoning: bool = False,
    selected_analysts: list[str] = None,
    model_name: str = "llama-3.3-70b-versatile",
    model_provider: str = "Groq",
):
    """Full hybrid-memory recommendation flow:

    1. Load user profile from PostgreSQL
    2. Load portfolio holdings from PostgreSQL
    3. Retrieve relevant semantic memories from ChromaDB
    4. Retrieve conversation context from ChromaDB
    5. Build LangGraph state with all of the above
    6. Execute agents
    7. Store recommendation log in PostgreSQL
    8. Store new memory in ChromaDB
    """
    progress.start()

    db = _get_db()

    try:
        with db.get_session() as session:
            user_service = _get_user_service()(session)
            portfolio_svc = _get_portfolio_service()(session)
            rec_service = _get_recommendation_service()(session)
            memory_service = _get_memory_service()
            conversation_service = _get_conversation_service()

            # ── 1. Load user profile from PostgreSQL ──
            user_profile = {}
            if user_id:
                user_profile = user_service.get_profile_dict(user_id)

            # ── 2. Load portfolio from PostgreSQL ──
            user_portfolio = {}
            if user_id:
                holdings = portfolio_svc.get_holdings_dict(user_id)
                target = {t: h["target_allocation"] for t, h in holdings.items()}
                user_portfolio = {
                    "cash": user_profile.get("initial_capital", 100000.0),
                    "margin_requirement": user_profile.get("margin_requirement", 0.0),
                    "positions": {
                        t: {"long": h["shares"], "avg_cost": h["avg_cost"]}
                        for t, h in holdings.items()
                    },
                    "target_allocation": target,
                }

            # ── 1b. Seed default user profile if empty ──
            if not user_profile:
                user_profile = {
                    "risk_appetite": "moderate",
                    "investment_goal": "growth",
                    "investment_horizon": "medium",
                    "preferred_sectors": ["Technology", "Healthcare"],
                    "excluded_sectors": ["Energy"],
                    "preferred_analysts": [],
                    "initial_capital": 100000.0,
                    "margin_requirement": 0.0,
                }

            # ── 2b. Seed dummy portfolio if user has no holdings ──
            if not user_portfolio.get("positions"):
                user_portfolio = {
                    "cash": user_profile.get("initial_capital", 100000.0),
                    "margin_requirement": user_profile.get("margin_requirement", 0.0),
                    "positions": {
                        "AAPL": {"long": 10, "avg_cost": 150.0},
                        "MSFT": {"long": 5, "avg_cost": 350.0},
                        "SPY": {"long": 20, "avg_cost": 450.0},
                    },
                    "target_allocation": {},
                }

            # ── 3. Retrieve relevant memories from ChromaDB ──
            semantic_memories = []
            if user_id and user_message:
                semantic_memories = memory_service.get_relevant_memories(
                    user_id, query=user_message, limit=5
                )

            # ── 4. Retrieve conversation context from ChromaDB ──
            conversation_context = []
            if user_id:
                conversation_context = conversation_service.get_recent_context(
                    user_id, query=user_message or "", limit=5
                )

            # ── 5. Store user message in conversation memory ──
            if user_id and user_message:
                conversation_service.add_message(user_id, "user", user_message)

            # Merge passed portfolio with DB portfolio
            merged_portfolio = {**portfolio, **user_portfolio}
            if not merged_portfolio.get("positions"):
                merged_portfolio["positions"] = user_portfolio.get("positions", {})

            # ── 6. Build LangGraph state and execute ──
            workflow = create_personalized_workflow(
                selected_analysts if selected_analysts is not None else DEFAULT_PERSONALIZED_ANALYSTS
            )
            agent = workflow.compile()

            final_state = agent.invoke({
                "messages": [
                    HumanMessage(
                        content=user_message or "Make trading decisions based on the provided data.",
                    )
                ],
                "data": {
                    "tickers": tickers,
                    "portfolio": merged_portfolio,
                    "start_date": start_date,
                    "end_date": end_date,
                    "analyst_signals": {},
                },
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": model_name,
                    "model_provider": model_provider,
                },
                "user_profile": user_profile,
                "portfolio": user_portfolio,
                "memory": semantic_memories,
                "conversation_context": conversation_context,
                "question": user_message or "",
            })

            # ── 7. Store assistant response in conversation memory ──
            response_text = str(final_state["messages"][-1].content)
            if user_id:
                conversation_service.add_message(user_id, "assistant", response_text)

            # ── 7b. Log recommendation to PostgreSQL ──
            decisions = parse_hedge_fund_response(response_text) or {}
            if user_id and decisions:
                for ticker, decision in decisions.items():
                    if isinstance(decision, dict):
                        rec_service.log_recommendation(
                            user_id=user_id,
                            ticker=ticker,
                            signal=decision.get("action", decision.get("signal", "hold")),
                            confidence=float(decision.get("confidence", 0)),
                            reasoning=decision.get("reasoning", ""),
                            agent_signals=final_state["data"].get("analyst_signals", {}),
                        )

            # ── 8. Log agent analyses to PostgreSQL ──
            analysis_svc = __import__("src.services.analysis_service", fromlist=[""]).AnalysisService(session)
            analyst_signals = final_state["data"].get("analyst_signals", {})
            if user_id and analyst_signals:
                for agent_name, signals in analyst_signals.items():
                    for ticker, signal_data in signals.items():
                        if isinstance(signal_data, dict):
                            raw_reasoning = signal_data.get("reasoning", "")
                            if not isinstance(raw_reasoning, str):
                                raw_reasoning = json.dumps(raw_reasoning, default=str)
                            analysis_svc.log_analysis(
                                user_id=user_id,
                                ticker=ticker,
                                agent_name=agent_name,
                                signal=signal_data.get("action", signal_data.get("signal", "neutral")),
                                confidence=float(signal_data.get("confidence", 0)),
                                reasoning=raw_reasoning,
                                details=json.dumps(signal_data, default=str),
                            )

            # ── 9. Store new memory in ChromaDB ──
            if user_id and user_message and decisions:
                memory_service.store_recommendation_memory(
                    user_id,
                    f"User asked about {', '.join(tickers)}. Recommendation: {json.dumps(decisions)}",
                )

        return {
            "decisions": decisions,
            "analyst_signals": final_state["data"]["analyst_signals"],
            "advisor_context": final_state["data"].get("advisor_context"),
            "user_profile": user_profile,
            "memories_used": semantic_memories,
        }
    finally:
        progress.stop()


if __name__ == "__main__":
    inputs = parse_cli_inputs(
        description="Run the hedge fund trading system",
        require_tickers=True,
        default_months_back=None,
        include_graph_flag=True,
        include_reasoning_flag=True,
    )

    tickers = inputs.tickers
    selected_analysts = inputs.selected_analysts

    portfolio = {
        "cash": inputs.initial_cash,
        "margin_requirement": inputs.margin_requirement,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
            for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
            }
            for ticker in tickers
        },
    }

    result = run_hedge_fund(
        tickers=tickers,
        start_date=inputs.start_date,
        end_date=inputs.end_date,
        portfolio=portfolio,
        show_reasoning=inputs.show_reasoning,
        selected_analysts=inputs.selected_analysts,
        model_name=inputs.model_name,
        model_provider=inputs.model_provider,
    )
    print_trading_output(result)
