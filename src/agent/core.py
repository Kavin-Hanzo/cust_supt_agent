import os
from typing import List, Dict, Any, Tuple, Optional
from google import genai
from google.genai import types
from src.agent.prompts import SYSTEM_PROMPT
from src.tools import (
    make_get_order_status_tool,
    make_check_return_eligibility_tool,
    search_policy,
    escalate_to_human,
)


class SupportAgent:
    """
    Core Agent Orchestrator built on Google's unified `google.genai` SDK.

    Each instance is bound to one authenticated customer (`customer_email`).
    That binding is what makes order lookups safe: `get_order_status` and
    `check_return_eligibility` are generated per-instance with the customer's
    email baked into a closure, so the model itself never controls whose
    orders it can see.
    """

    def __init__(
        self,
        customer_email: str,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.6-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")
        if not customer_email or not customer_email.strip():
            raise ValueError(
                "customer_email is required: every SupportAgent session must be "
                "tied to a verified customer so order lookups can be scoped to them."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.customer_email = customer_email.strip().lower()

        self.tools = [
            make_get_order_status_tool(self.customer_email),
            make_check_return_eligibility_tool(self.customer_email),
            search_policy,
            escalate_to_human,
        ]

    def process_turn(
        self, st_messages: List[Dict[str, Any]]
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Processes conversation history, handles tool calls automatically via the new SDK,
        and returns the assistant reply, handoff status, and handoff metadata.
        """
        # Format message history into google.genai Content objects
        contents = []
        for msg in st_messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg.get("content"):
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

        # Configure system instructions and automatic function tools.
        #
        # NOTE: `temperature` (and `top_p`/`top_k`) are deprecated as of the 3.x
        # Flash generation -- the API ignores them today and will return an error
        # on future models if supplied. Google's guidance is to drive determinism
        # through explicit system-instruction rules instead, which SYSTEM_PROMPT
        # already does (strict guardrails, mandatory escalation triggers, etc).
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=self.tools,
        )

        # Execute content generation with automatic function execution
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config,
        )

        # Inspect whether escalate_to_human was triggered during function calls.
        #
        # IMPORTANT: with automatic function calling, the SDK executes tool calls
        # (including escalate_to_human) internally and loops until the model
        # produces a final text-only answer. By the time we get `response` back,
        # `response.function_calls` reflects only that *final* turn -- which is
        # almost always plain text -- so it will NOT show a call that already
        # happened mid-loop. We must instead scan
        # `response.automatic_function_calling_history`, which the SDK populates
        # with every intermediate FunctionCall/FunctionResponse exchanged.
        handoff_triggered = False
        handoff_details: Dict[str, Any] = {}

        afc_history = getattr(response, "automatic_function_calling_history", None) or []
        for content in afc_history:
            for part in (content.parts or []):
                fc = getattr(part, "function_call", None)
                if fc and fc.name == "escalate_to_human":
                    handoff_triggered = True
                    handoff_details = dict(fc.args) if fc.args else {}

        # Fallback: in case automatic function calling stopped short (e.g. hit
        # maximum_remote_calls) and the model's final turn is itself an
        # un-executed escalate_to_human call, catch that too.
        if response.function_calls:
            for call in response.function_calls:
                if call.name == "escalate_to_human":
                    handoff_triggered = True
                    handoff_details = dict(call.args) if call.args else handoff_details

        return response.text or "", handoff_triggered, handoff_details
