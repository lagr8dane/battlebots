# app/config.py

# --- Model Definitions ---
# MODEL_MIKE and MODEL_JIMMY are no longer needed here.
# The UI will let you select any model.
MODEL_CRITIC = "critic:7b"

# --- Temperatures ---
# These are the new variables that were causing the error
TEMP_PRO_DEFAULT = 0.4
TEMP_CON_DEFAULT = 0.7
TEMP_CRITIC = 0.3

# --- Generation & Timeout Caps ---
CAPS_WARMUP = {"num_predict": 5, "timeout": 60}
CAPS_BASELINE = {"num_predict": 500, "timeout": 60}
CAPS_EXCHANGE = {"num_predict": 500, "timeout": 60}
CAPS_FINALIZE = {"num_predict": 700, "timeout": 90}
CAPS_REPAIR = {"num_predict": 400, "timeout": 45}

# --- NEW CONFIG FOR COMPARATOR APP ---
MODEL_A_DEFAULT = "mike:debater" # This is fine, comparator can have its own defaults
MODEL_B_DEFAULT = "mistral:7b"
MODEL_COMPARATOR = "critic:7b"

CAPS_COMPARISON = {"num_predict": 1000, "timeout": 120} 
CAPS_CRITIQUE = {"num_predict": 700, "timeout": 90}
