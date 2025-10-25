# Examples Quick Reference

## 🎯 Examples by Category

### 🌟 Beginner-Friendly (Start Here!)

| Example | Command | What It Teaches |
|---------|---------|----------------|
| Hello World | `python -m uv run examples/basic/hello_world.py` | Basic agent setup and running |
| Tools | `python -m uv run examples/basic/tools.py` | Function calling/tool use |
| Streaming | `python -m uv run examples/basic/stream_text.py` | Real-time response streaming |

### 🧠 Agent Patterns (Core Concepts)

| Pattern | Example File | Use Case |
|---------|-------------|----------|
| Sequential Flow | `agent_patterns/deterministic.py` | Break tasks into ordered steps |
| Routing | `agent_patterns/routing.py` | Direct requests to specialized agents |
| Agents as Tools | `agent_patterns/agents_as_tools.py` | Reuse agents like function calls |
| LLM as Judge | `agent_patterns/llm_as_a_judge.py` | Self-improvement and refinement |
| Parallel Execution | `agent_patterns/parallelization.py` | Run multiple agents simultaneously |
| Input Validation | `agent_patterns/input_guardrails.py` | Validate inputs before processing |
| Output Validation | `agent_patterns/output_guardrails.py` | Validate agent outputs |
| Force Tool Use | `agent_patterns/forcing_tool_use.py` | Require specific tool usage |

### 🔧 Tools & Capabilities

| Capability | Example File | Description |
|------------|-------------|-------------|
| Web Search | `tools/web_search.py` | Search the internet |
| Code Execution | `tools/code_interpreter.py` | Run Python code safely |
| File Operations | `tools/file_search.py` | Search and read files |
| Image Generation | `tools/image_generator.py` | Create images with DALL-E |
| Shell Commands | `tools/local_shell.py` | Execute system commands |
| Computer Use | `tools/computer_use.py` | Control computer actions |

### 💾 Memory & Sessions

| Type | Example File | When to Use |
|------|-------------|-------------|
| SQLite Session | `memory/sqlite_session_example.py` | Simple persistent memory |
| Redis Session | `memory/redis_session_example.py` | Distributed/scalable memory |
| Advanced SQLite | `memory/advanced_sqlite_session_example.py` | Complex session handling |
| Encrypted Session | `memory/encrypted_session_example.py` | Secure sensitive data |
| SQLAlchemy | `memory/sqlalchemy_session_example.py` | Use existing database ORM |

### 🔌 MCP (Model Context Protocol)

| Server Type | Example Directory | What It Does |
|-------------|------------------|--------------|
| Filesystem | `mcp/filesystem_example/` | Access local files |
| Git | `mcp/git_example/` | Git repository operations |
| Custom Prompt Server | `mcp/prompt_server/` | Custom prompt templates |
| SSE Streaming | `mcp/sse_example/` | Server-sent events |
| HTTP Streaming | `mcp/streamablehttp_example/` | HTTP-based streaming |

### 🏢 Complete Applications

| Application | Directory | Description |
|-------------|-----------|-------------|
| Research Bot | `research_bot/` | Multi-agent research assistant |
| Financial Research | `financial_research_agent/` | Financial analysis workflow |
| Customer Service | `customer_service/` | Support bot with handoffs |

### 🎙️ Voice & Realtime

| Feature | Directory | Use Case |
|---------|-----------|----------|
| Realtime App | `realtime/app/` | Web-based voice interface |
| Realtime CLI | `realtime/cli/` | Command-line voice demo |
| Twilio Integration | `realtime/twilio/` | Phone call integration |
| Voice Pipeline | `voice/streamed/` | Custom voice workflows |
| Static Voice | `voice/static/` | Pre-recorded voice |

### 🔀 Model Providers

| Provider | Example File | Use Case |
|----------|-------------|----------|
| LiteLLM Auto | `model_providers/litellm_auto.py` | Use 100+ LLM providers |
| LiteLLM Provider | `model_providers/litellm_provider.py` | Configure specific models |
| Custom Agent | `model_providers/custom_example_agent.py` | Agent-level customization |
| Custom Global | `model_providers/custom_example_global.py` | Global provider config |

## 🎓 Learning Paths

### Path 1: Complete Beginner
1. `basic/hello_world.py` - Understand the basics
2. `basic/tools.py` - Learn function calling
3. `agent_patterns/deterministic.py` - Sequential workflows
4. `agent_patterns/routing.py` - Multi-agent systems

### Path 2: Building Production Apps
1. `memory/sqlite_session_example.py` - Add persistence
2. `agent_patterns/input_guardrails.py` - Input validation
3. `agent_patterns/output_guardrails.py` - Output validation
4. `research_bot/` - Complete application example

### Path 3: Advanced Capabilities
1. `tools/web_search.py` - External data access
2. `mcp/filesystem_example/` - File system integration
3. `agent_patterns/parallelization.py` - Performance optimization
4. `financial_research_agent/` - Complex workflows

### Path 4: Voice & Realtime
1. `realtime/cli/demo.py` - CLI voice interface
2. `realtime/app/` - Web voice interface
3. `voice/streamed/` - Custom voice pipelines
4. `realtime/twilio/` - Phone integration

## 🔑 Key Concepts

### Agent Components
```python
agent = Agent(
    name="AgentName",              # Identifier
    instructions="...",            # System prompt
    tools=[...],                   # Available functions
    handoffs=[...],                # Other agents
    output_type=MyModel,           # Structured output
    model="gpt-4o",                # LLM to use
)
```

### Running Agents
```python
# Async (recommended)
result = await Runner.run(agent, "input")

# Sync (simpler for scripts)
result = Runner.run_sync(agent, "input")

# With session memory
result = await Runner.run(agent, "input", session=session)

# With streaming
async for chunk in Runner.run_streamed(agent, "input"):
    print(chunk)
```

### Creating Tools
```python
@function_tool
def my_tool(param: str) -> str:
    """Tool description for the LLM."""
    return "result"
```

### Handoffs
```python
specialist = Agent(name="Specialist", ...)
generalist = Agent(
    name="Generalist",
    handoffs=[specialist]  # Can transfer to specialist
)
```

## 📊 Example Complexity

| Complexity | Examples |
|------------|----------|
| ⭐ Simple | `basic/hello_world.py`, `basic/tools.py` |
| ⭐⭐ Medium | `agent_patterns/routing.py`, `memory/sqlite_session_example.py` |
| ⭐⭐⭐ Advanced | `research_bot/`, `financial_research_agent/` |
| ⭐⭐⭐⭐ Expert | `realtime/app/`, `voice/streamed/` |

## 🚀 Quick Start Commands

```powershell
# Navigate to project
cd "C:\Users\Alex Archer\Desktop\openai-agents-python"

# Set API key (do this first!)
$env:OPENAI_API_KEY = "your-key-here"

# Run basic example
python -m uv run examples/basic/hello_world.py

# Run with different patterns
python -m uv run examples/agent_patterns/routing.py
python -m uv run examples/agent_patterns/deterministic.py
python -m uv run examples/tools/web_search.py

# Explore research bot (complex example)
python -m uv run examples/research_bot/main.py
```

## 💡 Pro Tips

1. **Always use `python -m uv run`** - This ensures the right environment
2. **Read the code first** - Examples are well-commented
3. **Start small** - Begin with basic examples, then progress
4. **Modify examples** - Best way to learn is by experimenting
5. **Check README files** - Many example directories have their own READMEs
6. **Use tracing** - Built-in tracing helps debug agent behavior
7. **Session memory** - Use sessions for multi-turn conversations

## 📚 Additional Resources

- **Documentation**: https://openai.github.io/openai-agents-python/
- **API Reference**: https://openai.github.io/openai-agents-python/ref/
- **GitHub Issues**: https://github.com/openai/openai-agents-python/issues
- **OpenAI Platform**: https://platform.openai.com/docs

