import streamlit as st
import time

# --- Simple Authentication (NOT FOR PRODUCTION) ---
# Load users from secrets.toml for this example
# In production, use a secure database and hashing (e.g., streamlit-authenticator).

def get_users():
    """Loads user credentials from st.secrets."""
    # --- Keeping minimal debug for confirmation ---
    #print("--- DEBUG: Contents of st.secrets ---")
    #print(st.secrets)
    #print("--- END DEBUG ---")

    users = {}
    key_to_check = "credentials"

    # --- CORRECTED CONDITION ---
    # Check ONLY if the 'credentials' key exists.
    # We trust that if it exists, Streamlit parsed it into a usable structure (AttrDict).
    if key_to_check in st.secrets:
        #print(f"DEBUG: Found key '{key_to_check}'. Assuming it's the credentials section.")
        try:
            # Access it directly - AttrDict supports dictionary-like access
            users = st.secrets[key_to_check]
            # You might want to explicitly convert it to a standard dict for consistency downstream, though often not strictly necessary
            users = dict(users)
            #print(f"DEBUG: Successfully extracted users from st.secrets['{key_to_check}']")
        except Exception as e:
            #print(f"ERROR: Could not access or process st.secrets['{key_to_check}']: {e}")
            users = {} # Ensure users is empty on error
    else:
        # This 'else' block now correctly handles the case where the [credentials] section is MISSING
        #print(f"DEBUG: Key '{key_to_check}' not found. Checking for top-level user keys as fallback.")
        excluded_keys = ["GEMINI_API_KEY"]
        # Filter top-level items that are strings (potential user=pass pairs)
        potential_users = {k: v for k, v in st.secrets.items() if k not in excluded_keys and isinstance(v, str)}
        if potential_users:
            users = potential_users
            st.warning("Using top-level keys in secrets.toml for authentication. Consider using a [credentials] section for clarity.", icon="⚠️")
            #print(f"DEBUG: Found users defined as top-level keys: {list(users.keys())}")
        else:
             #print("DEBUG: No fallback users found at top level either.")
            users = {}

    # Final check - Ensure 'users' is actually a dictionary before returning
    if not isinstance(users, dict):
        #print(f"ERROR: Extracted 'users' is not a dictionary (type: {type(users)}). Resetting to empty.")
        users = {}

    #print(f"DEBUG: Final 'users' dictionary being returned: {users}")
    return users

# --- Rest of auth.py ---
# (login_user, show_login_form, logout_user, is_authenticated functions remain the same)
# Make sure their indentation is correct

def login_user(username, password):
    users = get_users()
    if not users: # Add check in case get_users failed somehow
         st.error("Authentication system error: No users loaded.")
         return False
    # Check if the username exists and the password matches
    # Using .get() is safer in case the key is missing for some reason
    if username in users and users.get(username) == password:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.success("Logged In Successfully!")
        time.sleep(0.5) # Brief pause before rerunning
        st.rerun() # Rerun to hide login form and show app
        return True
    else:
        st.error("Incorrect username or password")
        return False

def show_login_form():
    """Displays the login form."""
    st.warning("⚠️ This is a demo login system. Do not use for production applications.", icon="🔒")
    users = get_users()
    if not users:
         # The error message is now printed within get_users if loading fails
         st.error("Failed to load user credentials. Check configuration and logs.")
         st.stop()

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            login_user(username, password)

def logout_user():
    """Logs the user out by clearing session state."""
    keys_to_delete = ["logged_in", "username"] # List of keys to remove
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    # Optionally clear other module-specific states if needed
    # e.g., del st.session_state['chat_messages']
    st.success("Logged out successfully.")
    time.sleep(1)
    st.rerun()

def is_authenticated():
    """Checks if the user is logged in."""
    return st.session_state.get("logged_in", False)