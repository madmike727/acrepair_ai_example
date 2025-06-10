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
from utils.rag import setup_rag_chain, query_rag, BASE_DOC_DIR
import os

# Define the specific RAG context for this module (e.g., company policies, general FAQs)
# Ensure you have a corresponding folder in rag_documents/
RAG_ID = "company_policies" # Or "general_knowledge", "hr_documents" etc.
MODULE_TITLE = "🧠 Knowledge Base Search"

def show_knowledge_search():
    st.subheader(MODULE_TITLE)
    st.caption(f"Search indexed company documents (e.g., policies, procedures) in: `{os.path.join(BASE_DOC_DIR, RAG_ID)}`")
    st.markdown("---")

    # Initialize or get the RAG chain specific to this context
    chain_key = f'rag_chain_{RAG_ID}'
    if chain_key not in st.session_state or st.session_state[chain_key] is None:
        st.write(f"Initializing knowledge base for '{RAG_ID}'...")
        st.session_state[chain_key] = setup_rag_chain(rag_id=RAG_ID)
        # Consider a rerun if setup gives feedback, use cautiously
        # st.rerun()

    qa_chain = st.session_state.get(chain_key)

    if not qa_chain:
        st.error(f"Could not initialize the knowledge base for '{RAG_ID}'.")
        st.warning(f"Please ensure you have placed relevant documents (PDF, TXT) into the `{os.path.join(BASE_DOC_DIR, RAG_ID)}` folder and then use the 'Manage Knowledge Base' tool to **index** this context.")
        return

    # --- Query Input ---
    query_placeholder = f"Ask questions about content in the '{RAG_ID}' documents..."
    query = st.text_area(
        "Enter your search query:",
        key=f"knowledge_query_{RAG_ID}",
        placeholder=query_placeholder,
        height=100
    )

    if st.button(f"Search Knowledge Base", key=f"knowledge_submit_{RAG_ID}"):
        if query:
            answer, source_docs = query_rag(qa_chain, query)

            st.markdown("#### Search Result:")
            st.info(answer)

            if source_docs:
                st.markdown("---")
                st.markdown("#### Found In Documents:")
                for i, doc in enumerate(source_docs):
                    source_name = doc.metadata.get('source', f'Source {i+1}')
                    display_source = os.path.basename(source_name)
                    page_num = doc.metadata.get('page', None)
                    source_label = f"Source {i+1}: {display_source}"
                    if page_num is not None:
                        source_label += f" (Page {page_num + 1})"

                    with st.expander(source_label):
                        snippet = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
                        st.write(f"Content Snippet:\n```\n{snippet}\n```")
            else:
                 st.markdown("---")
                 st.warning("No specific documents were retrieved to support this answer.")

        else:
            st.warning("Please enter a search query.")