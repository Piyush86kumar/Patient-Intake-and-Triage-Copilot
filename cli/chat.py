from __future__ import annotations

import asyncio

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
