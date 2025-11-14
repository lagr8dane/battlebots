# ui/comparator_app.py
import streamlit as st
import pandas as pd
import json
import subprocess
import re
from app.comparator import ComparatorCoordinator
from app.config import MODEL_A_DEFAULT, MODEL_B_DEFAULT

# --- HELPER FUNCTIONS ---
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

# --- NEW DYNAMIC "SMART" FILTER ---
@st.cache_data(ttl=600)  # Cache the list for 10 minutes
def get_base_models_by_prefix():
    """
    Runs 'ollama list' and filters for models matching a known prefix.
    This filters out custom-named models.
    """
    # These are the "base" models we want to compare
    BASE_MODEL_PREFIXES = ["llama3", "mistral", "phi3"]
    
    models = []
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        lines = result.stdout.strip().split('\n')
        
        if len(lines) <= 1:
            return ["Error: 'ollama list' is empty"]

        # Parse the table, skipping the header
        for line in lines[1:]:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 1:
                name = parts[0]
                # Check if the model name starts with any of our allowed prefixes
                if any(name.startswith(prefix) for prefix in BASE_MODEL_PREFIXES):
                    models.append(name)
                        
    except FileNotFoundError:
        return ["Error: 'ollama' command not found."]
    except Exception as e:
        return [f"Error parsing models: {e}"]
    
    if not models:
        return ["No base models found (llama3, mistral, phi3)"]
        
    return sorted(models)
# --- END OF NEW FUNCTION ---


# --- Page Config ---
st.set_page_config(layout="wide", page_title="Model Comparator")
st.title("🤖 Model A/B Test")
st.caption("One Prompt, Two Responses, One Critic")

# --- Initialize Coordinator ---
@st.cache_resource
def get_coordinator():
    return ComparatorCoordinator()

coordinator = get_coordinator()

# --- Initialize State ---
if 'response_a' not in st.session_state: st.session_state.response_a = ""
if 'response_b' not in st.session_state: st.session_state.response_b = ""
if 'metrics_a' not in st.session_state: st.session_state.metrics_a = BLANK_METRICS
if 'metrics_b' not in st.session_state: st.session_state.metrics_b = BLANK_METRICS
if 'critique_report' not in st.session_state: st.session_state.critique_report = {}
if 'critique_raw' not in st.session_state: st.session_state.critique_raw = ""
if 'metrics_critique' not in st.session_state: st.session_state.metrics_critique = BLANK_METRICS

# --- THE LIST IS NOW DYNAMIC AND FILTERED ---
AVAILABLE_MODELS = get_base_models_by_prefix()
# ---

# --- Sidebar Controls ---
with st.sidebar:
    st.header("1. User Prompt")
    user_prompt = st.text_area("Enter your prompt here:", height=150, 
                               value="Explain the theory of relativity like I'm a 10-year-old.")
    st.divider()
    st.header("2. Model Configuration")
    
    # Check if model loading failed
    if "Error:" in AVAILABLE_MODELS[0] or "No base models found" in AVAILABLE_MODELS[0]:
        st.error(f"Failed to load models: {AVAILABLE_MODELS[0]}")
        # Stop the sidebar from rendering further
        st.stop()
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Model A")
            # Try to default to llama3, else just pick the first one
            default_index_a = 0
            if "llama3:8b" in AVAILABLE_MODELS:
                default_index_a = AVAILABLE_MODELS.index("llama3:8b")
            model_a_name = st.selectbox("Select Model A", AVAILABLE_MODELS, index=default_index_a)
            persona_a_text = st.text_area("Persona A (Optional System Prompt)", height=100, 
                                          placeholder="e.g., You are a helpful assistant.")
        with col2:
            st.subheader("Model B")
            # Try to default to mistral, else pick the second one
            default_index_b = 1 if len(AVAILABLE_MODELS) > 1 else 0
            if "mistral:7b" in AVAILABLE_MODELS:
                default_index_b = AVAILABLE_MODELS.index("mistral:7b")
            model_b_name = st.selectbox("Select Model B", AVAILABLE_MODELS, index=default_index_b)
            persona_b_text = st.text_area("Persona B (Optional System Prompt)", height=100, 
                                          placeholder="e.g., You are a sarcastic pirate.")
        st.divider()
        st.header("3. Run")
        
        if st.button("Generate & Compare", type="primary"):
            st.session_state.response_a = ""
            st.session_state.response_b = ""
            st.session_state.metrics_a = BLANK_METRICS
            st.session_state.metrics_b = BLANK_METRICS
            st.session_state.critique_report = {}
            st.session_state.critique_raw = ""
            st.session_state.metrics_critique = BLANK_METRICS
            
            with st.status("Running comparison...", expanded=True) as status:
                status.update(label="Generating responses for Model A and B...")
                res_a, res_b = coordinator.run_comparison(
                    user_prompt, model_a_name, persona_a_text, model_b_name, persona_b_text
                )
                st.session_state.response_a = res_a.get("response", f"Error: {res_a.get('error')}")
                st.session_state.metrics_a = res_a.get("metrics", BLANK_METRICS)
                st.session_state.response_b = res_b.get("response", f"Error: {res_b.get('error')}")
                st.session_state.metrics_b = res_b.get("metrics", BLANK_METRICS)
                status.update(label="Responses generated. Critic is analyzing...")

                critique_data = coordinator.run_critique(
                    user_prompt, 
                    model_a_name, st.session_state.response_a, st.session_state.metrics_a,
                    model_b_name, st.session_state.response_b, st.session_state.metrics_b
                )
                
                st.session_state.critique_report = critique_data.get("critique_report", {"verdict": "Critic failed."})
                st.session_state.critique_raw = critique_data.get("raw_critique", "")
                st.session_state.metrics_critique = critique_data.get("metrics", BLANK_METRICS)
                status.update(label="Comparison complete!", state="complete")

# --- Main Display Area ---
if st.session_state.critique_report:
    st.header("👨‍⚖️ Critic's Verdict")
    report = st.session_state.critique_report
    
    st.info(report.get("verdict", "No verdict provided."))
    
    if report.get("reasons"):
        st.subheader("Analysis & Reasons")
        st.markdown(report.get("reasons"))
        
    if report.get("scores"):
        st.subheader("Scores")
        st.code(report.get("scores"), language="text")

    if report.get("advice"):
        st.subheader("Advice")
        st.markdown(report.get("advice"))

    with st.expander("Show Critic's Performance & Raw Output"):
        render_metrics_dashboard(st.session_state.metrics_critique)
        st.markdown("---")
        st.markdown("##### Raw Critic Output")
        st.code(st.session_state.critique_raw, language="xml")
    st.divider()

col1, col2 = st.columns(2)
with col1:
    st.header(f"Response A ({model_a_name})")
    st.markdown(st.session_state.response_a)
    with st.expander("Show Metrics for Model A"):
        render_metrics_dashboard(st.session_state.metrics_a)

with col2:
    st.header(f"Response B ({model_b_name})")
    st.markdown(st.session_state.response_b)
    with st.expander("Show Metrics for Model B"):
        render_metrics_dashboard(st.session_state.metrics_b)
