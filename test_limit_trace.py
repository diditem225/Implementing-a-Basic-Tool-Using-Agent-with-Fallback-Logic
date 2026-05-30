from agent import Agent
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
agent = Agent(api_key=api_key)

query = "What is the limit of ln(2x)/e^(x²)*sin(x/2) when x goes to +infinity?"

print("Testing Limit Query - Full Trace")
print("=" * 80)
print(f"Query: {query}")
print("=" * 80)

answer, trace = agent.run_agent(query)

print("\nEXECUTION TRACE:")
for step in trace:
    stage = step.get('stage', 'UNKNOWN')
    status = step.get('status', 'UNKNOWN')
    print(f"\n{stage}: {status}")
    if step.get('details'):
        print(f"  Details: {step['details']}")

print("\n" + "=" * 80)
print("FINAL ANSWER:")
print("=" * 80)
print(answer)
