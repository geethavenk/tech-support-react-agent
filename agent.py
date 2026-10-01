import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    ToolMessage,
    AIMessage
)

from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from tools import tools, tools_by_name

# Environment
load_dotenv()

os.environ.setdefault(
    "LANGSMITH_PROJECT",
    "technical-support-react-agent"
)

## config
MAX_ITERATIONS = 6
MODEL_NAME = "gpt-4.1"

# LLM

llm = ChatOpenAI(
    model = MODEL_NAME, 
    api_key=os.environ["API_KEY"],
    base_url=os.environ["BASE_URL"],
    temperature=0, 
    )

# Every tool schema sent to the model gets an extra required "reason" argument
REASON_FIELD = {
    "type": "string",
    "description": (
        "1-2 sentences: what the evidence so far tells you and why this "
        "tool is the right next step."
    ),
}

def with_reason(tool) -> dict:
    schema = convert_to_openai_tool(tool)
    params = schema["function"]["parameters"]
    params["properties"] = {"reason": REASON_FIELD, **params.get("properties", {})}
    params["required"] = ["reason", *params.get("required", [])]
    return schema

llm_with_tools = llm.bind_tools([with_reason(t) for t in tools])

# State

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iteration: int

SYSTEM_PROMPT = """
You are a Technical Support Agent for a software company.
 
Your job is to investigate customer technical problems and provide
a concise, evidence-based troubleshooting resolution.
 
Available tools:
 
- check_app_status
- check_server_logs
- check_db_status
- check_api_health
- search_internal_docs
 
IMPORTANT BEHAVIOR:
 
1. Analyze the customer's problem first.
 
2. Select only tools that are relevant to the reported issue.
 
3. Do NOT call unnecessary tools.
 
4. Investigate iteratively when additional evidence is needed.
 
5. Use tool results to decide what tool should be called next.
 
6. Stop investigating when you have enough evidence to determine
the likely root cause and provide a useful resolution.
 
7. Do not repeatedly call the same tool unless there is a clear
reason to do so.
 
8. If the issue is a password-reset or login question, do not
automatically inspect database health.
 
9. If an API returns HTTP 500, investigate the API and relevant
dependencies rather than blindly checking every available tool.
 
10. Never invent information that was not provided by the user
or returned by a tool.
 
11. At the end, provide:
    - Problem
    - Investigation performed
    - Likely root cause
    - Recommended action
    - Whether escalation is required
 
12. If evidence is insufficient, explicitly say what is unknown.

13. Only act on evidence that relates to the reported issue. For
example, errors from /api/orders do not explain a login failure, so
they are not a reason to inspect the database.
 

"""

# once the iteration cap is hit -- this message is shown to the model to force a wrap-up answer
FINALIZE_INSTRUCTION = SystemMessage(
    content=(
        "Maximum investigation iterations reached. Do not call any more "
        "tools. Using ONLY the evidence already collected above, provide "
        "your best possible conclusion in the required format (Problem, "
        "Investigation performed, Likely root cause, Recommended action, "
        "Escalation needed). Explicitly note anything that remains "
        "unknown because the investigation was cut short."
    )
)

## Agent node

def agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    iteration = state.get("iteration", 0)

    if iteration >= MAX_ITERATIONS:
        # wrap-up anser
        try:
            response = llm.invoke(
                [SystemMessage(content=SYSTEM_PROMPT), *messages, FINALIZE_INSTRUCTION]
                )
        except Exception as e:
            response = AIMessage(
                content=(
                    "Reached the investigation limit and also hit an error"
                    f"while summarizing ({e}). Please escalate to a human engineer with the transcript collected so far."

                )
            )

        return {
            "messages": [response],
            "iteration": iteration,

        }

    try:
        response = llm_with_tools.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *messages]
        )
    except Exception as e:
        response = AIMessage(
            content=(
                f"I hit an internal error while reasoning about this issue "
                f"({type(e).__name__}: {e}). Please try again, or "
                "excalate to a human engineer if this persists."
            )
        ) 

    return {
        "messages": [response],
        "iteration": iteration + 1,
    }   

## Tool node

def safe_tool_node(state: AgentState):
    """
    Executes every tool call requested by the last message"""

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []

    result_messages = []

    for call in tool_calls:
        try:
            tool_fn = tools_by_name[call["name"]]
            args = {k: v for k, v in call["args"].items() if k != "reason"}
            output = tool_fn.invoke(args)
            content = str(output)
        except Exception as e:
            content = (
                "Tool execution failed. "
                "Do not assume the tool result."
                f"Error: {str(e)}"
            )   

        result_messages.append(
            ToolMessage(content=content, tool_call_id=call["id"])
        ) 

    return {
        "messages": result_messages,
        "iteration": state["iteration"]

    }

# Conditional routing

def should_continue(state: AgentState):
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tools"

    return "end"

# Build graph

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", safe_tool_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    graph.add_edge("tools", "agent")

    return graph.compile()

app = build_graph()