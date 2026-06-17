from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal
import json

from src.graph.state import AgentState, show_agent_reasoning
from src.utils.llm import call_llm
from src.utils.progress import progress


class RAGResponse(BaseModel):
    signal: Literal["informational", "educational", "clarification"]
    confidence: int = Field(description="Confidence 0-100")
    reasoning: str = Field(description="Answer to the user's question")
    related_topics: list[str] = Field(default_factory=list)


def rag_agent(state: AgentState, agent_id: str = "rag_agent"):
    """Answers general financial education questions with clear explanations."""
    question = state.get("question", "")
    user_profile = state.get("user_profile", {})
    conversation_context = state.get("conversation_context", [])

    progress.update_status(agent_id, None, "Researching answer")

    context_str = "\n".join(conversation_context[-3:]) if conversation_context else "None"

    template = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful financial education assistant. Answer the user's "
            "question clearly and concisely. Use simple language and real-world examples. "
            "Return JSON only.",
        ),
        (
            "human",
            "User question: {question}\n"
            "User profile: {profile}\n"
            "Recent conversation: {context}\n\n"
            'Return: {{"signal": "informational"|"educational"|"clarification", '
            '"confidence": int, "reasoning": "...", "related_topics": [...]}}',
        ),
    ])

    prompt = template.invoke({
        "question": question,
        "profile": json.dumps(user_profile) if user_profile else "None",
        "context": context_str,
    })

    def default():
        return RAGResponse(
            signal="informational", confidence=0,
            reasoning="I'm not sure about that. Please consult a financial advisor for personalized advice.",
            related_topics=[],
        )

    output: RAGResponse = call_llm(
        prompt=prompt,
        pydantic_model=RAGResponse,
        agent_name=agent_id,
        state=state,
        default_factory=default,
    )

    response_data = {
        "rag_response": {
            "signal": output.signal,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
            "related_topics": output.related_topics,
        }
    }

    state["data"]["analyst_signals"][agent_id] = response_data

    message = HumanMessage(content=json.dumps(response_data), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(response_data, agent_id)

    progress.update_status(agent_id, None, "Done")

    return {"messages": state["messages"] + [message], "data": state["data"]}
