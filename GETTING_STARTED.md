# Getting Started with OpenAI Agents SDK Examples

## ✅ Environment Setup (Completed!)

You've successfully installed all dependencies! The virtual environment is now ready at `.venv`.

## 🔑 Step 1: Set Your OpenAI API Key

Before running the examples, you need to set your OpenAI API key. Choose one of these methods:

### Option A: Environment Variable (Session-based)
```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

### Option B: .env File (Recommended)
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your-api-key-here
```

You can get your API key from: https://platform.openai.com/api-keys

## 🚀 Step 2: Run Your First Example

### Example 1: Hello World (Simplest)
```powershell
cd "C:\Users\Alex Archer\Desktop\openai-agents-python"
python -m uv run examples/basic/hello_world.py
```

**What this does:**
- Creates an agent that responds in haikus
- Asks about recursion in programming
- Returns a poetic response

### Example 2: Tools Example (Function Calling)
```powershell
python -m uv run examples/basic/tools.py
```

**What this does:**
- Creates an agent with a weather tool
- Agent learns to call the tool to get information
- Demonstrates function calling

### Example 3: Handoffs (Multi-Agent)
```powershell
python -m uv run examples/handoffs/message_filter.py
```

**What this does:**
- Shows how agents can hand off to other agents
- Demonstrates agent specialization

## 📚 Explore More Examples

### Basic Examples (`examples/basic/`)
- `hello_world.py` - Simple agent interaction
- `tools.py` - Function calling
- `stream_text.py` - Streaming responses
- `usage_tracking.py` - Track token usage
- `local_image.py` - Working with images

### Agent Patterns (`examples/agent_patterns/`)
- `deterministic.py` - Sequential agent workflow
- `routing.py` - Route to specialized agents
- `agents_as_tools.py` - Use agents as tools
- `llm_as_a_judge.py` - Self-improvement pattern
- `parallelization.py` - Run agents in parallel
- `input_guardrails.py` - Input validation
- `output_guardrails.py` - Output validation

### Advanced Examples
- `research_bot/` - Multi-agent research assistant
- `financial_research_agent/` - Financial analysis workflow
- `customer_service/` - Customer service bot
- `mcp/` - Model Context Protocol examples
- `memory/` - Session memory examples
- `realtime/` - Real-time voice agents
- `voice/` - Voice interaction

## 🔍 Example Walkthroughs

### Pattern 1: Sequential Workflow (Deterministic)
Run: `python -m uv run examples/agent_patterns/deterministic.py`

This shows how to:
1. Break down a task into steps
2. Chain agents together
3. Pass output from one agent to the next

### Pattern 2: Routing
Run: `python -m uv run examples/agent_patterns/routing.py`

This shows how to:
1. Create specialized agents (Spanish, English)
2. Use a triage agent to route requests
3. Handle multilingual conversations

### Pattern 3: Agents as Tools
Run: `python -m uv run examples/agent_patterns/agents_as_tools.py`

This shows how to:
1. Use agents as reusable tools
2. Call multiple agents in parallel
3. Combine outputs from different agents

## 📖 Reading the Examples

Each example file is well-commented. To understand them:
1. Read the code from top to bottom
2. Look for the `Agent()` definitions
3. Find the `Runner.run()` or `Runner.run_sync()` calls
4. Check what tools or handoffs are configured

## 🛠️ Common Commands

### Run any example:
```powershell
cd "C:\Users\Alex Archer\Desktop\openai-agents-python"
python -m uv run examples/<folder>/<file>.py
```

### Run tests (if you want to verify everything works):
```powershell
python -m uv run pytest tests/ -v
```

### Format code (if you make changes):
```powershell
python -m uv run ruff format .
```

### Type check:
```powershell
python -m uv run mypy .
```

## 💡 Tips

1. **Start simple**: Begin with `hello_world.py` and `tools.py`
2. **Read the docs**: https://openai.github.io/openai-agents-python/
3. **Experiment**: Modify the examples to learn how they work
4. **Check agent_patterns/**: This folder has the most educational examples
5. **Use tracing**: The SDK automatically traces runs for debugging

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'agents'"
Solution: Use `python -m uv run` instead of just `python`

### "No API key provided"
Solution: Set your `OPENAI_API_KEY` environment variable (see Step 1)

### Import errors
Solution: Make sure you're in the project directory and ran `python -m uv sync`

## 📝 Next Steps

1. ✅ Set your API key
2. ✅ Run `examples/basic/hello_world.py`
3. ✅ Run `examples/basic/tools.py`
4. ✅ Explore `examples/agent_patterns/`
5. ✅ Try modifying an example
6. ✅ Read the documentation at https://openai.github.io/openai-agents-python/

Happy coding! 🎉

