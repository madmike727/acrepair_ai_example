import streamlit as st
from utils.gemini import generate_response
from utils.rag import setup_rag_chain, query_rag, BASE_DOC_DIR # Optional RAG usage
import os

MODULE_TITLE = "📦 Inventory Assistant (Conceptual)"
# Optional: Define a RAG context if you have documents listing parts, common issues, etc.
RAG_ID_PARTS = "parts_data" # Example context name

def show_inventory_management():
    st.subheader(MODULE_TITLE)
    st.caption("Get AI suggestions for potential parts needed based on job descriptions or common issues.")
    st.warning("⚠️ This tool provides AI-generated *suggestions* based on general knowledge or indexed documents. It does **not** track real-time stock levels or guarantee part compatibility. Always verify with official manuals and inventory systems.", icon="🤖")
    st.markdown("---")

    use_rag = st.checkbox(f"Augment suggestions with knowledge from `{RAG_ID_PARTS}` documents? (Requires indexing)", value=False, key="inv_use_rag")

    qa_chain_parts = None
    if use_rag:
        st.caption(f"Using RAG on documents in: `{os.path.join(BASE_DOC_DIR, RAG_ID_PARTS)}`")
        chain_key = f'rag_chain_{RAG_ID_PARTS}'
        if chain_key not in st.session_state or st.session_state[chain_key] is None:
            st.write(f"Initializing knowledge base for '{RAG_ID_PARTS}'...")
            st.session_state[chain_key] = setup_rag_chain(rag_id=RAG_ID_PARTS)

        qa_chain_parts = st.session_state.get(chain_key)
        if not qa_chain_parts:
            st.error(f"Could not initialize the '{RAG_ID_PARTS}' knowledge base. Ensure documents are present and indexed via 'Manage Knowledge Base'. Proceeding without RAG.")
            use_rag = False # Fallback to non-RAG mode

    st.markdown("---")
    input_type = st.radio("Suggest parts based on:", ("Job Description / Symptoms", "AC Unit Model"), horizontal=True, key="inv_input_type")

    user_input = ""
    if input_type == "Job Description / Symptoms":
        user_input = st.text_area(
            "Enter job description, symptoms, or error codes:",
            placeholder="e.g., Unit not cooling, fan runs but compressor doesn't start. Humming noise from outdoor unit. Error code E10.",
            height=100,
            key="inv_symptoms"
        )
    else: # AC Unit Model
        user_input = st.text_input(
            "Enter AC Unit Model Number:",
            placeholder="e.g., Trane XL16i (4TTX6048)",
            key="inv_model"
        )

    if st.button("Suggest Potential Parts", key="inv_suggest_button"):
        if user_input:
            rag_context_info = ""
            if use_rag and qa_chain_parts:
                # Perform a RAG query first to get context
                with st.spinner("Searching parts knowledge base..."):
                     rag_answer, rag_sources = query_rag(qa_chain_parts, f"What are common parts or issues related to: {user_input}?")
                     if rag_answer and rag_answer != "Error: RAG system not available.":
                          rag_context_info = f"\n\n**Information from Knowledge Base ({RAG_ID_PARTS}):**\n{rag_answer}"
                          if rag_sources:
                               source_files = list(set([os.path.basename(s.metadata.get('source','')) for s in rag_sources]))
                               rag_context_info += f"\n(Sources: {', '.join(source_files)})"


            # Construct the main prompt for the LLM
            prompt = f"""
            Act as an experienced HVAC parts specialist. Based on the provided information and general HVAC knowledge, suggest a list of potential parts that a technician might need to investigate or replace for the given scenario.

            **Scenario Input ({input_type}):**
            {user_input}
            {rag_context_info if use_rag else ""}

            **Task:**
            1.  Analyze the input ({'symptoms/description' if input_type == 'Job Description / Symptoms' else 'AC model'}).
            {f'2. Consider the supplemental information from the knowledge base if provided.' if use_rag else ''}
            3.  Generate a bulleted list of **potential** parts that might be related to this scenario.
            4.  For each part, briefly explain *why* it might be relevant (e.g., "Capacitor: Common cause for compressor start issues/humming").
            5.  Prioritize parts that are common failure items for the described symptoms or model type (if known).
            6.  Include a strong disclaimer that this is a suggestion list and diagnosis requires on-site testing by a qualified technician.

            **Output:**
            Provide only the bulleted list of potential parts with brief justifications and the final disclaimer. Do not guarantee compatibility.
            """

            with st.spinner("Generating parts suggestions..."):
                # Temperature can be moderate
                parts_suggestion = generate_response(prompt, temperature=0.5)

            st.markdown("#### AI-Generated Potential Parts Suggestions:")
            st.info(parts_suggestion) # Display suggestions in an info box

        else:
            st.warning("Please enter the required information (symptoms or model number).")