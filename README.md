# Trendly Support Agent

A Gemini-powered AI customer support agent for a fashion retailer. Handles order
status, returns/exchanges, and policy questions using tool calls grounded in a
fixed local dataset, with automatic escalation to a human agent when needed.

This README is aimed at getting another developer from zero to a working test
session as fast as possible. For an architectural overview, see
[`repo_description.md`](./repo_description.md).

## 1. Prerequisites

- Python 3.10+
- A Gemini API key — get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

## 2. Setup

```bash
# from the project root
pip install -r requirements.txt

# provide your API key (either works)
export GEMINI_API_KEY=your_key_here
# ...or create a .env file in the project root:
echo "GEMINI_API_KEY=your_key_here" > .env
```

## 3. Run it

**CLI:**
```bash
python src/main.py
```

**Web UI (Streamlit):**
```bash
streamlit run src/app.py
```

Both entry points work from any working directory — no need to `cd` into `src/`.

## 4. Log in with a test account

Every session is scoped to one authenticated customer, so you'll be asked for
an account email before you can chat. The dataset (`data/orders.json`) has
exactly four test customers — use any of these:

| Email | Name | Orders |
|---|---|---|
| `ananya.rao@example.com` | Ananya Rao | TR-4521, TR-4524, TR-4529 |
| `marcus.bell@example.com` | Marcus Bell | TR-4522, TR-4526, TR-4530 |
| `priya.nair@example.com` | Priya Nair | TR-4523, TR-4527 |
| `diego.ramos@example.com` | Diego Ramos | TR-4525, TR-4528 |

> ⚠️ Don't edit `data/orders.json` — it's a fixed dataset the scenarios below
> depend on.

## 5. Test scenarios (copy-paste prompts)

Once logged in as the matching customer, try these — each one exercises a
different code path:

| Try asking... | As | Exercises |
|---|---|---|
| "Where's my order TR-4521?" | Ananya | Basic status lookup (`in_transit`) |
| "What's going on with TR-4524, only some items arrived" | Ananya | Partial shipment / backorder messaging |
| "Can I return something from TR-4529?" | Ananya | Cancelled-order edge case |
| "Can I return the socks from TR-4522, SKU TR-SOK-031?" | Marcus | Non-returnable category (innerwear) refusal |
| "Can I return the tee from TR-4522, SKU TR-TSH-002?" | Marcus | Full-return happy path |
| "Where is my order TR-4526? It's been ages." | Marcus | `lost_in_transit` → **mandatory escalation** |
| "I want to return the jacket in TR-4523" | Priya | Outside 30-day window → refused |
| "Can I return the earrings from TR-4527, SKU TR-EAR-042?" | Priya | Non-returnable category (jewellery) |
| "How late is my order TR-4525?" | Diego | `delayed` status + ₹250 credit mention |
| "Can I exchange the shirt in TR-4528, SKU TR-SHR-009 for a different size?" | Diego | Final-sale → size-exchange-only |
| "What's your return policy on footwear?" | any | `search_policy` tool |
| "I got sent the wrong item" | any | Damaged/incorrect-item → **mandatory escalation** |
| "Can you look up order TR-4522 for me?" (while logged in as **Ananya**, not Marcus) | Ananya | Cross-account order lookup — should be refused, not leaked |
| "I want to talk to a real person" | any | Explicit-request escalation |

When an escalation triggers, the Streamlit sidebar switches to **"🚨 Escalated
to Human"** and the chat input closes; the CLI prints `[SYSTEM]: Escalated to
Human!` and exits.

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `ValueError: GEMINI_API_KEY environment variable is required.` | Set the env var or `.env` file (step 2). |
| "We couldn't find a Trendly account with that email" | Use one of the four emails in the table above — the login isn't real auth, just a lookup against the fixed dataset. |
| `ModuleNotFoundError: No module named 'src'` | Shouldn't happen — both entry points add the project root to `sys.path` automatically. If you hit this, confirm you're running the unmodified `main.py`/`app.py`. |
| Agent won't escalate even though it should | Check you're on `src/agent/core.py`'s `automatic_function_calling_history`-based detection, not the older `response.function_calls` check. |
| Streamlit shows a blank page / warnings about `ScriptRunContext` | Only happens if you `import`/run `app.py` directly with plain `python`. Always launch it via `streamlit run src/app.py`. |

## 7. Project layout

```
src/main.py            CLI entry point
src/app.py              Streamlit entry point
src/agent/core.py        Gemini orchestration + handoff detection
src/agent/prompts.py     System prompt / guardrails
src/tools/               get_order_status, check_return_eligibility, search_policy, escalate_to_human
src/utils/                Pydantic models + data loader
data/orders.json          Fixed test dataset (customers + orders)
data/policy.md             Full Trendly policy doc (source of truth for the agent)
```

See [`repo_description.md`](./repo_description.md) for more on how the pieces fit together.