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

MODULE_TITLE = "🧾 Invoice Generator"
RAG_ID = "billing_info" # RAG context for standard rates

def show_invoice_generator():
    st.subheader(MODULE_TITLE)
    st.caption("Enter job details to generate a professional invoice. Use the knowledge base for standard rates.")
    st.markdown("---")

    # Initialize or get the RAG chain specific to this context
    chain_key = f'rag_chain_{RAG_ID}'
    if chain_key not in st.session_state:
        st.session_state[chain_key] = None # Initialize as None

    with st.spinner(f"Loading '{RAG_ID}' knowledge base..."):
        if st.session_state[chain_key] is None:
            st.session_state[chain_key] = setup_rag_chain(rag_id=RAG_ID)

    qa_chain = st.session_state.get(chain_key)

    if not qa_chain:
        st.warning(f"Could not load the '{RAG_ID}' knowledge base. Standard pricing information may be unavailable. Ensure documents are present and indexed via 'Manage Knowledge Base'.")

    # --- Invoice Form ---
    with st.form("invoice_form"):
        st.write("**Invoice Details**")

        # Company Info (can be hardcoded or moved to a config file)
        company_info = {
            "name": "CoolBreeze AC Repair",
            "address": "456 Service Rd, Maple County, 12345",
            "phone": "555-COOL (555-2665)",
            "email": "billing@coolbreezeac.com"
        }

        cols1 = st.columns(2)
        invoice_num = cols1[0].text_input("Invoice Number", f"INV-{datetime.date.today().year}-1001")
        invoice_date = cols1[1].date_input("Invoice Date", datetime.date.today())

        st.write("**Customer Information**")
        cols2 = st.columns(2)
        customer_name = cols2[0].text_input("Customer Name", "Jane Doe")
        customer_address = cols2[1].text_input("Customer Address", "123 Main St, Redwood City, 54321")

        st.write("**Job & Line Items**")
        job_date = st.date_input("Date of Service", datetime.date.today())
        line_items_input = st.text_area(
            "List of Services Performed & Parts Used (one per line)",
            height=150,
            placeholder="e.g.,\nStandard Diagnostic Fee\nReplaced run capacitor\nAdded 1.5 lbs of R-410A Refrigerant"
        )
        notes = st.text_area("Additional Notes or Recommendations", "Recommended annual maintenance to prevent future issues.")

        submitted = st.form_submit_button("Generate Invoice")

        if submitted:
            if not customer_name or not line_items_input:
                st.error("Please fill in at least the Customer Name and Line Items.")
            else:
                billing_context = ""
                if qa_chain:
                    with st.spinner("Searching knowledge base for pricing info..."):
                        # Query RAG with the line items to find relevant pricing
                        rag_answer, _ = query_rag(qa_chain, f"Provide standard pricing for the following items if available: {line_items_input}")
                        if rag_answer and "Error" not in rag_answer:
                            billing_context = f"\n\n**Reference Pricing Information from Knowledge Base:**\n{rag_answer}"

                prompt = f"""
                Act as a professional billing assistant for 'CoolBreeze AC Repair'. Your task is to generate a clean, formatted invoice based on the provided details.

                **Company Information:**
                - Name: {company_info['name']}
                - Address: {company_info['address']}
                - Phone: {company_info['phone']}
                - Email: {company_info['email']}

                **Invoice Details:**
                - Invoice #: {invoice_num}
                - Invoice Date: {invoice_date.strftime('%Y-%m-%d')}
                - Date of Service: {job_date.strftime('%Y-%m-%d')}

                **Bill To:**
                - Customer: {customer_name}
                - Address: {customer_address}

                **Line Items from Technician:**
                {line_items_input}

                **Additional Notes:**
                {notes}
                {billing_context}

                **Instructions:**
                1.  Create a professional, well-formatted invoice.
                2.  Use the "Reference Pricing Information" to assign a plausible price to each line item. If a price isn't listed, estimate a reasonable one based on the item description.
                3.  Create a clear table for the line items with columns for 'Description', 'Quantity', 'Unit Price', and 'Total'. Assume quantity is 1 unless specified.
                4.  Calculate a subtotal, a sales tax (assume 7.5%), and a final total amount due.
                5.  Include a "Thank You" message and payment instructions (e.g., "Payment is due upon receipt.").
                6.  Output only the formatted invoice text. Do not add any extra commentary.

                **Example Output Format:**

                # INVOICE

                **CoolBreeze AC Repair**
                456 Service Rd, Maple County, 12345
                Phone: 555-COOL | billing@coolbreezeac.com

                ---
                **BILL TO:**
                Jane Doe
                123 Main St, Redwood City, 54321

                **Invoice #:** {invoice_num}
                **Date:** {invoice_date.strftime('%Y-%m-%d')}
                ---

                | Description                          | Qty | Unit Price | Total   |
                |--------------------------------------|-----|------------|---------|
                | Standard Diagnostic Fee              | 1   | $95.00     | $95.00  |
                | Replaced run capacitor               | 1   | $165.00    | $165.00 |
                | R-410A Refrigerant (1.5 lbs)         | 1.5 | $85.00     | $127.50 |

                ---
                **Subtotal:**  $387.50
                **Sales Tax (7.5%):** $29.06
                **TOTAL DUE:** **$416.56**
                ---

                **Notes:**
                {notes}

                *Thank you for your business! Payment is due upon receipt.*
                """
                with st.spinner("Generating invoice..."):
                    invoice_text = generate_response(prompt, temperature=0.2)
                st.markdown("#### Generated Invoice:")
                st.text_area("Invoice Text (copy this)", value=invoice_text, height=400)