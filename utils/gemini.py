import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time # For potential rate limiting

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

# --- Gemini API Configuration ---
# Use a simple flag to avoid configuring multiple times per run
if 'gemini_configured' not in st.session_state:
    st.session_state['gemini_configured'] = False

def configure_gemini():
    """Configures the Gemini API using the key from st.secrets or environment."""
    if st.session_state.get('gemini_configured', False):
        return True # Already configured

    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Gemini API Key not found. Please set it in `.streamlit/secrets.toml` or as an environment variable `GEMINI_API_KEY`.")
        st.stop()
        return False # Stop execution if key is missing

    try:
        genai.configure(api_key=api_key)
        # Optional: Test connectivity lightly (listing models can consume quota)
        # models = genai.list_models()
        # print("Available Gemini Models:", [m.name for m in models])
        st.session_state['gemini_configured'] = True
        print("Gemini configured successfully.") # Log to console
        return True
    except Exception as e:
        st.error(f"Fatal Error configuring Gemini: {e}")
        st.session_state['gemini_configured'] = False
        st.stop() # Stop execution on configuration failure
        return False

def get_gemini_model(model_name="gemini-1.5-flash"):
    """Initializes and returns a specific Gemini model."""
    if not st.session_state.get('gemini_configured', False):
        if not configure_gemini(): # Attempt to configure if not already
             return None # Return None if configuration fails

    try:
        # Add safety settings if desired
        # safety_settings = [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        # ]
        model = genai.GenerativeModel(
            model_name
            # safety_settings=safety_settings
        )
        return model
    except Exception as e:
        st.error(f"Error initializing Gemini model ({model_name}): {e}")
        return None

def generate_response(prompt, model_name="gemini-1.5-flash", **kwargs):
    """Generates a response from the Gemini model with error handling."""
    model = get_gemini_model(model_name)
    if not model:
        return "AI Model could not be initialized. Check configuration and API key."

    # Basic rate limiting check (example, adjust as needed)
    # last_call_time = st.session_state.get('last_gemini_call', 0)
    # if time.time() - last_call_time < 1: # Limit to 1 call per second
    #     time.sleep(1 - (time.time() - last_call_time))
    # st.session_state['last_gemini_call'] = time.time()

    try:
        # Allow passing generation config parameters like temperature
        generation_config = genai.types.GenerationConfig(
            # candidate_count=1, # Default is 1
            # stop_sequences=['\n'],
             max_output_tokens=kwargs.get('max_output_tokens', 2048),
             temperature=kwargs.get('temperature', 0.7), # Default temp
             top_p=kwargs.get('top_p', None),
             top_k=kwargs.get('top_k', None),
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            # safety_settings=... # Could apply here too
            )

        # More robust checking of response structure
        if response.parts:
            # Handle potential multi-part responses if necessary, usually just take text
            return "".join(part.text for part in response.parts if hasattr(part, 'text'))
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
            block_reason = response.prompt_feedback.block_reason.name
            block_message = f"Content blocked due to: {block_reason}."
            # Optionally include details about ratings if available
            safety_ratings = response.prompt_feedback.safety_ratings
            if safety_ratings:
                 block_message += f" Ratings: { {rating.category.name: rating.probability.name for rating in safety_ratings} }"
            st.warning(block_message)
            return f"Blocked due to: {block_reason}. Please adjust your input."
        else:
            # Handle cases where generation finishes without error but yields no parts (rare)
            finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            st.warning(f"No content generated. Finish Reason: {finish_reason}")
            return "No content was generated by the AI. This might be due to safety filters or an unexpected issue."

    except google.api_core.exceptions.ResourceExhausted as e:
         st.error(f"API Quota Exceeded: {e}. Please check your Gemini usage limits or try again later.")
         return "Error: API quota limit reached."
    except Exception as e:
        st.error(f"Error generating response from Gemini: {e}")
        # Log the full error for debugging if needed
        # print(f"Gemini Error Traceback: {traceback.format_exc()}")
        return "An error occurred while contacting the AI model."

# Example Usage (can be tested independently)
if __name__ == "__main__":
    # To run this directly:
    # 1. Make sure .env file exists with GEMINI_API_KEY or set it as env var
    # 2. Run `python utils/gemini.py`
    print("Testing Gemini Connection...")
    test_prompt = "Explain the basic function of an AC expansion valve in one sentence."
    response = generate_response(test_prompt)
    print(f"Prompt: {test_prompt}")
    print(f"Response: {response}")