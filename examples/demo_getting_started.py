"""
Getting Started Demo - Your First Agent

This is a simple demo to verify your setup is working.
It creates a helpful assistant and asks it a question.
"""

import asyncio
import os
from agents import Agent, Runner


async def main():
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY environment variable is not set!")
        print("\nPlease set it using one of these methods:")
        print("  PowerShell: $env:OPENAI_API_KEY = 'your-api-key-here'")
        print("  Or create a .env file with: OPENAI_API_KEY=your-api-key-here")
        print("\nGet your API key from: https://platform.openai.com/api-keys")
        return

    print("✅ API key found!\n")
    print("=" * 60)
    print("Running your first agent...")
    print("=" * 60)

    # Create a simple agent
    agent = Agent(
        name="Getting Started Assistant",
        instructions="You are a helpful assistant. Be concise and friendly.",
    )

    # Run the agent
    print("\n📝 Question: What are the three laws of robotics?\n")
    
    result = await Runner.run(
        agent,
        "What are the three laws of robotics? Please be brief."
    )

    print("🤖 Agent Response:")
    print("-" * 60)
    print(result.final_output)
    print("-" * 60)
    
    print("\n✅ Success! Your environment is set up correctly.")
    print("\n💡 Next steps:")
    print("   1. Check out GETTING_STARTED.md for more examples")
    print("   2. Try examples/basic/tools.py to see function calling")
    print("   3. Explore examples/agent_patterns/ for common patterns")


if __name__ == "__main__":
    asyncio.run(main())

