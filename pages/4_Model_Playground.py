# pages/4_Model_Playground.py
import streamlit as st
import subprocess
import re
import pandas as pd
from app.runner import run_ollama
from app.config import CAPS_COMPARISON # We can re-use the 1000-token cap

# --- HELPER FUNCTIONS COPIED FROM OTHER APPS ---
# This makes the app self-contained and robust.

BLANK_METRICS = {
    "time_total_s": 0, "time_load_s": 0, "time_gen_s": 0,
    "tokens_in": 0, "tokens_out": 0, "tokens_per_s": 0
}

def render_metrics_dashboard(metrics: dict):
    """Displays a compact, human-readable dashboard of the model's performance."""
    if not metrics or metrics.get("tokens_per_s", 0) == 0:
        st.info("No metrics recorded for this run.")
        return
    
    summary = (
        f"**Summary:** Generated **{metrics.get('tokens_out', 0)} tokens** "
        f"at **{metrics.get('tokens_per_s', 0)} tok/s** "
        f"(took {metrics.get('time_gen_s', 0)}s to generate)."
    )
    st.markdown(summary)
    st.markdown("---")
    
    st.markdown("##### ⏱️ Performance Details")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gen. Speed (tok/s)", metrics.get("tokens_per_s", 0))
    col2.metric("Output Tokens", metrics.get("tokens_out", 0))
    col3.metric("Input Tokens", metrics.get("tokens_in", 0))
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Total Time (s)", metrics.get("time_total_s", 0))
    col5.metric("Gen. Time (s)", metrics.get("time_gen_s", 0))
    col6.metric("Load Time (s)", metrics.get("time_load_s", 0))

@st.cache_data(ttl=60) # Cache for 60 seconds
def get_local_models():
    """
    Runs 'ollama list' and returns a simple list of all model names.
    """
    model_names = []
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        lines = result.stdout.strip().split('\n')
        
        if len(lines) > 1:
            for line in lines[1:]:
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 1:
                    model_names.append(parts[0])
    except Exception as e:
        st.error(f"Error reading local models: {e}")
    return model_names
# --- END OF HELPER FUNCTIONS ---


# --- Page Config ---
st.set_page_config(page_title="Model Playground", layout="wide")
st.title("🧪 Model Playground")
st.caption("A simple app to test a single model and see its performance.")

# --- Initialize State ---
if 'playground_response' not in st.session_state:
    st.session_state.playground_response = ""
if 'playground_metrics' not in st.session_state:
    st.session_state.playground_metrics = BLANK_METRICS

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Configuration")
    
    # Get all local models for the dropdown
    AVAILABLE_MODELS = get_local_models()
    if not AVAILABLE_MODELS:
        st.error("No local Ollama models found. Please pull a model in the 'Model Explorer'.")
        st.stop()

    model_name = st.selectbox("Select a Model", AVAILABLE_MODELS, index=0,
                              help="Select any model you have installed locally.")
    
    persona = st.text_area("System Prompt / Persona (Optional)", height=150,
                           placeholder="e.g., You are a witty assistant who answers in rhymes.")

# --- Main Page ---
user_prompt = st.text_area("Your Prompt", height=200, 
                           placeholder="Enter your prompt here...")

if st.button("Generate Response", type="primary"):
    st.session_state.playground_response = ""
    st.session_state.playground_metrics = BLANK_METRICS
    
    if not user_prompt:
        st.warning("Please enter a prompt.")
    else:
        full_prompt = user_prompt
        if persona:
            full_prompt = f"{persona}\n\n---\n\n{user_prompt}"
            
        with st.status(f"Generating response with {model_name}...", expanded=True) as status:
            success, raw, metrics, err = run_ollama(
                model_name=model_name,
                prompt=full_prompt,
                temperature=0.5,
                **CAPS_COMPARISON # Re-use the 1000-token cap
            )
            
            if success:
                st.session_state.playground_response = raw
                st.session_state.playground_metrics = metrics
                status.update(label="Response complete!", state="complete")
            else:
                st.session_state.playground_response = f"Error: {err}"
                st.session_state.playground_metrics = metrics
                status.update(label="Error", state="error")

# --- Display Area ---
if st.session_state.playground_response:
    st.divider()
    st.header("Model Response")
    st.markdown(st.session_state.playground_response)
    
    with st.expander("Show Performance Metrics"):
        render_metrics_dashboard(st.session_state.playground_metrics)
