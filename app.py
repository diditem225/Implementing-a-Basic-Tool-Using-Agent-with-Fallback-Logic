import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from agent import Agent

# Load environment variables (e.g. GROQ_API_KEY) from .env file if present
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route("/")
def index():
    # Render the main dashboard page
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        
        if not query:
            return jsonify({"error": "Query cannot be empty"}), 400

        # Get API key from request payload or environment variable
        api_key = data.get("groq_api_key", "").strip()
        if not api_key:
            api_key = os.environ.get("GROQ_API_KEY", "").strip()
            
        if not api_key:
            api_key = None  # Will trigger Mock Mode in agent

        # Parse developer mode failure override options
        force_calc_timeout = bool(data.get("force_calc_timeout", False))
        force_search_error = bool(data.get("force_search_error", False))

        # Initialize agent with the provided key (or None)
        agent = Agent(api_key=api_key)
        
        # Execute agent workflow
        answer, trace = agent.run_agent(
            query=query,
            force_calc_timeout=force_calc_timeout,
            force_search_error=force_search_error
        )
        
        return jsonify({
            "answer": answer,
            "trace": trace,
            "mock_mode": agent.is_mock_mode()
        })
        
    except Exception as e:
        return jsonify({
            "error": "Internal Agent Error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    # Start the Flask development server on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
