# app/user_config.py
import json
import os
import streamlit as st

# We'll store our user's last-used settings here
CONFIG_FILE = "config/debate_defaults.json"

def load_user_defaults():
    """
    Tries to load the user's last-used models from a JSON file.
    If the file doesn't exist or is corrupt, returns empty defaults.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
            return {} # Return empty dict on error
    return {} # Return empty dict if file doesn't exist

def save_user_defaults():
    """
    This is a callback function. It saves the current selections 
    from st.session_state to the JSON file.
    """
    # Ensure the config directory exists
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    # Get all the keys we want to save
    keys_to_save = [
        "model_pro", "temp_pro", "persona_pro",
        "pro_tone", "pro_style", "pro_formality", "pro_complexity",
        "model_con", "temp_con", "persona_con",
        "con_tone", "con_style", "con_formality", "con_complexity"
    ]
    
    current_config = load_user_defaults()

    # Update the config with all current values from session state
    for key in keys_to_save:
        if key in st.session_state:
            current_config[key] = st.session_state[key]
    
    # Write the new config back to the file
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(current_config, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save user defaults: {e}")
