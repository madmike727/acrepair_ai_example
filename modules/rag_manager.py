import streamlit as st
import os
import shutil
from utils.rag import load_documents, split_documents, create_or_load_vector_store, BASE_DOC_DIR, BASE_VECTOR_STORE_DIR

MODULE_TITLE = "📚 Manage Knowledge Base (RAG)"

def get_available_rag_contexts():
    """Lists subdirectories in the base document directory as available RAG contexts."""
    if not os.path.exists(BASE_DOC_DIR) or not os.path.isdir(BASE_DOC_DIR):
        st.error(f"Base document directory '{BASE_DOC_DIR}' not found. Please create it.")
        return []
    try:
        contexts = [d for d in os.listdir(BASE_DOC_DIR) if os.path.isdir(os.path.join(BASE_DOC_DIR, d))]
        # Filter out hidden directories like .DS_Store if necessary
        contexts = [c for c in contexts if not c.startswith('.')]
        return contexts
    except Exception as e:
        st.error(f"Error listing document contexts: {e}")
        return []

def show_rag_manager():
    st.subheader(MODULE_TITLE)
    st.caption("Upload documents and create/update searchable knowledge bases (Vector Stores) for different AI tools.")
    st.markdown("---")

    # --- Select RAG Context ---
    available_contexts = get_available_rag_contexts()

    if not available_contexts:
        st.warning(f"No RAG contexts (document folders) found in `{BASE_DOC_DIR}`.")
        st.info(f"To create a knowledge base, first create a subfolder inside `{BASE_DOC_DIR}` (e.g., `tech_manuals`, `company_policies`) and place your `.txt` or `.pdf` documents inside it.")
        st.stop()

    # Use a selectbox to choose which RAG context to manage
    selected_context = st.selectbox(
        "Select Knowledge Base Context to Manage:",
        available_contexts,
        index=0,
        key="rag_manager_context_select"
        )
    context_doc_path = os.path.join(BASE_DOC_DIR, selected_context)
    context_vector_store_path = os.path.join(BASE_VECTOR_STORE_DIR, f"{selected_context}_chroma")
    st.write(f"**Managing Context:** `{selected_context}`")
    st.write(f" - Document Source: `{context_doc_path}`")
    st.write(f" - Vector Store: `{context_vector_store_path}`")
    st.markdown("---")


    # --- File Uploader ---
    st.write(f"**Upload New Documents to '{selected_context}':**")
    uploaded_files = st.file_uploader(
        f"Upload PDF or TXT files for '{selected_context}'",
        accept_multiple_files=True,
        type=['pdf', 'txt'], # Add more types if loaders are added in rag.py
        key=f"uploader_{selected_context}" # Unique key per context prevents state issues
    )

    if uploaded_files:
        file_status = []
        # Ensure the target document directory exists
        os.makedirs(context_doc_path, exist_ok=True)
        for uploaded_file in uploaded_files:
            file_path = os.path.join(context_doc_path, uploaded_file.name)
            try:
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_status.append(f"✅ Successfully saved: `{uploaded_file.name}`")
            except Exception as e:
                file_status.append(f"❌ Error saving `{uploaded_file.name}`: {e}")
        # Display status messages
        for status in file_status:
            if "✅" in status:
                st.success(status)
            else:
                st.error(status)
        st.info(f"**Important:** After uploading, you must **Re-Index** the '{selected_context}' knowledge base below to include the new documents in searches.")
        # Clear the uploader state after processing to avoid re-uploading on rerun
        # This can be tricky with Streamlit's execution model; often simpler to let user clear manually.


    # --- List Current Documents & Manage ---
    st.markdown("---")
    st.write(f"**Current Documents in '{selected_context}':**")
    try:
        if not os.path.exists(context_doc_path):
             st.info("Document folder does not exist yet for this context.")
             current_files = []
        else:
             current_files = [f for f in os.listdir(context_doc_path) if os.path.isfile(os.path.join(context_doc_path, f)) and not f.startswith('.')]

        if current_files:
            # Allow deletion? (Use with caution!)
            cols = st.columns([3, 1]) # Column for filename, column for delete button
            for filename in sorted(current_files):
                 cols[0].write(f"- `{filename}`")
                 # delete_key = f"delete_{selected_context}_{filename}" # Unique key
                 # if cols[1].button("Delete", key=delete_key, help=f"Permanently delete {filename}"):
                 #     try:
                 #         os.remove(os.path.join(context_doc_path, filename))
                 #         st.success(f"Deleted '{filename}'. Re-index recommended.")
                 #         st.rerun() # Rerun to update the list
                 #     except Exception as e:
                 #         st.error(f"Error deleting '{filename}': {e}")
            st.markdown(f"*Found {len(current_files)} document(s).*")

        else:
            st.info(f"No documents found in the `{context_doc_path}` folder.")
    except Exception as e:
         st.error(f"Could not list files in '{context_doc_path}': {e}")


    # --- Indexing Actions ---
    st.markdown("---")
    st.write(f"**Index Documents for '{selected_context}':**")
    st.warning("Re-indexing processes all documents in the selected context folder. This can take time for large collections and will overwrite the existing index for this context.")

    col1, col2 = st.columns(2)

    # Button to Re-Index
    if col1.button(f"🔄 Create / Re-Index '{selected_context}' Knowledge Base", key=f"index_{selected_context}"):
        with st.spinner(f"Processing and indexing documents for '{selected_context}'... Please wait."):
            st.write("Step 1: Loading documents...")
            docs = load_documents(rag_id=selected_context)
            if not docs:
                st.error("No documents were loaded. Indexing cannot proceed. Check the document folder and file types.")
            else:
                st.write("Step 2: Splitting documents into chunks...")
                splits = split_documents(docs)
                if not splits:
                    st.error("Document splitting failed. Cannot proceed with indexing.")
                else:
                    st.write("Step 3: Creating/Updating vector store and embeddings...")
                    # Force recreate = True ensures we overwrite the old index
                    vector_store = create_or_load_vector_store(splits, rag_id=selected_context, force_recreate=True)
                    if vector_store:
                        st.success(f"✅ Knowledge base '{selected_context}' was successfully indexed!")
                        st.info("AI tools using this context will now use the updated information.")
                        # Clear the cached RAG chain for this context so it forces a reload on next use
                        chain_key = f'rag_chain_{selected_context}'
                        if chain_key in st.session_state:
                            del st.session_state[chain_key]
                            st.write(f"(Cleared cached RAG chain for '{selected_context}')")
                    else:
                        st.error(f"❌ Failed to create or update the vector store for '{selected_context}'. Check logs/errors above.")

    # Button to Delete Index (Use with extreme caution)
    if os.path.exists(context_vector_store_path):
         if col2.button(f"🗑️ Delete Index for '{selected_context}'", key=f"delete_index_{selected_context}", help="WARNING: This permanently deletes the indexed data (vector store) for this context. Documents remain, but searchability is removed until re-indexed."):
              try:
                   shutil.rmtree(context_vector_store_path)
                   st.success(f"Successfully deleted the index/vector store for '{selected_context}'.")
                   # Clear any cached chain too
                   chain_key = f'rag_chain_{selected_context}'
                   if chain_key in st.session_state:
                         del st.session_state[chain_key]
                   st.rerun() # Rerun to update UI reflecting deletion
              except Exception as e:
                   st.error(f"Error deleting index directory '{context_vector_store_path}': {e}")
    else:
         col2.info(f"No index found for '{selected_context}' to delete.")