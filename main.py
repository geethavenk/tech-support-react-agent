"""
Entry point for the technical support agent: runs the graph, pretty prints the ReAct trace
"""

import sys
from langchain_core.messages import HumanMessage
from agent import app, MAX_ITERATIONS

def run_support_agent(user_issue: str):
    initial_state = {
        "messages": [HumanMessage(content=user_issue)],
        "iteration": 0

    }

    result = app.invoke(
        initial_state,
        config = {
            "run_name": "technical-support-investigation",
            "metadata": {
                "agent_type": "ReAct",
                "max_iterations": MAX_ITERATIONS
            }
        }
    )

    return result

### Pretty printer

def print_execution(result):
    print("\n" + "=" * 70)
    print("TECHNICAL SUPPORT AGENT EXECUTION")
    print("=" * 70)

    for message in result["messages"]:

        message_type = message.__class__.__name__
        print(f"\n[{message_type}]")

        if getattr(message, "content", None):
            print(message.content)

        if getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                args = dict(tool_call["args"])
                reason = args.pop("reason", "(no reason given)")
                print(f"\nTool selected: {tool_call['name']}")
                print(f"Reason: {reason}")
                print(f"Arguments: {args}")

    print("\n" + "=" * 70)
    print(f"Iterations: {result['iteration']}")
    print("=" * 70)


## Example scenarios
SCENARIOS = {
    "api_500": """
My API is returning HTTP 500 errors when I try to create an order.
The request sometimes takes several seconds before returning the
500 error.
""",
    "slow": """
Our application has become very slow. Users report that pages
take several seconds to load.
""",
    "login": """
I cannot log into the application. My login keeps failing.
""",
    "database": """
The application cannot connect to the database and database
connections appear to be timing out.
""",
    "docker": """
Our Docker container keeps restarting every few minutes.
""",
}
 
 
def run_scenario(name: str):
    issue = SCENARIOS[name]
    result = run_support_agent(issue)
    print_execution(result)
  

## Interactive CLI

def interactive_mode():
    print("\nTechnical Support ReAct Agent")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("Customer: ")

        if user_input.lower().strip() == "exit":
            break

        try:
            result = run_support_agent(user_input)
            final_message = result["messages"][-1]
            print("\nAgent:")
            print(final_message.content)
            print()

        except Exception as e:
            print("\nAgent error:", str(e))


if __name__ == "__main__":
    if "--interactive" in sys.argv:
        interactive_mode()
    else:
        run_scenario("login")   


                          

