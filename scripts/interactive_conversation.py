# -*- coding: utf-8 -*-
"""
Interactive conversation with OpenAI via terminal.

Run this script to have a real conversation with OpenAI that will appear
in your OpenAI usage logs. Requires OPENAI_API_KEY to be set in .env.

Usage:
    py scripts/interactive_conversation.py

Note: Use 'py' command (not 'python') to ensure Python 3.14 is used.
"""

import os
import sys

# Force correct Python
if 'msys64' in sys.executable.lower():
    print("❌ ERROR: Using MSYS Python. Run: py scripts/interactive_conversation.py")
    sys.exit(1)

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.ai.openai_client import OpenAIClient
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)
from app.application.use_cases.conversation import ConversationUseCase


class InMemoryCache:
    """Simple in-memory cache for conversation history during a session.
    
    Implements CacheRepository interface for compatibility with ConversationUseCase.
    """

    def __init__(self):
        self.store = {}

    def get(self, key):
        """Retrieve value from cache."""
        return self.store.get(key)

    def set(self, key, value, ttl_seconds: int = 3600):
        """Store value in cache (ttl_seconds ignored for in-memory)."""
        self.store[key] = value
    
    def delete(self, key):
        """Delete value from cache."""
        self.store.pop(key, None)
    
    def exists(self, key) -> bool:
        """Check if key exists."""
        return key in self.store
    
    def clear(self):
        """Clear all cache entries."""
        self.store.clear()


class TerminalMessenger:
    """Mock messenger that just prints to terminal."""

    def send(self, phone, message):
        print(f"\n[SENT to {phone}]: {message}\n")


def main():
    load_dotenv()

    # Verify API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set in .env file")
        print("Set your OpenAI API key first:")
        print("  OPENAI_API_KEY=sk-xxxxx")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("🤖 OpenAI Interactive Conversation")
    print("=" * 70)
    print("Type your messages and press Enter to chat with OpenAI.")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("Type 'clear' to reset conversation history.")
    print("=" * 70 + "\n")

    try:
        # Initialize components
        ai_client = OpenAIClient(api_key=api_key)
        repo = ReservationRepositoryMemory()
        cache = InMemoryCache()
        messenger = TerminalMessenger()

        use_case = ConversationUseCase(
            ai_service=ai_client,
            reservation_repo=repo,
            cache_repository=cache,
            messaging=messenger,
        )

        phone = "terminal-session"
        turn = 0

        while True:
            turn += 1
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() == "clear":
                    cache.store = {}
                    print("✅ Conversation history cleared.\n")
                    continue

                # Show that we're processing
                print("\n⏳ Waiting for OpenAI...", end="", flush=True)

                # Execute conversation (calls real OpenAI API)
                response = use_case.execute(phone, user_input)

                # Clear the "waiting" message and show response
                print("\r" + " " * 30 + "\r", end="")  # clear line
                print(f"🤖 AI: {response}\n")

                # Show conversation statistics
                history = cache.get(phone) or []
                print(f"   [Turn {turn} | Messages in history: {len(history)}]\n")

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user.")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("   Check your API key and internet connection.\n")

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
