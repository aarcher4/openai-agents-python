# Visual Examples Overview

## 🎯 What Each Example Actually Does

### Basic Examples - Start Here!

#### `hello_world.py` ⭐
**What it does:**
```
You ask: "Tell me about recursion"
Agent responds: A haiku about recursion
```
**Learn:** Basic agent creation and running

---

#### `tools.py` ⭐
**What it does:**
```
You ask: "What's the weather in Tokyo?"
Agent thinks: "I need to call get_weather function"
Agent calls: get_weather("Tokyo")
Agent responds: "The weather in Tokyo is sunny with wind, 14-20°C"
```
**Learn:** How agents use tools to get information

---

#### `stream_text.py` ⭐
**What it does:**
```
Agent response appears word-by-word in real-time:
"The..." 
"The capital..." 
"The capital of..." 
"The capital of France..."
"The capital of France is Paris."
```
**Learn:** Real-time streaming responses

---

### Agent Patterns - Core Workflows

#### `deterministic.py` ⭐⭐
**What it does:**
```
Step 1: Outline Agent creates story outline
  → Output: "1. Introduction 2. Middle 3. End"
  
Step 2: Writer Agent writes the story using the outline
  → Output: Full story based on outline
  
Step 3: Editor Agent reviews and improves the story
  → Output: Polished final version
```
**Learn:** Sequential agent workflows

---

#### `routing.py` ⭐⭐
**What it does:**
```
User: "Hola, ¿cómo estás?"
Triage Agent: "This is Spanish, I'll hand off to Spanish Agent"
  → Hands off to Spanish Agent
Spanish Agent: "¡Hola! Estoy bien, gracias."

User: "Hello, how are you?"
Triage Agent: "This is English, I'll hand off to English Agent"
  → Hands off to English Agent
English Agent: "Hello! I'm doing great, thanks."
```
**Learn:** Route requests to specialized agents

---

#### `agents_as_tools.py` ⭐⭐
**What it does:**
```
Task: Translate "Hello" to multiple languages

Main Agent calls:
  - Spanish Translation Agent → "Hola"
  - French Translation Agent → "Bonjour"  
  - German Translation Agent → "Hallo"
  (All run in parallel!)

Main Agent combines: "Hello translates to: Hola (Spanish), Bonjour (French), Hallo (German)"
```
**Learn:** Use agents as reusable tools

---

#### `llm_as_a_judge.py` ⭐⭐⭐
**What it does:**
```
Round 1:
  Writer Agent: Creates first draft
  Judge Agent: "This needs more detail and better structure. 6/10"
  
Round 2:
  Writer Agent: Improves based on feedback
  Judge Agent: "Much better! Clear and detailed. 8/10"
  
Round 3:
  Writer Agent: Final polish
  Judge Agent: "Excellent work! 9/10" → ✅ Accept
```
**Learn:** Self-improvement through feedback loops

---

#### `parallelization.py` ⭐⭐
**What it does:**
```
Task: Translate "The quick brown fox" to Spanish

Run 5 translation attempts in parallel:
  Translation 1: "El rápido zorro marrón"
  Translation 2: "El veloz zorro café"
  Translation 3: "El zorro marrón rápido"
  Translation 4: "El zorro café veloz"
  Translation 5: "El rápido zorro pardo"

Judge picks best: "Translation 2 is most natural"
```
**Learn:** Parallel execution and selection

---

#### `input_guardrails.py` ⭐⭐
**What it does:**
```
User input: "Teach me Python programming"
  
Guardrail Agent (runs first): 
  "This is a valid programming question" ✅
  → Continue to main agent
  
Main Agent: Provides Python tutorial

---

User input: "Write my homework for me"

Guardrail Agent (runs first):
  "This requests academic dishonesty" ❌
  → STOPS execution, returns error
```
**Learn:** Validate inputs before processing

---

#### `output_guardrails.py` ⭐⭐
**What it does:**
```
Main Agent generates response: "Here's how to hack a website..."

Output Guardrail (checks response):
  "This contains harmful content" ❌
  → BLOCKS output, returns safe message instead

---

Main Agent generates: "Here's how to secure your website..."

Output Guardrail (checks response):
  "This is helpful and safe" ✅
  → Return response to user
```
**Learn:** Validate outputs before showing to users

---

### Tools Examples - Special Capabilities

#### `web_search.py` ⭐⭐
**What it does:**
```
You ask: "What's the latest news about AI?"
Agent thinks: "I need current information"
Agent calls: web_search("latest AI news")
Agent receives: Recent articles and links
Agent responds: Summary of latest AI developments
```
**Learn:** Access real-time internet data

---

#### `code_interpreter.py` ⭐⭐⭐
**What it does:**
```
You ask: "Calculate the fibonacci sequence up to 100"
Agent generates Python code:
  def fibonacci(n):
      ...
Agent executes code safely
Agent returns: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
```
**Learn:** Run code safely in sandbox

---

#### `image_generator.py` ⭐⭐
**What it does:**
```
You ask: "Create an image of a sunset over mountains"
Agent calls: DALL-E API
Agent receives: Image URL
Agent responds: Shows generated image
```
**Learn:** Generate images with AI

---

### Memory Examples - Persistent Conversations

#### `sqlite_session_example.py` ⭐⭐
**What it does:**
```
Turn 1:
You: "My favorite color is blue"
Agent: "Got it! I'll remember that."
  → Saves to SQLite database

Turn 2 (new conversation, same session):
You: "What's my favorite color?"
Agent: "Your favorite color is blue!"
  → Retrieved from SQLite database
```
**Learn:** Persistent memory across conversations

---

#### `redis_session_example.py` ⭐⭐⭐
**What it does:**
```
Same as SQLite, but:
  - Uses Redis (faster, scalable)
  - Works across multiple servers
  - Better for production apps
```
**Learn:** Distributed session management

---

### Complete Applications

#### Research Bot (`research_bot/`) ⭐⭐⭐
**What it does:**
```
You: "Research electric vehicles"

Planner Agent: 
  "I'll research: 1) Market trends 2) Technology 3) Environmental impact"
  
Search Agent (called 3 times in parallel):
  - Searches market trends → finds data
  - Searches technology → finds data
  - Searches environmental impact → finds data
  
Writer Agent:
  Combines all research into comprehensive report
  
Final output: 5-page research report with sources
```
**Learn:** Complex multi-agent workflows

---

#### Financial Research Agent (`financial_research_agent/`) ⭐⭐⭐⭐
**What it does:**
```
You: "Analyze Apple stock"

Planner: Creates analysis plan
  ↓
Search Agent: Gathers financial data
  ↓
Financials Agent: Analyzes numbers
  ↓
Risk Agent: Assesses risks
  ↓
Verifier: Fact-checks everything
  ↓
Writer: Creates final report

Output: Professional financial analysis report
```
**Learn:** Complex domain-specific workflows

---

### MCP Examples - External Integrations

#### `mcp/filesystem_example/` ⭐⭐
**What it does:**
```
You: "What files are in my documents folder?"
Agent: Uses MCP filesystem server
Agent: Lists all files in folder
Agent: "You have: resume.pdf, notes.txt, image.jpg"

You: "Read notes.txt"
Agent: Reads file via MCP
Agent: Returns file contents
```
**Learn:** Access local filesystem safely

---

#### `mcp/git_example/` ⭐⭐⭐
**What it does:**
```
You: "What changed in the last commit?"
Agent: Uses MCP git server
Agent: Runs git commands
Agent: "Last commit: Fixed bug in auth.py, added 3 lines, removed 1"
```
**Learn:** Integrate with Git repositories

---

### Voice & Realtime

#### `realtime/cli/demo.py` ⭐⭐⭐
**What it does:**
```
Terminal interaction via voice:
  You (speaking): "What's the weather like?"
  Agent (speaking back): "Let me check the weather for you..."
  [Real-time voice conversation]
```
**Learn:** Voice-based interactions

---

#### `realtime/app/` ⭐⭐⭐⭐
**What it does:**
```
Web browser interface:
  1. Click microphone button
  2. Speak to agent
  3. Agent responds with voice
  4. See conversation transcript
  [Full voice application in browser]
```
**Learn:** Build web-based voice apps

---

## 🎓 Learning Paths Visualized

### Beginner Path
```
hello_world.py → tools.py → deterministic.py → routing.py
    ⭐              ⭐            ⭐⭐              ⭐⭐
```

### Production Path
```
sqlite_session → input_guardrails → output_guardrails → research_bot
     ⭐⭐              ⭐⭐                 ⭐⭐              ⭐⭐⭐
```

### Advanced Path
```
web_search → parallelization → llm_as_a_judge → financial_research
    ⭐⭐           ⭐⭐                ⭐⭐⭐              ⭐⭐⭐⭐
```

## 🚀 Quick Start Recommendation

**Week 1: Fundamentals**
1. Day 1-2: `hello_world.py`, `tools.py`
2. Day 3-4: `deterministic.py`, `routing.py`
3. Day 5: `sqlite_session_example.py`

**Week 2: Patterns**
1. Day 1-2: `agents_as_tools.py`, `parallelization.py`
2. Day 3-4: `input_guardrails.py`, `output_guardrails.py`
3. Day 5: `llm_as_a_judge.py`

**Week 3: Applications**
1. Day 1-3: `research_bot/`
2. Day 4-5: Build your own application!

## 💡 Example Selection Guide

**I want to...**

- "Just see it work" → `hello_world.py`
- "Use external functions" → `tools.py`
- "Build a workflow" → `deterministic.py`
- "Have specialized agents" → `routing.py`
- "Remember conversations" → `sqlite_session_example.py`
- "Validate inputs" → `input_guardrails.py`
- "Improve outputs iteratively" → `llm_as_a_judge.py`
- "Search the web" → `web_search.py`
- "Run code safely" → `code_interpreter.py`
- "Build a research tool" → `research_bot/`
- "Add voice" → `realtime/cli/demo.py`
- "Build something serious" → `financial_research_agent/`

---

**Ready to start? Run:**
```powershell
cd "C:\Users\Alex Archer\Desktop\openai-agents-python"
$env:OPENAI_API_KEY = "your-key-here"
python -m uv run examples/demo_getting_started.py
```

