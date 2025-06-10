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
from utils.gemini import generate_response
import datetime

MODULE_TITLE = "🔮 Predictive Maintenance Suggestions"

def show_predictive_maintenance():
    st.subheader(MODULE_TITLE)
    st.caption("Enter AC unit details to receive AI-generated potential maintenance suggestions based on common failure patterns.")
    st.warning("Disclaimer: These are AI-generated suggestions based on general knowledge and inputs, NOT guarantees of failure or replacements for professional inspection.", icon="⚠️")
    st.markdown("---")

    with st.form("predictive_maint_form"):
        st.write("**Equipment Information:**")
        ac_model = st.text_input("AC Unit Model (e.g., Carrier 24ABC6)")
        ac_age = st.number_input("Age of Unit (Years)", min_value=0, max_value=50, step=1, value=10)

        st.write("**Service History & Observations:**")
        # Calculate default last service date (e.g., 1 year ago)
        today = datetime.date.today()
        default_last_service = today - datetime.timedelta(days=365)
        last_service_date = st.date_input("Date of Last Known Service", value=default_last_service)
        years_since_service = (today - last_service_date).days / 365.25 if last_service_date else None

        known_issues = st.text_area("Any known past repairs or current observations?", placeholder="e.g., Had capacitor replaced 2 years ago. Sometimes makes a humming noise on startup.")
        usage_pattern = st.selectbox("Estimated Usage Pattern:", ["Average Residential", "High Usage (e.g., server room, hot climate)", "Low Usage (e.g., vacation home)"])

        submitted = st.form_submit_button("Get Maintenance Suggestions")

        if submitted:
            # Basic validation
            if ac_age < 0:
                st.error("Please enter a valid age for the unit (0 or greater).")
            else:
                # Construct prompt for Gemini
                prompt = f"""
                Act as an experienced HVAC technician providing preventative maintenance advice based *only* on the provided information and general knowledge of common AC component lifespans and failure modes.

                **Do NOT predict specific failures or dates.** Focus on recommending *inspections* or *potential preventative actions* based on age, known issues, and usage.

                **Unit Information:**
                - Model: {ac_model if ac_model else 'Not Specified'}
                - Age: {ac_age} years old
                - Last Known Service: {last_service_date.strftime('%Y-%m-%d') if last_service_date else 'Unknown'} ({f'{years_since_service:.1f} years ago' if years_since_service is not None else 'Unknown'})
                - Known Issues/Observations: {known_issues if known_issues else 'None reported'}
                - Usage Pattern: {usage_pattern}

                **Task:** Based *only* on the above, provide a bulleted list of potential preventative maintenance checks or suggestions suitable for this unit. Prioritize suggestions based on likelihood for a unit of this age and profile. Explain *why* each check is relevant (e.g., "Capacitors often degrade after X years..."). Keep suggestions actionable for a technician visit.

                **Example Format:**
                *   **Check Capacitor:** Capacitors are common failure points, especially in units over 5-7 years old. Recommend testing capacitance values.
                *   **Inspect Contactor:** Check for pitting or burning on the contact points, common with age and usage.
                *   **Clean Coils:** Dirty coils reduce efficiency and strain the system, especially important given the age/usage. Recommend checking both evaporator and condenser coils.
                *   **Monitor Refrigerant Charge:** While leaks aren't assumed, verifying charge is good practice during maintenance, especially if past issues were noted.
                *   [Add other relevant points based on input]

                **Output:**
                Provide only the bulleted list of suggestions and their brief justifications.
                """

                with st.spinner("Analyzing unit profile and generating suggestions..."):
                    # Slightly higher temperature might allow for more nuanced suggestions
                    suggestions = generate_response(prompt, temperature=0.6)

                st.markdown("#### AI-Generated Maintenance Suggestions:")
                st.info(suggestions) # Display suggestions in an info box