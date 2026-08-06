# Trendly Support Agent

A Gemini-powered AI customer support agent for "Trendly," a fashion retailer.
Handles order status, returns/exchanges, and policy questions, with tool-based
grounding against a fixed dataset and automatic handoff to a human agent for
sensitive or unresolved cases.

## Stack

- **Model:** Gemini 3.6 Flash (`gemini-3.6-flash`) via the `google-genai` SDK, using automatic function calling, once the free quota or rate limit is reached wait until for reset else user will receive error.
- **Frontends:** Streamlit chat UI (`app.py`) and a CLI (`main.py`)
- **Data:** In-memory, loaded from local JSON/Markdown — no database

## How it works

1. The customer verifies their account email before chatting (checked against `data/orders.json`).
2. Each chat session gets one `SupportAgent`, bound to that verified email.
3. On every turn, the agent sends full conversation history + a system prompt to Gemini, which can call tools to look up orders, check return eligibility, search policy, or escalate to a human.
4. Order-lookup tools are generated per-session with the customer's email baked in (a closure), so the model can never view another customer's order.
5. If `escalate_to_human` is called at any point, the UI/CLI flips to a "handed off" state and stops the AI conversation.

## File map

```
data/
  orders.json          Fixed customer + order dataset (do not edit — used for grading/testing)
  policy.md            Full Trendly shipping/returns/refunds policy (source of truth)

src/
  main.py              CLI entry point — run with `python src/main.py`
  app.py               Streamlit entry point — run with `streamlit run src/app.py`

  agent/
    core.py            SupportAgent: wraps the Gemini client, builds per-session tools,
                        runs a turn, and detects handoff via automatic_function_calling_history
    prompts.py         SYSTEM_PROMPT — guardrails, tool routing, mandatory escalation rules

  tools/
    orders.py           get_order_status / check_return_eligibility (as per-session factories,
                         each scoped to the authenticated customer's email)
    policy.py            search_policy — returns the policy document
    handoff.py           escalate_to_human — signals a handoff to a human agent

  utils/
    models.py             Pydantic schemas: Customer, Order, OrderItem, and the tool response shapes
    loader.py              DataLoader — loads orders.json / policy.md once, indexes by order ID /
                            customer ID / email

requirements.txt        google-genai, streamlit, python-dotenv, pydantic
```

## Running it

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here   # or put it in a .env file

python src/main.py          # CLI
streamlit run src/app.py    # Web UI
```

## Key design notes

- **Authentication:** No real auth — email is matched against the dataset as a lightweight identity check. Good enough for a demo; would need real auth for production.
- **Order privacy:** Unauthorized/nonexistent order lookups return an identical generic "not found" message, so order IDs can't be enumerated.
- **Escalation:** Mandatory for lost parcels, damaged/defective items, COD refunds needing bank details, explicit requests, or unresolved/hostile conversations (see `prompts.py`).
- **No live "current date":** Return-window math uses `date.today()`, so results will drift correctly over time (the dataset's own notes assume "today" is around Aug 2026).