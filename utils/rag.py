import streamlit as st
import os
import shutil # For potentially removing directories
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai # Need this for checking API key config

# --- RAG Configuration ---
# Define base directories relative to the project root
# Assuming this script is in `utils/` and project root is one level up
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DOC_DIR = os.path.join(PROJECT_ROOT, "rag_documents")
BASE_VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")

# --- Ensure Base Directories Exist ---
os.makedirs(BASE_DOC_DIR, exist_ok=True)
os.makedirs(BASE_VECTOR_STORE_DIR, exist_ok=True)

# Function to check if Gemini API is configured (needed for embeddings)
def check_gemini_configured_for_rag():
    if st.session_state.get('gemini_configured', False):
        return True
    # Attempt configuration if not done yet (e.g., if accessing RAG manager before other tools)
    from .gemini import configure_gemini # Use relative import
    if configure_gemini():
        return True
    else:
        st.error("Gemini API Key must be configured for RAG functionality (Embeddings).")
        return False

# --- Document Loading ---
def load_documents(rag_id="default"):
    """Loads documents from a specific subdirectory within rag_documents."""
    doc_path = os.path.join(BASE_DOC_DIR, rag_id)
    if not os.path.exists(doc_path) or not os.path.isdir(doc_path):
        st.warning(f"Document directory for context '{rag_id}' not found: {doc_path}")
        return []

    loaded_docs = []
    st.write(f"Scanning for documents in: `{doc_path}`") # Debug info
    files_found = os.listdir(doc_path)
    if not files_found:
        st.info(f"No files found in the '{rag_id}' document folder.")
        return []

    for filename in files_found:
        filepath = os.path.join(doc_path, filename)
        if os.path.isfile(filepath):
            file_ext = os.path.splitext(filename)[1].lower()
            try:
                if file_ext == '.pdf':
                    loader = PyPDFLoader(filepath)
                    loaded_docs.extend(loader.load())
                elif file_ext == '.txt':
                    loader = TextLoader(filepath, encoding='utf-8', autodetect_encoding=True)
                    loaded_docs.extend(loader.load())
                # Add elif for other supported extensions here (e.g., .csv, .docx)
                # Requires installing additional libraries (e.g., `unstructured`, `python-docx`)
                # elif file_ext == '.docx':
                #     from langchain_community.document_loaders import UnstructuredWordDocumentLoader
                #     loader = UnstructuredWordDocumentLoader(filepath)
                #     loaded_docs.extend(loader.load())
                else:
                    st.warning(f"  Skipping unsupported file type: {filename}")
            except Exception as e:
                st.error(f"Error loading file '{filename}': {e}")

    if loaded_docs:
         st.success(f"Successfully loaded {len(loaded_docs)} document(s) from '{rag_id}'.")
    elif files_found : # Check if files existed but none were loadable/supported
         st.warning(f"Found files in '{rag_id}' but none were loaded (check file types and errors).")

    return loaded_docs

# --- Text Splitting ---
def split_documents(documents, chunk_size=1000, chunk_overlap=150):
    """Splits loaded documents into smaller chunks."""
    if not documents:
        return []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True, # Helpful for locating source text
        is_separator_regex=False,
    )
    try:
        splits = text_splitter.split_documents(documents)
        st.write(f"Split {len(documents)} documents into {len(splits)} chunks.")
        return splits
    except Exception as e:
        st.error(f"Error splitting documents: {e}")
        return []


# --- Embeddings and Vector Store ---
def create_or_load_vector_store(splits, rag_id="default", force_recreate=False):
    """Creates a Chroma vector store or loads an existing one for a specific RAG context."""
    if not check_gemini_configured_for_rag():
        return None

    # Define the specific persistent directory for this RAG context
    persist_directory = os.path.join(BASE_VECTOR_STORE_DIR, f"{rag_id}_chroma")
    embedding_model_name = "models/embedding-001" # Recommended Gemini embedding model

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model_name)
    except Exception as e:
        st.error(f"Error initializing GoogleGenerativeAIEmbeddings ({embedding_model_name}): {e}")
        return None

    vector_store = None
    # Check if the directory exists and we are not forcing recreation
    if os.path.exists(persist_directory) and os.path.isdir(persist_directory) and not force_recreate:
        try:
            st.write(f"Attempting to load existing vector store for '{rag_id}' from: `{persist_directory}`")
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            # Perform a quick check to see if loading worked (e.g., count items)
            # This can fail if the store is corrupted or incompatible
            # count = vector_store._collection.count() # Accessing internal API, might change
            # st.success(f"Successfully loaded vector store for '{rag_id}' with approx. {count} items.")
            st.success(f"Successfully loaded vector store for '{rag_id}'.")
        except Exception as e:
            st.error(f"Error loading existing vector store from '{persist_directory}': {e}. Will attempt to recreate.")
            st.info("This might happen if the vector store files are corrupted or incompatible. Removing old store...")
            try:
                shutil.rmtree(persist_directory) # Remove corrupted/old store
                st.info("Old vector store directory removed.")
            except Exception as remove_err:
                st.error(f"Could not remove old vector store directory: {remove_err}. Manual deletion might be required: {persist_directory}")
            force_recreate = True # Force recreation after failed load

    # Create new store if it doesn't exist, load failed, or force_recreate is True
    if vector_store is None or force_recreate:
        if not splits:
            st.warning(f"No document splits provided for '{rag_id}'. Cannot create/recreate vector store.")
            # If forcing recreate but no splits, ensure the old directory is gone if it exists
            if force_recreate and os.path.exists(persist_directory):
                try:
                     shutil.rmtree(persist_directory)
                except Exception as remove_err:
                     st.error(f"Could not remove directory during failed recreate: {remove_err}")
            return None

        try:
            st.write(f"Creating {'new' if not force_recreate else 'replacement'} vector store for '{rag_id}' at: `{persist_directory}`")
            os.makedirs(persist_directory, exist_ok=True) # Ensure directory exists before writing
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory # This saves the embeddings
            )
            # vector_store.persist() # Persist explicitly (Chroma usually does this on creation with persist_directory)
            st.success(f"Successfully created and persisted vector store for '{rag_id}'.")
        except Exception as e:
            st.error(f"Fatal error creating vector store for '{rag_id}': {e}")
            # Clean up potentially partially created directory on failure
            if os.path.exists(persist_directory):
                 try:
                      shutil.rmtree(persist_directory)
                 except Exception: pass # Ignore cleanup error
            return None

    return vector_store

# --- RAG Querying ---
def setup_rag_chain(rag_id="default", model_name="gemini-1.5-flash", temperature=0.1, k_results=4):
    """Sets up the Langchain RAG chain for querying a specific context."""
    if not check_gemini_configured_for_rag():
        return None

    persist_directory = os.path.join(BASE_VECTOR_STORE_DIR, f"{rag_id}_chroma")
    if not os.path.exists(persist_directory) or not os.path.isdir(persist_directory):
        st.warning(f"Vector store for RAG context '{rag_id}' not found at `{persist_directory}`. Please index documents first using 'Manage Knowledge Base'.")
        return None

    try:
        embedding_model_name = "models/embedding-001"
        embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model_name)

        st.write(f"Loading vector store for '{rag_id}' to create RAG chain...")
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        st.write("Vector store loaded.")

        # Initialize the LLM for the chain
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, convert_system_message_to_human=True)

        # Configure retriever
        retriever = vector_store.as_retriever(
             search_type="similarity", # Other options: "mmr", "similarity_score_threshold"
             search_kwargs={"k": k_results} # Number of documents to retrieve
             )

        # Create the QA chain (using RetrievalQA for simplicity)
        # Chain types: "stuff", "map_reduce", "refine", "map_rerank"
        # "stuff" is good for smaller contexts, puts all retrieved docs into the prompt
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True, # Return the documents used for the answer
            # chain_type_kwargs={"prompt": YOUR_CUSTOM_PROMPT} # Optional: customize prompt
        )
        st.success(f"RAG chain ready for context '{rag_id}'.")
        return qa_chain

    except Exception as e:
        st.error(f"Error setting up RAG chain for context '{rag_id}': {e}")
        # Log detailed error for debugging
        # import traceback
        # st.error(traceback.format_exc())
        return None

def query_rag(qa_chain, query):
    """Queries the RAG chain and returns the result and source documents."""
    if not qa_chain:
        st.error("RAG chain is not initialized.")
        return "Error: RAG system not available.", []

    try:
        with st.spinner("Searching knowledge base and generating answer..."):
            # Input must be a dictionary with the key "query" for RetrievalQA
            response = qa_chain.invoke({"query": query})

        answer = response.get("result", "No answer could be generated.")
        source_docs = response.get("source_documents", [])

        # Post-processing or validation can happen here
        if not answer.strip():
             answer = "The AI generated an empty response, possibly due to filtering or lack of relevant information in the retrieved documents."

        return answer, source_docs
    except Exception as e:
        st.error(f"Error during RAG query: {e}")
        return f"An error occurred during the search: {e}", []