# AI Agent with Real-Time Web Search

An intelligent AI agent with calculator, real-time web search capabilities, and robust fallback mechanisms.

## 🎯 Features

- ✅ **Calculator Tool** - Evaluates mathematical expressions safely
- ✅ **Real-Time Web Search** - Fetches live data from the internet via DuckDuckGo API
- ✅ **LLM Fallback** - Uses AI knowledge when web search fails
- ✅ **Output Validation** - Checks result quality and triggers fallbacks
- ✅ **Execution Tracing** - Visual logs of decision-making process
- ✅ **Failure Simulation** - Test error handling and fallback logic

## 🚀 Quick Start

### Installation

```bash
cd 9
pip install -r requirements.txt
```

### Setup Environment

Create `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

### Run Web Interface

```bash
python app.py
```

Visit: http://127.0.0.1:5000

### Run CLI Test

```bash
python test_agent.py
```

## 🔍 How Web Search Works

The search tool uses a **3-tier fallback strategy**:

### 1. Real-Time Web Search (Primary)
- Uses **DuckDuckGo Instant Answer API**
- Fetches live data from the internet
- No API key required
- Best for: Facts, definitions, Wikipedia-style content

### 2. LLM Knowledge (Secondary)
- Uses Groq AI (llama-3.3-70b-versatile)
- Provides information from training data
- Knowledge cutoff: December 2023
- Best for: General knowledge, explanations, concepts

### 3. Static Fallback (Tertiary)
- Local database with basic facts
- Used when both above methods fail
- Limited coverage

## 📋 Search Capabilities

### ✅ Works Well For:
- **Definitions**: "What is Python programming?"
- **Facts**: "Tunisia information"
- **Concepts**: "Explain artificial intelligence"
- **Historical data**: "When was the Eiffel Tower built?"

### ⚠️ Limited For:
- **Breaking news**: DuckDuckGo API has limited news coverage
- **Real-time data**: Weather, stock prices, live events
- **Recent events**: Post-2023 information relies on LLM training

### 💡 Recommendation for True Real-Time News:
For comprehensive real-time news and current events, consider integrating:
- **NewsAPI** (newsapi.org) - Requires API key
- **Tavily API** (tavily.com) - AI-powered search API
- **SerpAPI** (serpapi.com) - Google Search results
- **Bing Search API** - Microsoft's search API

## 🛠️ Technical Details

### Search Flow

```
User Query
    ↓
1. Try DuckDuckGo API (real-time web)
    ↓ (if fails or low quality)
2. Try Groq LLM (training data)
    ↓ (if fails)
3. Static fallback database
```

### Example Queries

```python
# Math calculation
"What is sqrt(144) + 5?"

# Web search (works well)
"Search Tunisia"
"What is artificial intelligence?"
"Python programming language"

# News (limited - uses LLM knowledge)
"latest hantavirus news"
"current AI technology trends"

# Direct conversation
"Who are you?"
"Hello"
```

## 📊 Web Interface Features

### Left Panel: Controls
- **API Key Input**: Enter Groq API key (or leave blank for mock mode)
- **Failure Simulator**: Force tool failures to test fallback logic
- **Test Triggers**: Pre-configured queries for testing

### Center Panel: Chat
- Real-time conversation with the agent
- Visual indicators for routing (Direct/Tool/Fallback)
- Typing indicators during processing

### Right Panel: Execution Trace
- Live logs of agent decision-making
- Shows routing, execution, validation stages
- Color-coded status indicators

## 🔧 Customization

### Add Better Search API

To integrate NewsAPI for real-time news:

```python
# In agent.py, add to SearchTool class:

def _search_newsapi(self, query: str) -> Optional[Dict[str, Any]]:
    """Search using NewsAPI for current news"""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return None
    
    try:
        response = requests.get(
            'https://newsapi.org/v2/everything',
            params={
                'q': query,
                'apiKey': api_key,
                'sortBy': 'publishedAt',
                'pageSize': 3
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            if articles:
                results = []
                for article in articles[:3]:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    url = article.get('url', '')
                    published = article.get('publishedAt', '')
                    source = article.get('source', {}).get('name', '')
                    
                    results.append({
                        'title': title,
                        'description': description,
                        'url': url,
                        'published': published,
                        'source': source
                    })
                
                return {
                    'text': self._format_news_results(results),
                    'source': 'NewsAPI',
                    'url': '',
                    'type': 'news'
                }
        
        return None
    except Exception:
        return None

def _format_news_results(self, articles: List[Dict]) -> str:
    """Format news articles into readable text"""
    formatted = []
    for i, article in enumerate(articles, 1):
        text = f"{i}. {article['title']}\n"
        text += f"   {article['description']}\n"
        text += f"   Source: {article['source']} | Published: {article['published']}\n"
        text += f"   URL: {article['url']}"
        formatted.append(text)
    
    return "\n\n".join(formatted)

# Update run() method to try NewsAPI first for news queries:
def run(self, args: Dict[str, Any], **kwargs) -> str:
    query = args.get("query", "").strip()
    
    # Check if query is news-related
    news_keywords = ['news', 'latest', 'recent', 'current', 'today']
    is_news_query = any(keyword in query.lower() for keyword in news_keywords)
    
    if is_news_query:
        news_results = self._search_newsapi(query)
        if news_results:
            # Process news results...
            pass
    
    # Continue with existing logic...
```

### Environment Variables

Add to `.env`:
```
GROQ_API_KEY=your_groq_key
NEWS_API_KEY=your_newsapi_key  # Optional
```

## 📝 Testing

### Test Real-Time Search
```bash
python test_search.py
```

### Test Agent Logic
```bash
python test_agent.py
```

### Test Web Interface
```bash
python app.py
# Open browser to http://127.0.0.1:5000
```

## 🎓 Understanding the Agent

### Routing Logic
The agent analyzes each query and decides:
- **Calculator**: Math expressions, calculations
- **Search**: Facts, definitions, information lookup
- **Direct**: Greetings, conversational queries

### Validation Logic
After tool execution, the agent validates:
- Output is not empty
- Output length is sufficient (>25 chars for search)
- Output is relevant to the query

If validation fails → Triggers LLM fallback

### Fallback Logic
When tools fail or return low-quality results:
1. Agent acknowledges the tool issue
2. Uses LLM's internal knowledge
3. Provides best possible answer
4. Mentions the limitation

## 🚨 Current Limitations

1. **News Coverage**: DuckDuckGo API has limited real-time news
2. **Knowledge Cutoff**: LLM training data ends December 2023
3. **No Authentication**: DuckDuckGo API is free but rate-limited
4. **Search Quality**: Best for facts/definitions, not breaking news

## 💡 Recommendations

For production use with comprehensive real-time search:

1. **Integrate NewsAPI** for current news and events
2. **Add Tavily API** for AI-powered web search
3. **Use SerpAPI** for Google Search results
4. **Implement caching** to reduce API calls
5. **Add rate limiting** to prevent abuse

## 📦 Dependencies

```
flask           # Web framework
groq            # LLM API client
python-dotenv   # Environment variables
requests        # HTTP client for web search
```

## 🔗 Useful Links

- **DuckDuckGo API**: https://duckduckgo.com/api
- **NewsAPI**: https://newsapi.org
- **Tavily API**: https://tavily.com
- **Groq API**: https://groq.com

---

**Built with Flask + Groq AI + DuckDuckGo API 🚀**
