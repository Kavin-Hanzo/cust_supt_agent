README.md: Contains local startup commands (chainlit run src/main.py or docker build -t app . && docker run -p 8000:8000 app), environment setup instructions, base URL, and an explicit note on how AI tools (e.g., Cursor, Claude Code) were used during development.

PROMPTS.md: Tracks initial vs. final system prompts, tool description iterations (how tweaking tool docstrings improved function selection accuracy), and failed edge-case prompt attempts.

SOLUTION.md: Stores the 1–2 page technical architecture write-up, key trade-offs, system limitations, and the five discovery questions for the operations team.

src/agent/core.py: Manages conversation history, invokes LLM function calls, parses structured tool payloads, and intercepts handoff events.

src/tools/: Modular tool definitions wrapped with Pydantic schemas so the LLM receives strict typing for tool arguments (order_id, email, reason).

src/utils/loader.py: Loads orders.json into a fast memory lookup map indexed by order_id and pre-loads policy.md for zero-latency retrieval.