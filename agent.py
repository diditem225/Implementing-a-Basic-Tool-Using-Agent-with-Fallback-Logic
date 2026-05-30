import os
import math
import re
import time
import json
import requests
from typing import Dict, Any, Tuple, Optional, List
from groq import Groq
from serpapi import GoogleSearch

# ==========================================
# TOOL BASE & IMPLEMENTATIONS
# ==========================================

class Tool:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def run(self, args: Dict[str, Any], **kwargs) -> str:
        raise NotImplementedError("Each tool must implement its run method.")


class CalculatorTool(Tool):
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Evaluates mathematical expressions. Use this for math and arithmetic calculations. Argument should be 'expression' (e.g., 'sqrt(144) + 5')."
        )

    def run(self, args: Dict[str, Any], **kwargs) -> str:
        # Check for simulated timeout
        if kwargs.get("force_timeout", False):
            time.sleep(1.5)  # Simulate delay
            raise TimeoutError("Calculator tool execution timed out (limit 1.0s exceeded).")

        expression = args.get("expression", "")
        if not expression:
            raise ValueError("No expression provided to the calculator.")

        # Sanitization: allow only numbers, math operators, spaces, parentheses, and math functions
        # This prevents execution of arbitrary code via eval.
        allowed_chars = re.compile(r'^[0-9+\-*/().\s%]+$')
        allowed_math_funcs = ["sqrt", "sin", "cos", "tan", "log", "exp", "pi", "e", "pow"]
        
        # Strip out valid math functions to check if any forbidden text remains
        expr_check = expression
        for func in allowed_math_funcs:
            expr_check = expr_check.replace(func, "")
            
        if not allowed_chars.match(expr_check):
            raise ValueError(f"Unsafe characters or invalid functions detected in expression: '{expression}'")

        # Prepare evaluation environment
        eval_env = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "exp": math.exp,
            "pow": math.pow,
            "pi": math.pi,
            "e": math.e,
            "__builtins__": {}  # Empty builtins for security
        }

        try:
            # Safely evaluate
            result = eval(expression, eval_env)
            return str(result)
        except ZeroDivisionError:
            raise ArithmeticError("Division by zero is mathematically undefined.")
        except Exception as e:
            raise RuntimeError(f"Failed to evaluate math expression. Error: {str(e)}")


class SearchTool(Tool):
    def __init__(self, groq_client=None):
        super().__init__(
            name="search",
            description="Searches the internet in real-time for current information, news, facts, and data using Google Search. Argument should be 'query' (e.g., 'latest hantavirus news', 'current weather', 'recent events')."
        )
        self.groq_client = groq_client
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self._fallback_db = {
            "tunisia": (
                "Tunisia is a North African country bordering the Mediterranean Sea and the Sahara Desert. "
                "The capital, Tunis, features the Bardo Museum with its famous Roman mosaics, and the ancient ruins of Carthage lie nearby. "
                "Tunisia is known for its rich olive oil production, historic medinas, and beautiful coastal towns like Sidi Bou Said."
            ),
            "agent": (
                "An AI agent is an autonomous software entity that can perceive its environment, make decisions, "
                "and use tools (like calculators, web search, or database queries) to achieve specific goals defined by a user."
            ),
            "404": "Error: Page not found. Search index failure."
        }

    def _search_serpapi(self, query: str) -> Optional[Dict[str, Any]]:
        """Performs real-time web search using SerpAPI (Google Search)"""
        if not self.serpapi_key or self.serpapi_key == "your_serpapi_key_here":
            return None
            
        try:
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "engine": "google",
                "num": 5
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            search_results = []
            
            answer_box = results.get("answer_box", {})
            if answer_box:
                answer = answer_box.get("answer") or answer_box.get("snippet")
                if answer:
                    search_results.append({
                        'type': 'answer_box',
                        'content': answer,
                        'source': answer_box.get("title", "Google Answer Box")
                    })
            
            knowledge_graph = results.get("knowledge_graph", {})
            if knowledge_graph:
                description = knowledge_graph.get("description")
                if description:
                    search_results.append({
                        'type': 'knowledge_graph',
                        'content': description,
                        'source': knowledge_graph.get("title", "Knowledge Graph")
                    })
            
            organic_results = results.get("organic_results", [])
            for result in organic_results[:3]:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                link = result.get("link", "")
                
                if snippet:
                    search_results.append({
                        'type': 'organic',
                        'title': title,
                        'content': snippet,
                        'url': link
                    })
            
            if search_results:
                return {
                    'results': search_results,
                    'source': 'Google Search (SerpAPI)',
                    'query': query
                }
            
            return None
            
        except Exception as e:
            print(f"SerpAPI Error: {e}")
            return None

    def _format_search_results(self, search_data: Dict[str, Any]) -> str:
        """Format search results into readable text"""
        results = search_data.get('results', [])
        formatted = ["[LIVE WEB SEARCH - Google]\n"]
        
        for i, result in enumerate(results, 1):
            result_type = result.get('type', 'organic')
            
            if result_type == 'answer_box':
                formatted.append(f"📌 Quick Answer:")
                formatted.append(f"{result.get('content', '')}")
                formatted.append(f"Source: {result.get('source', 'Google')}\n")
                
            elif result_type == 'knowledge_graph':
                formatted.append(f"📚 Knowledge Graph:")
                formatted.append(f"{result.get('content', '')}")
                formatted.append(f"Source: {result.get('source', 'Google')}\n")
                
            elif result_type == 'organic':
                formatted.append(f"{i}. {result.get('title', 'Result')}")
                formatted.append(f"   {result.get('content', '')}")
                if result.get('url'):
                    formatted.append(f"   🔗 {result.get('url')}\n")
        
        return "\n".join(formatted)

    def _search_with_llm(self, query: str, web_results: Optional[Dict[str, Any]] = None) -> str:
        """Uses LLM to enhance web results or provide fallback"""
        if not self.groq_client:
            return None
            
        try:
            if web_results:
                formatted_results = self._format_search_results(web_results)
                
                system_prompt = (
                    "You are a search result synthesizer. The user searched for information and we found real-time results from Google. "
                    "Your job is to synthesize these results into a clear, comprehensive answer. "
                    "Include key facts, dates, sources, and URLs. Keep the [LIVE WEB SEARCH - Google] header. "
                    "Organize the information logically and make it easy to read."
                )
                user_message = f"Query: {query}\n\nGoogle Search Results:\n{formatted_results}\n\nSynthesize this into a clear, informative response:"
            else:
                system_prompt = (
                    "You are a search assistant. Real-time web search is unavailable. "
                    "Provide the best information from your training data (cutoff: December 2023). "
                    "Start with '[LLM KNOWLEDGE - Training Data]' and clearly mention your knowledge cutoff. "
                    "Include facts, dates, and context. Be honest about limitations."
                )
                user_message = f"Search query: {query}\n\nProvide information from your training data:"
            
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=600
            )
            
            result = response.choices[0].message.content.strip()
            return result if result and len(result) > 25 else None
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return None

    def run(self, args: Dict[str, Any], **kwargs) -> str:
        if kwargs.get("force_error", False):
            raise ConnectionError("Search API failed: HTTP 503 Service Unavailable (DNS Resolution Failure)")

        query = args.get("query", "").strip()
        if not query:
            return ""

        if "404" in query.lower() or "error" in query.lower():
            raise RuntimeError("External Search API returned a 404/500 error code during index scanning.")

        serpapi_results = self._search_serpapi(query)
        
        if serpapi_results and serpapi_results.get('results'):
            if self.groq_client:
                enhanced = self._search_with_llm(query, serpapi_results)
                if enhanced:
                    return enhanced
            
            return self._format_search_results(serpapi_results)
        
        if self.groq_client:
            llm_result = self._search_with_llm(query, None)
            if llm_result:
                return llm_result
        
        return self._fallback_search(query)

    def _fallback_search(self, query: str) -> str:
        """Fallback to static database if all else fails"""
        query_lower = query.lower()
        matches = []
        for key, value in self._fallback_db.items():
            if key in query_lower or query_lower in key:
                matches.append(value)

        if matches:
            return " | ".join(matches)
        
        return "No results."


# ==========================================
# AGENT RUNTIME
# ==========================================

class Agent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = Groq(api_key=api_key) if api_key else None
        self.tools = {
            "calculator": CalculatorTool(),
            "search": SearchTool(groq_client=self.client)
        }

    def is_mock_mode(self) -> bool:
        return self.client is None

    def route_query(self, query: str) -> Dict[str, Any]:
        """
        Classifies the query and extracts parameters.
        Returns: {"tool": "calculator" | "search" | "direct", "args": {...}}
        """
        if self.is_mock_mode():
            return self._mock_route_query(query)

        # Groq-based LLM Router
        system_prompt = (
            "You are the routing system of an AI Agent. Your job is to classify the user query "
            "and determine if it requires a tool, or can be answered directly.\n\n"
            "Available tools:\n"
            "1. calculator: Use this for arithmetic and math computations (e.g. square roots, products, additions, expressions).\n"
            "   Required arg keys: {'expression': 'string math expression to evaluate'}\n"
            "2. search: Use this for factual questions, explanations, definitions, and general knowledge (e.g. countries, weather, concepts).\n"
            "   Required arg keys: {'query': 'string search query'}\n"
            "3. direct: Use this if the query is a simple greeting, conversational question about yourself, or doesn't need external data.\n"
            "   Required arg keys: {}\n\n"
            "Return ONLY a JSON object in this format:\n"
            '{"tool": "tool_name", "args": {"arg_name": "arg_value"}}'
        )

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # Fallback to local mock routing on Groq error
            return self._mock_route_query(query)

    def _mock_route_query(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower().strip()
        
        # Check for Calculator triggers
        math_indicators = ["sqrt", "+", "-", "*", "/", "%", "pow", "math", "evaluate", "calculate"]
        if any(ind in query_lower for ind in math_indicators) or re.search(r'\d+\s*[+\-*/]\s*\d+', query_lower):
            # Try to extract the mathematical expression
            expr = query
            for term in ["calculate", "what is", "evaluate", "equal to", "?"]:
                expr = expr.lower().replace(term, "")
            expr = expr.strip()
            return {"tool": "calculator", "args": {"expression": expr}}

        # Check for conversational triggers
        conversational_indicators = ["who are you", "hello", "hi ", "hey", "tell me a joke", "what is your name"]
        if any(ind in query_lower for ind in conversational_indicators):
            return {"tool": "direct", "args": {}}

        # Default to Search for everything else requiring lookup
        return {"tool": "search", "args": {"query": query}}

    def generate_direct_response(self, query: str) -> str:
        """Generates response directly from LLM without using tools."""
        if self.is_mock_mode():
            return self._mock_direct_response(query)

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful, conversational AI assistant. Answer the user query directly."},
                    {"role": "user", "content": query}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception:
            return self._mock_direct_response(query)

    def _mock_direct_response(self, query: str) -> str:
        query_lower = query.lower()
        if "who are you" in query_lower or "your name" in query_lower:
            return "I am an AI agent demonstrating tool usage and robust fallback routing, running in Mock Mode."
        if "hello" in query_lower or "hi" in query_lower or "hey" in query_lower:
            return "Hello! How can I assist you today? Feel free to ask me math questions or query facts."
        return "I am an AI assistant. This is a direct conversational response generated without querying any external tools."

    def generate_fallback_response(self, query: str, tool_name: str, failure_reason: str) -> str:
        """LLM answers directly based on internal knowledge after tool failure/low confidence."""
        if self.is_mock_mode():
            return self._mock_fallback_response(query, tool_name, failure_reason)

        system_prompt = (
            f"You are an AI Agent. While trying to answer the user query, the tool '{tool_name}' failed or returned low confidence.\n"
            f"Reason: {failure_reason}\n\n"
            "You must answer the query directly using your own internal knowledge. "
            "Acknowledge the tool issue politely in your response, but still provide the best possible answer."
        )

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception:
            return self._mock_fallback_response(query, tool_name, failure_reason)

    def _mock_fallback_response(self, query: str, tool_name: str, failure_reason: str) -> str:
        intro = f"[Notice: Tool '{tool_name}' failed/rejected. Fallback logic triggered. Reason: {failure_reason}]\n\n"
        query_lower = query.lower()
        
        if "tunisia" in query_lower:
            return intro + (
                "Although the search tool is unavailable right now, my fallback memory knows that "
                "Tunisia is a beautiful Mediterranean nation in North Africa. It is famous for Carthage, "
                "its olive trees, Roman ruins, and its capital Tunis."
            )
        if "sqrt" in query_lower or "144" in query_lower:
            return intro + (
                "The math calculation tool timed out, but I can compute this directly: "
                "The square root of 144 is 12, and 12 + 5 is 17."
            )
        return intro + f"I encountered an issue executing the '{tool_name}' tool. Relying on my offline database, here is the answer: I received your request for '{query}' but my specific information is limited on this topic without live tools."

    def generate_final_with_tool(self, query: str, tool_name: str, tool_output: str) -> str:
        """Formats the raw tool output into a helpful human response."""
        if self.is_mock_mode():
            return f"According to the {tool_name} tool, the result is: {tool_output}"

        system_prompt = (
            f"You are an AI Agent. You successfully ran the tool '{tool_name}' and got the following output:\n"
            f"'{tool_output}'\n\n"
            "Please format this output into a natural, helpful, and concise response to the user's query."
        )

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception:
            return f"According to the {tool_name} tool, the result is: {tool_output}"

    def run_agent(self, query: str, force_calc_timeout: bool = False, force_search_error: bool = False) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Runs the full agent cycle: Routing -> Tool Exec -> Validation -> Generation / Fallback.
        Returns: (final_answer, execution_trace_logs)
        """
        trace = []
        start_time = time.time()
        
        def log_step(stage: str, status: str, details: Any):
            trace.append({
                "stage": stage,
                "status": status,
                "timestamp": round(time.time() - start_time, 4),
                "details": details
            })

        log_step("INITIALIZATION", "SUCCESS", {
            "query": query, 
            "mode": "Groq LLM" if not self.is_mock_mode() else "Local Mock Mode",
            "api_key_provided": self.api_key is not None
        })

        # 1. Routing
        try:
            routing_decision = self.route_query(query)
            tool_name = routing_decision.get("tool", "direct")
            tool_args = routing_decision.get("args", {})
            log_step("ROUTING", "SUCCESS", {
                "selected_tool": tool_name,
                "extracted_arguments": tool_args
            })
        except Exception as e:
            tool_name = "direct"
            tool_args = {}
            log_step("ROUTING", "FAILURE", {
                "error": str(e),
                "action": "Fallback to direct generation"
            })

        # 2. Execution
        if tool_name == "direct":
            log_step("EXECUTION", "BYPASSED", {"reason": "Query routed for direct reasoning."})
            answer = self.generate_direct_response(query)
            log_step("GENERATION", "DIRECT", {"answer": answer})
            return answer, trace

        # Attempt Tool Call
        tool = self.tools.get(tool_name)
        if not tool:
            # Fallback if router selected an invalid tool
            reason = f"Tool '{tool_name}' is not registered in this agent."
            log_step("EXECUTION", "ERROR", {"error": reason})
            answer = self.generate_fallback_response(query, tool_name, reason)
            log_step("GENERATION", "FALLBACK", {"answer": answer, "reason": reason})
            return answer, trace

        try:
            # Inject simulated triggers
            tool_kwargs = {}
            if tool_name == "calculator" and force_calc_timeout:
                tool_kwargs["force_timeout"] = True
            if tool_name == "search" and force_search_error:
                tool_kwargs["force_error"] = True

            log_step("EXECUTION", "RUNNING", {"tool": tool_name, "args": tool_args})
            raw_output = tool.run(tool_args, **tool_kwargs)
            log_step("EXECUTION", "SUCCESS", {"raw_output": raw_output})

        except Exception as e:
            # Execution Failed -> Fallback
            error_message = str(e)
            log_step("EXECUTION", "FAILED", {"error": error_message})
            
            # Call fallback LLM reasoning
            answer = self.generate_fallback_response(query, tool_name, f"Execution failed: {error_message}")
            log_step("GENERATION", "FALLBACK", {"answer": answer, "reason": f"Tool execution failed ({error_message})"})
            return answer, trace

        # 3. Output Validation / Confidence Assessment
        # Confidence Check Rules:
        # - Empty output
        # - Search results under 25 chars are considered unhelpful / low confidence
        is_valid = True
        validation_reason = ""
        
        if not raw_output or len(raw_output.strip()) == 0:
            is_valid = False
            validation_reason = "Tool returned an empty result."
        elif tool_name == "search" and (len(raw_output) < 25 or raw_output.strip().lower() == "no results."):
            is_valid = False
            validation_reason = f"Low confidence: Search output is too short or irrelevant ('{raw_output}')"

        if not is_valid:
            log_step("VALIDATION", "FAILED", {"reason": validation_reason, "output": raw_output})
            # Fallback to LLM reasoning due to low confidence output
            answer = self.generate_fallback_response(query, tool_name, validation_reason)
            log_step("GENERATION", "FALLBACK", {"answer": answer, "reason": f"Validation failed ({validation_reason})"})
            return answer, trace

        log_step("VALIDATION", "PASSED", {"confidence": "HIGH", "output": raw_output})

        # 4. Generate response with tool data
        try:
            answer = self.generate_final_with_tool(query, tool_name, raw_output)
            log_step("GENERATION", "TOOL_SUCCESS", {"answer": answer})
        except Exception as e:
            # If final formatting fails for some reason, use the raw tool output
            answer = f"The {tool_name} returned: {raw_output}"
            log_step("GENERATION", "TOOL_SUCCESS_RAW", {"answer": answer, "formatting_error": str(e)})

        return answer, trace
