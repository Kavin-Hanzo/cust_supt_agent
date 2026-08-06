# src/main.py (CLI Mode)
#
# Can be run either as `python -m src.main` from the project root, or directly
# as `python src/main.py`. The sys.path fix below makes the second form work too:
# running a script directly only puts *its own* directory on sys.path, not the
# project root, so `from src...` imports would otherwise fail with
# "ModuleNotFoundError: No module named 'src'".
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
from src.agent.core import SupportAgent
from src.utils.loader import get_data_loader

load_dotenv()


def _authenticate() -> str:
    """Verifies the customer's email against the Trendly dataset before starting
    a session, so order lookups can be safely scoped to a real account."""
    loader = get_data_loader()
    print("Please verify your account to start a support chat.")
    while True:
        email = input("Account email (or 'exit' to quit): ").strip()
        if email.lower() in ("exit", "quit"):
            return ""
        if loader.get_customer_by_email(email):
            return email.strip().lower()
        print("We couldn't find a Trendly account with that email. Please try again.")


def run_cli():
    email = _authenticate()
    if not email:
        return

    agent = SupportAgent(customer_email=email)
    messages = []
    print("\n=== Trendly Support Agent CLI (Type 'exit' to quit) ===")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        messages.append({"role": "user", "content": user_input})
        reply, handoff, meta = agent.process_turn(messages)
        messages.append({"role": "assistant", "content": reply})

        print(f"\nAgent: {reply}")
        if handoff:
            print(f"\n[SYSTEM]: Escalated to Human! Details: {meta}")
            break


if __name__ == "__main__":
    run_cli()
