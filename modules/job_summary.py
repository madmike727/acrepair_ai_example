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

MODULE_TITLE = "✍️ Automated Job Summary Generator"

def show_job_summary():
    st.subheader(MODULE_TITLE)
    st.caption("Enter raw technician notes below to generate a structured summary for invoices or records.")
    st.markdown("---")

    notes_placeholder = """Example:
Arrived 10:15 AM. Customer: Jane Doe, 123 Main St. Complaint: AC not cooling, blowing warm air.
Checked thermostat - set correctly.
Checked filter - extremely dirty, blocked airflow. Replaced filter (customer provided).
Checked outdoor unit - condenser coils very dirty. Cleaned coils with approved cleaner.
Checked refrigerant pressures - slightly low on suction side (R410a system). Added 0.5 lbs R410a.
Checked temperature split after service - 18 degrees delta T. System cooling properly now.
Advised customer on importance of regular filter changes (monthly recommended) and annual maintenance.
Departed 11:30 AM.
"""
    notes = st.text_area(
        "Paste or Type Technician Notes Here:",
        height=250,
        placeholder=notes_placeholder,
        key="job_summary_notes"
        )

    st.markdown("---")
    st.write("Select Summary Style:")
    summary_style = st.radio(
        "Choose Format:",
        ("Standard Invoice Summary", "Detailed Internal Log", "Brief Customer Text"),
        key="summary_style",
        horizontal=True
    )

    if st.button("Generate Summary", key="generate_summary_button"):
        if notes:
            # Tailor the prompt based on the selected style
            if summary_style == "Standard Invoice Summary":
                prompt_instructions = """
                Generate a concise, professional job summary suitable for a customer invoice. Focus on:
                1. Customer Reported Issue
                2. Diagnosis/Findings (briefly)
                3. Work Performed (clearly list actions taken)
                4. Parts Used (if mentioned)
                5. Final System Status
                Keep it factual and customer-friendly. Avoid excessive technical jargon.
                """
            elif summary_style == "Detailed Internal Log":
                prompt_instructions = """
                Generate a detailed job summary for internal records. Include:
                1. Arrival/Departure Times (if mentioned)
                2. Customer Details (if mentioned)
                3. Detailed Customer Complaint
                4. Step-by-step Diagnostic Process
                5. Specific Findings (including measurements like pressures, temps if noted)
                6. Detailed Work Performed
                7. Parts Used (including quantities if noted)
                8. Recommendations Given to Customer
                9. Any observations about system condition (age, rust, etc. if mentioned)
                10. Final System Status & Tests Performed
                Be thorough and capture all relevant technical details from the notes.
                """
            else: # Brief Customer Text
                prompt_instructions = """
                Generate a very brief, friendly text message summary for the customer.
                Include:
                1. Confirmation the job is complete.
                2. The main issue found and fixed (simply put).
                3. Confirmation the AC is working now.
                Example: "Hi [Customer Name if possible], just letting you know we've finished the AC repair. We found a [main issue like dirty filter/low charge] and fixed it. Your AC is cooling again! - CoolBreeze AC"
                Adapt based on the notes. If no name, use a general greeting.
                """

            full_prompt = f"""
            **Task:** Transform the following raw technician notes into a specific job summary format.

            **Format Required:** {summary_style}

            **Instructions:**
            {prompt_instructions}

            **Raw Technician Notes:**
            ---
            {notes}
            ---

            **Generated Summary:**
            """

            with st.spinner("Generating Summary..."):
                # Use a slightly lower temperature for more factual summary generation
                summary = generate_response(full_prompt, temperature=0.3)

            st.markdown(f"#### Generated {summary_style}:")
            st.text_area("Summary Output:", value=summary, height=200, key="summary_output", help="You can copy this text.")
            # st.success(summary) # Alternative display using success box

        else:
            st.warning("Please enter technician notes first.")