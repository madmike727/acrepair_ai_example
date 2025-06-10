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
from utils.rag import setup_rag_chain, query_rag, BASE_DOC_DIR # Import BASE_DOC_DIR for display
import os

# Define the specific RAG context for this module
RAG_ID = "tech_manuals"
MODULE_TITLE = "🛠️ Technician Diagnostic Assistant"

def show_technician_assistant():
    st.subheader(MODULE_TITLE)
    st.caption(f"Powered by RAG on documents in: `{os.path.join(BASE_DOC_DIR, RAG_ID)}`")
    st.markdown("---")

    # Initialize or get the RAG chain specific to tech manuals from session state
    chain_key = f'rag_chain_{RAG_ID}'
    if chain_key not in st.session_state or st.session_state[chain_key] is None:
        # Attempt to setup the chain if not already done or if setup failed previously
        st.write(f"Initializing knowledge base for '{RAG_ID}'...")
        st.session_state[chain_key] = setup_rag_chain(rag_id=RAG_ID)
        # Rerun slightly to update the state if setup_rag_chain provides feedback
        # st.rerun() # Use cautiously, might cause loops if setup fails repeatedly

    qa_chain = st.session_state.get(chain_key)

    if not qa_chain:
        st.error(f"Could not initialize the knowledge base for '{RAG_ID}'.")
        st.warning(f"Please ensure you have placed relevant documents (PDF, TXT) into the `{os.path.join(BASE_DOC_DIR, RAG_ID)}` folder and then use the 'Manage Knowledge Base' tool to **index** this context.")
        return # Stop execution for this module if chain isn't ready

    # --- Query Input ---
    query_placeholder = "Enter symptoms (e.g., 'unit blowing warm air'), error codes (e.g., 'E4 error'), or specific questions (e.g., 'what is the charge pressure for model XYZ?')"
    query = st.text_area(
        "Describe the issue or ask your question:",
        key=f"tech_query_{RAG_ID}",
        placeholder=query_placeholder,
        height=100
    )

    if st.button(f"Get Assistance", key=f"tech_submit_{RAG_ID}"):
        if query:
            answer, source_docs = query_rag(qa_chain, query)

            st.markdown("#### AI Diagnostic Suggestions:")
            st.info(answer) # Use info box for the answer

            if source_docs:
                st.markdown("---")
                st.markdown("#### Relevant Information Found In:")
                for i, doc in enumerate(source_docs):
                    # Displaying metadata like source filename is helpful
                    source_name = doc.metadata.get('source', f'Source {i+1}')
                    # Extract just the filename from the path for cleaner display
                    display_source = os.path.basename(source_name)

                    page_num = doc.metadata.get('page', None) # PyPDFLoader often includes page number
                    source_label = f"Source {i+1}: {display_source}"
                    if page_num is not None:
                        source_label += f" (Page {page_num + 1})" # Page numbers are often 0-indexed

                    with st.expander(source_label):
                        # Display a snippet of the relevant text chunk
                        snippet = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
                        st.write(f"Content Snippet:\n```\n{snippet}\n```")
                        # st.write("---")
                        # st.json(doc.metadata) # Uncomment to see all metadata for debugging
            else:
                st.markdown("---")
                st.warning("No specific documents were retrieved to support this answer. The response is based on the AI's general knowledge potentially guided by the query context.")

        else:
            st.warning("Please enter a description of the issue or a question.")