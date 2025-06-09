import streamlit as st
from utils.auth import show_login_form, logout_user, is_authenticated
from utils.gemini import configure_gemini
# Import all modules from the 'modules' package
from modules import (
    technician_assistant,
    customer_chatbot,
    job_summary,
    predictive_maintenance,
    scheduling_optimizer,     # New
    inventory_management,    # New
    knowledge_search,        # New
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

    # Define the modules and their corresponding functions/titles
    # Using a dictionary makes it easier to manage
    modules = {
        "Customer Chatbot": customer_chatbot.show_customer_chatbot,
        "Technician Assistant": technician_assistant.show_technician_assistant,
        "Job Summary Generator": job_summary.show_job_summary,
        "Predictive Maintenance": predictive_maintenance.show_predictive_maintenance,
        "Scheduling Assistant": scheduling_optimizer.show_scheduling_optimizer,
        "Inventory Assistant": inventory_management.show_inventory_management,
        "Knowledge Base Search": knowledge_search.show_knowledge_search,
        "Manage Knowledge Base": rag_manager.show_rag_manager,
    }

    selected_module_title = st.sidebar.radio(
        "Choose a tool:",
        list(modules.keys()), # Get the titles for the radio button options
        key="main_module_selection"
    )
    st.sidebar.markdown("---")

    # --- Logout Button ---
    if st.sidebar.button("Logout", key="logout_button"):
        logout_user()

    # --- Display Selected Module in Main Area ---
    # Find the function associated with the selected title
    module_function = modules.get(selected_module_title)

    if module_function:
        # Display the title of the selected module in the main area
        # Extract icon from the module's title if defined there (optional enhancement)
        # e.g., if MODULE_TITLE = "🛠️ Technician Assistant", extract "🛠️"
        module_icon = ""
        try:
            # Attempt to get title from the module itself if it defines one
            mod_title = getattr(module_function.__module__, 'MODULE_TITLE', selected_module_title)
            if " " in mod_title:
                 icon_part = mod_title.split(" ")[0]
                 # Check if it looks like an emoji or icon
                 if len(icon_part) <= 2 and not icon_part.isalnum():
                      module_icon = icon_part
        except: # Ignore errors if attribute isn't found or parsing fails
            pass

        st.title(f"{module_icon} {selected_module_title}")
        st.markdown("---") # Separator below title

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