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
# REMOVED: import chromadb
# REMOVED: from langchain.vectorstores import Chroma
from utils.auth import show_login_form, logout_user, is_authenticated
from utils.gemini import configure_gemini
# Import all modules from the 'modules' package
from modules import (
    technician_assistant,
    customer_chatbot,
    job_summary,
    predictive_maintenance,
    scheduling_optimizer,
    inventory_management,
    knowledge_search,
    invoice_generator,       # New
    contract_creator,        # New
    rag_manager
)
import os # To help construct paths if needed

# --- Page Configuration (Set first) ---
st.set_page_config(
    page_title="AC Repair AI Portal",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'mailto:support@youcompany.com', # Replace with your help info
        'Report a bug': "mailto:bugs@youcompany.com", # Replace
        'About': "# AC Repair AI Assistant Portal\nBrings AI tools to help streamline AC repair operations."
    }
)

# --- Initialize Gemini API ---
# This is called early to ensure the API key is checked/configured.
# Errors are handled within configure_gemini() and will stop the app if critical.
if 'gemini_init_done' not in st.session_state:
     configure_gemini()
     st.session_state['gemini_init_done'] = True # Mark as done


# --- Main Application Logic ---
def display_app():
    st.sidebar.title(f"❄️ AI Portal")
    st.sidebar.write(f"Welcome, **{st.session_state['username']}**!")
    st.sidebar.markdown("---")

    # --- Module Selection ---
    st.sidebar.header("Assistant Tools")

    # Define ALL modules and their corresponding functions
    all_modules = {
        "Customer Chatbot": customer_chatbot.show_customer_chatbot,
        "Technician Assistant": technician_assistant.show_technician_assistant,
        "Job Summary Generator": job_summary.show_job_summary,
        "Predictive Maintenance": predictive_maintenance.show_predictive_maintenance,
        "Scheduling Assistant": scheduling_optimizer.show_scheduling_optimizer,
        "Inventory Assistant": inventory_management.show_inventory_management,
        "Invoice Generator": invoice_generator.show_invoice_generator,          # New
        "Contract Creator": contract_creator.show_contract_creator,            # New
        "Knowledge Base Search": knowledge_search.show_knowledge_search,
        "Manage Knowledge Base": rag_manager.show_rag_manager,
    }

    # Create a list of modules that the current user can click on.
    # We check if the username is 'admin'.
    is_admin = st.session_state.get('username') == 'admin'
    enabled_module_keys = list(all_modules.keys())

    if not is_admin:
        # If the user is NOT an admin, remove the management tool from the clickable list.
        enabled_module_keys.remove("Manage Knowledge Base")

    # Create the radio button group ONLY with the enabled modules for the current user.
    selected_module_title = st.sidebar.radio(
        "Choose a tool:",
        enabled_module_keys, # Use the filtered list of module titles
        key="main_module_selection",
        label_visibility="collapsed" # Hides the label for a cleaner look
    )

    # If the user is NOT an admin, we manually display the disabled option using styled markdown.
    if not is_admin:
        st.sidebar.markdown(
            "⚪ <span style='color: #888; font-style: italic;'>Manage Knowledge Base (Admin only)</span>",
            unsafe_allow_html=True
        )

    st.sidebar.markdown("---")

    # --- Logout Button ---
    if st.sidebar.button("Logout", key="logout_button"):
        logout_user()

    # --- Display Selected Module in Main Area ---
    # Find the function associated with the selected title from the 'all_modules' dictionary
    module_function = all_modules.get(selected_module_title)

    if module_function:
        # Display the title of the selected module in the main area
        module_icon = ""
        try:
            mod_title = getattr(module_function.__module__, 'MODULE_TITLE', selected_module_title)
            if " " in mod_title:
                 icon_part = mod_title.split(" ")[0]
                 if len(icon_part) <= 2 and not icon_part.isalnum():
                      module_icon = icon_part
        except:
            pass

        st.title(f"{module_icon} {selected_module_title}")
        st.markdown("---")

        # Call the function to display the selected module's UI
        module_function()
    else:
        st.error("Selected module could not be loaded.")


# --- App Entry Point ---
if __name__ == "__main__":
    # Check authentication status
    if not is_authenticated():
        st.title("❄️ AC Repair AI Portal Login")
        st.markdown("---")
        show_login_form()
    else:
        # User is logged in, display the main application interface
        display_app()