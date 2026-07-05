from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from triage_copilot.controller.state_machine import process_turn


def main() -> None:
    print("Triage Copilot chat loop. Type 'quit' to exit.")
    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye.")
            break

        conversation_id = "local-dev"
        response = asyncio.run(process_turn(conversation_id, user_input))
        print(f"Assistant: {response.message}")


if __name__ == "__main__":
    main()
