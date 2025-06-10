# --- FIX for ChromaDB on Streamlit Sharing ---
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# --- END FIX ---

import streamlit as st
from utils.gemini import generate_response
from utils.rag import setup_rag_chain, query_rag, BASE_DOC_DIR
import os
import datetime

MODULE_TITLE = "📄 Contract Creator"
RAG_ID = "contract_templates"

def show_contract_creator():
    st.subheader(MODULE_TITLE)
    st.caption("Select a service plan and enter customer details to generate a service agreement.")
    st.markdown("---")

    # Initialize or get the RAG chain specific to this context
    chain_key = f'rag_chain_{RAG_ID}'
    if chain_key not in st.session_state or st.session_state[chain_key] is None:
        st.write(f"Initializing knowledge base for '{RAG_ID}'...")
        st.session_state[chain_key] = setup_rag_chain(rag_id=RAG_ID)

    qa_chain = st.session_state.get(chain_key)

    if not qa_chain:
        st.error(f"Could not initialize the contract templates knowledge base.")
        st.warning(f"Please ensure you have placed `contract_templates.txt` into the `{os.path.join(BASE_DOC_DIR, RAG_ID)}` folder and then use the 'Manage Knowledge Base' tool to **index** this context.")
        return

    # --- Contract Form ---
    with st.form("contract_form"):
        st.write("**Contract Parameters**")

        cols1 = st.columns(2)
        customer_name = cols1[0].text_input("Customer Name", "John Smith")
        customer_address = cols1[1].text_input("Customer Address", "789 Service Ln, Maple County, 12345")

        service_plan = st.selectbox(
            "Select Service Plan",
            ("Basic Annual Plan", "Premium Semi-Annual Plan"),
            help="This selection will be used to find the correct template from the knowledge base."
        )
        equipment_list = st.text_area(
            "List of Covered Equipment (one per line)",
            "Carrier AC Unit - Model: 24ABC6\nGoodman Furnace - Model: GMVC96",
            height=100
        )

        cols2 = st.columns(2)
        start_date = cols2[0].date_input("Contract Start Date", datetime.date.today())
        contract_price = cols2[1].number_input("Total Contract Price ($)", min_value=0.0, value=189.00, step=10.0)

        submitted = st.form_submit_button("Generate Contract")

        if submitted:
            # Step 1: Query RAG to get the base contract template
            with st.spinner(f"Retrieving template for '{service_plan}'..."):
                template_query = f"Retrieve the complete and unmodified text for the '{service_plan} Template'. Include everything from 'START OF' to 'END OF' the template."
                template_text, sources = query_rag(qa_chain, template_query)

                if "Error" in template_text or not sources:
                    st.error(f"Failed to retrieve a valid contract template for '{service_plan}'. Please check the knowledge base.")
                    st.stop()

            # Step 2: Use LLM to fill in the template with user data
            with st.spinner("Populating contract with customer details..."):
                fill_prompt = f"""
                You are a legal document assistant. Your task is to populate a contract template with specific customer information.
                Do not alter the legal language of the template. Only replace the placeholder values.

                **Contract Template to Use:**
                ---
                {template_text}
                ---

                **Data to Insert:**
                - [CUSTOMER_NAME]: {customer_name}
                - [CUSTOMER_ADDRESS]: {customer_address}
                - [EQUIPMENT_LIST]: {equipment_list}
                - [START_DATE]: {start_date.strftime('%B %d, %Y')}
                - [CONTRACT_PRICE]: {contract_price:.2f}
                - [CURRENT_DATE]: {datetime.date.today().strftime('%B %d, %Y')}

                **Instructions:**
                Carefully replace every placeholder in the template (e.g., `[CUSTOMER_NAME]`, `[CONTRACT_PRICE]`) with the corresponding data provided above.
                Present the final, completed contract text. Do not include any of your own commentary or headers.
                """
                final_contract = generate_response(fill_prompt, temperature=0.0) # Use 0 temp for precise replacement

            st.markdown("#### Generated Service Agreement:")
            st.text_area("Contract Text (copy this)", value=final_contract, height=500)