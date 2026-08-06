import sys
from pathlib import Path

# See the comment in main.py: this makes `streamlit run src/app.py` work
# regardless of the working directory it's launched from, by putting the
# project root (parent of src/) on sys.path before any `from src...` import.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import os
import streamlit as st
from dotenv import load_dotenv
from src.agent.core import SupportAgent
from src.utils.loader import get_data_loader

load_dotenv()

st.set_page_config(
    page_title="Trendly Customer Support",
    page_icon="🛍️",
    layout="centered"
)

st.title("🛍️ Trendly Customer Support")
st.caption("AI Support Assistant for Orders, Returns & Policy Inquiries (Gemini Powered)")

if "customer_email" not in st.session_state:
    st.session_state.customer_email = None

if "agent" not in st.session_state:
    st.session_state.agent = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "handoff_active" not in st.session_state:
    st.session_state.handoff_active = False

if "handoff_details" not in st.session_state:
    st.session_state.handoff_details = None


def _start_session(email: str) -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Missing `GEMINI_API_KEY`. Please set it in your environment or `.env` file.")
        st.stop()
    st.session_state.agent = SupportAgent(api_key=api_key, customer_email=email)
    st.session_state.customer_email = email


# --- Login gate -------------------------------------------------------------
# Order lookups are scoped per-customer, so we need a verified email before
# any chat tools can run (this is what prevents one customer from viewing
# another customer's order -- see Policy Section 7).
if not st.session_state.customer_email:
    st.subheader("Verify your account to start chatting")
    with st.form("login_form"):
        email_input = st.text_input("Account email")
        submitted = st.form_submit_button("Start chat")

    if submitted:
        loader = get_data_loader()
        if loader.get_customer_by_email(email_input):
            _start_session(email_input)
            st.rerun()
        else:
            st.error("We couldn't find a Trendly account with that email. Please try again.")
    st.stop()

with st.sidebar:
    st.header("Agent Operations")
    st.caption(f"Signed in as: {st.session_state.customer_email}")

    if st.session_state.handoff_active:
        st.error("🚨 Escalated to Human Agent")
        if st.session_state.handoff_details:
            st.json(st.session_state.handoff_details)
    else:
        st.success("🟢 AI Agent Active")

    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.session_state.handoff_active = False
        st.session_state.handoff_details = None
        st.rerun()

    if st.button("Switch Account"):
        st.session_state.customer_email = None
        st.session_state.agent = None
        st.session_state.messages = []
        st.session_state.handoff_active = False
        st.session_state.handoff_details = None
        st.rerun()

for msg in st.session_state.messages:
    if msg["role"] in ["user", "assistant"] and msg.get("content"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if st.session_state.handoff_active:
    st.warning("⚠️ This chat has been transferred to a Trendly human support specialist "
               "(Support Hours: 9 AM - 9 PM IST). An agent will join shortly.")

if not st.session_state.handoff_active:
    if prompt := st.chat_input("How can I help you with your Trendly order?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Trendly Assistant is thinking..."):
            reply, handoff, handoff_meta = st.session_state.agent.process_turn(
                st.session_state.messages
            )

        st.session_state.messages.append({"role": "assistant", "content": reply})

        with st.chat_message("assistant"):
            st.markdown(reply)

        if handoff:
            st.session_state.handoff_active = True
            st.session_state.handoff_details = handoff_meta
            st.rerun()
