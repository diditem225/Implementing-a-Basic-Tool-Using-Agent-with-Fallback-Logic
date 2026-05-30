from agent import Agent
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
agent = Agent(api_key=api_key)

print("Testing Improved Routing")
print("=" * 80)

test_queries = [
    ("What is sqrt(144) + 5?", "calculator"),
    ("Calculate 12 * 8", "calculator"),
    ("ln(9999999999)", "calculator"),
    ("What is the limit of ln(2x)/e^(x²)*sin(x/2) when x goes to +infinity?", "search"),
    ("Find the derivative of x^2 + 3x", "search"),
    ("What is the integral of sin(x)?", "search"),
    ("latest hantavirus news", "search"),
    ("Who are you?", "direct"),
]

for query, expected_tool in test_queries:
    print(f"\nQuery: {query}")
    print(f"Expected: {expected_tool}")
    
    answer, trace = agent.run_agent(query)
    
    routing_step = next((step for step in trace if step['stage'] == 'ROUTING'), None)
    if routing_step:
        details = routing_step.get('details', {})
        actual_tool = details.get('selected_tool', 'unknown')
        print(f"Actual: {actual_tool}")
        
        if actual_tool == expected_tool:
            print("✅ CORRECT")
        else:
            print("❌ WRONG")
    
    print("-" * 80)
