# --- FIX for ChromaDB on Streamlit Sharing ---
# This is a "monkey patch" to use a more modern version of SQLite
# that is required by ChromaDB.
# See: https://docs.trychroma.com/troubleshooting#sqlite
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# --- END FIX ---

# Now you can import your other libraries
import streamlit as st
from utils.gemini import generate_response

MODULE_TITLE = "💬 Customer Service Chatbot"

# Define system prompt for the chatbot outside the function to avoid redefinition
CHATBOT_SYSTEM_PROMPT = """
You are a friendly and professional AI Customer Service Representative for 'CoolBreeze AC Repair'.
Your goal is to assist customers with inquiries about AC services, basic troubleshooting, and scheduling availability, while maintaining a helpful and polite tone.

**Your Capabilities:**
*   Answer frequently asked questions (FAQs) about services offered (repair, maintenance, installation), service areas, and business hours.
*   Provide *very basic* troubleshooting steps that customers can safely perform themselves (e.g., checking the thermostat settings, checking/replacing air filters, checking the circuit breaker).
*   Check general availability or provide typical response times (e.g., "We usually have technicians available within 24-48 hours, but exact times depend on current workload").
*   Gather initial information about the customer's problem (e.g., "What seems to be the issue with your AC?", "Is it making any strange noises?").
*   Explain the process for booking an appointment (e.g., "To book an appointment, I can help gather your details, or you can call us directly at 555-COOL").

**Your Limitations & Guidelines:**
*   **Do NOT provide specific price quotes.** State: "For specific pricing, please call our office or I can arrange for someone to call you back."
*   **Do NOT confirm specific appointment times.** State: "I can take your request and preferred time, and our dispatcher will call you back to confirm the exact appointment slot based on technician availability."
*   **Do NOT give complex diagnostic advice.** If the issue sounds complex or requires tools/expertise, state: "That sounds like something our technicians should look at. Would you like to schedule a visit?"
*   **Be polite and empathetic.** Acknowledge customer frustration if expressed.
*   **If unsure, say so.** Don't make up information. Offer to connect the customer with a human representative.
*   Keep responses relatively concise.

Business Info (Example - Customize this):
*   Company Name: CoolBreeze AC Repair
*   Phone: 555-COOL (555-2665)
*   Services: AC Repair, AC Maintenance, AC Installation, Duct Cleaning
*   Service Area: Maple County, Redwood City
*   Hours: Mon-Fri 8 AM - 6 PM, Sat 9 AM - 1 PM (Emergency service available 24/7 via phone)
"""

def show_customer_chatbot():
    st.subheader(MODULE_TITLE)
    st.caption("Ask about our services, basic AC tips, or scheduling inquiries.")
    st.markdown("---")

    # Initialize chat history in session state if it doesn't exist
    if "customer_chat_messages" not in st.session_state:
        st.session_state.customer_chat_messages = [
            {"role": "assistant", "content": "Hello! Welcome to CoolBreeze AC Repair. How can I help you today?"}
        ]

    # Display past chat messages
    for message in st.session_state.customer_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input using chat_input
    if prompt := st.chat_input("What can I help you with?"):
        # Add user message to history and display it
        st.session_state.customer_chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare the context for the LLM (includes system prompt and history)
        # We should format the history appropriately for the LLM
        history_for_llm = []
        for msg in st.session_state.customer_chat_messages:
             # Gemini API expects a specific format usually alternating 'user' and 'model' roles
             role = "model" if msg["role"] == "assistant" else msg["role"]
             history_for_llm.append(f"{role}: {msg['content']}")

        # Combine system prompt, history, and new prompt
        # Note: Formatting might need adjustment based on how the model best handles history.
        #       Simple concatenation might work, or a more structured format.
        #       For Gemini, sending history might involve constructing a 'contents' list.
        #       Let's try a simpler approach first by just including the last few turns in the prompt.
        context_window = 5 # How many past messages (user + assistant) to include
        recent_history = "\n".join(history_for_llm[-(context_window*2):]) # Get last N pairs

        full_prompt = f"{CHATBOT_SYSTEM_PROMPT}\n\n**Conversation History:**\n{recent_history}\n\n**user:** {prompt}\n**model:**"


        # Generate assistant response and display it
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Pass the full prompt to the LLM
                response = generate_response(full_prompt, temperature=0.5) # Lower temp for more factual chat
                st.markdown(response)
                # Add assistant response to history
                st.session_state.customer_chat_messages.append({"role": "assistant", "content": response})