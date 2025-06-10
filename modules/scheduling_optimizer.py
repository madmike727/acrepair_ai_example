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

MODULE_TITLE = "📅 Scheduling Assistant (Conceptual)"

def show_scheduling_optimizer():
    st.subheader(MODULE_TITLE)
    st.caption("Enter job details and technician availability to get an AI-suggested schedule.")
    st.warning("⚠️ This tool provides AI-generated *suggestions* based on text input. It does **not** perform complex route optimization, skill matching, or real-time traffic analysis. Use as a starting point only.", icon="🤖")
    st.markdown("---")

    with st.form("schedule_assist_form"):
        st.write("**Scheduling Parameters:**")
        schedule_date = st.date_input("Date for Schedule", value=datetime.date.today())
        techs_available = st.text_area(
            "Technicians Available & Start/End Times (one per line):",
            placeholder="Tech A (John S.), 8 AM - 5 PM, Start Location: Office\nTech B (Maria G.), 9 AM - 6 PM, Start Location: North Zone",
            height=100
            )

        st.write("**Job List (add details relevant for scheduling):**")
        job_list = st.text_area(
            "Jobs to Schedule (one per line - include address/area, priority, estimated duration):",
            placeholder="Job 1: 123 Maple St, High Priority (No Cool), Est. 2 hrs\nJob 2: 456 Oak Ave (South Zone), Medium Priority (Maintenance), Est. 1.5 hrs\nJob 3: 789 Pine Ln (North Zone), Low Priority (Noise Check), Est. 1 hr",
            height=150
            )

        additional_constraints = st.text_area(
            "Additional Constraints or Notes:",
            placeholder="e.g., Customer for Job 1 only available after 1 PM. Tech A has specific part needed for Job 3. Avoid sending Tech B to Maple St area due to traffic closure."
        )

        submitted = st.form_submit_button("Suggest Schedule")

        if submitted:
            if not techs_available or not job_list:
                st.warning("Please provide technician availability and a list of jobs.")
            else:
                prompt = f"""
                Act as a scheduling assistant for an AC repair company. Based ONLY on the provided information, create a *suggested* daily schedule for the available technicians for {schedule_date.strftime('%Y-%m-%d')}.

                **Goal:** Assign jobs to technicians trying to logically group nearby jobs (if location info is provided) and respect priorities and time estimates. Acknowledge that this is a basic suggestion without real-time optimization.

                **Input Information:**
                *   **Technicians Available:**
                {techs_available}
                *   **Jobs to Schedule:**
                {job_list}
                *   **Additional Constraints/Notes:**
                {additional_constraints if additional_constraints else 'None'}

                **Task:**
                1.  Analyze the inputs.
                2.  Assign each job to a technician.
                3.  Provide a potential sequence of jobs for each technician, considering estimated durations and any location hints or constraints mentioned.
                4.  Format the output clearly, showing the schedule per technician.
                5.  Explicitly state if some jobs could not be scheduled or if constraints conflict.
                6.  Include a reminder that this is a *suggestion* and travel time is not precisely calculated.

                **Example Output Format:**

                **Suggested Schedule for {schedule_date.strftime('%Y-%m-%d')}**

                **Tech A (John S.) - 8 AM - 5 PM (Starts: Office)**
                *   8:30 AM - 9:30 AM: Job X (Location/Details) - Est. 1 hr (+ travel)
                *   10:00 AM - 11:30 AM: Job Y (Location/Details) - Est. 1.5 hrs (+ travel)
                *   ... (Lunch Break?) ...
                *   1:00 PM - 3:00 PM: Job Z (Location/Details) - Est. 2 hrs (+ travel)

                **Tech B (Maria G.) - 9 AM - 6 PM (Starts: North Zone)**
                *   9:15 AM - 10:45 AM: Job P (Location/Details) - Est. 1.5 hrs (+ travel)
                *   ... etc ...

                **Notes/Unscheduled:**
                *   [Mention any jobs that couldn't fit or conflicts found]
                *   Reminder: This schedule is a suggestion. Actual travel times and job durations may vary. Dispatcher should confirm.

                ---
                **Generate the suggested schedule based *only* on the provided inputs:**
                """

                with st.spinner("Generating schedule suggestion..."):
                    # Temperature might be lower here for more structured output
                    schedule_suggestion = generate_response(prompt, temperature=0.4)

                st.markdown("#### AI-Generated Schedule Suggestion:")
                st.text_area("Suggested Schedule:", value=schedule_suggestion, height=300, key="schedule_output", help="This is a conceptual schedule. Verify details before dispatching.")