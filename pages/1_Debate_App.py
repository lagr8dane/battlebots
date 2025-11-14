# pages/1_Debate_App.py
import streamlit as st
import pandas as pd
import json
import time
import subprocess
import re
from datetime import datetime
from app.coordinator import DebateCoordinator 
from app.coordinator import BLANK_METRICS
from app.config import TEMP_PRO_DEFAULT, TEMP_CON_DEFAULT 
from app.user_config import load_user_defaults, save_user_defaults

# --- Page Config ---
st.set_page_config(page_title="Battle of the Bots", layout="wide")
st.title("🤖 Battle of the Bots")
st.caption("Offline debate analysis with Ollama")

# --- HELPER FUNCTIONS ---
@st.cache_data(ttl=60)
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

def get_transcript_json() -> str:
    transcript = {
        "topic": st.session_state.topic,
        "debate_config": {
            "model_pro": st.session_state.model_pro,
            "temp_pro": st.session_state.temp_pro,
            "persona_pro": st.session_state.persona_pro,
            "style_pro": {
                "tone": st.session_state.pro_tone,
                "style": st.session_state.pro_style,
                "formality": st.session_state.pro_formality,
                "complexity": st.session_state.pro_complexity
            },
            "model_con": st.session_state.model_con,
            "temp_con": st.session_state.temp_con,
            "persona_con": st.session_state.persona_con,
            "style_con": {
                "tone": st.session_state.con_tone,
                "style": st.session_state.con_style,
                "formality": st.session_state.con_formality,
                "complexity": st.session_state.con_complexity
            },
            "force_adversarial": st.session_state.force_adversarial,
        },
        "history": st.session_state.debate_history,
        "finals": st.session_state.final_outputs,
        "critic_report": st.session_state.critic_report
    }
    return json.dumps(transcript, indent=2)
# --- END HELPER FUNCTIONS ---


# --- Initialize Coordinator ---
@st.cache_resource
def get_coordinator():
    return DebateCoordinator()

coordinator = get_coordinator()

# --- State Initialization ---
def init_session_state():
    local_models = get_local_models()
    if not local_models:
        st.error("No local Ollama models found. Please pull a model in the 'Model Explorer'.")
        st.stop()
        
    user_defaults = load_user_defaults()
    
    # Check if the saved PRO model still exists
    default_pro = user_defaults.get("model_pro", "llama3:8b")
    if default_pro not in local_models:
        default_pro = local_models[0] # Fallback to first model
        
    # Check if the saved CON model still exists
    default_con = user_defaults.get("model_con", "mistral:7b")
    if default_con not in local_models:
        default_con = local_models[1] if len(local_models) > 1 else local_models[0] # Fallback to second model
    
    defaults = {
        'topic': "AI will create more jobs than it destroys",
        'debate_history': [], 
        'final_outputs': None,
        'critic_report': None,
        'running': False,
        'warmup_complete': False,
        'force_adversarial': True,
        
        'model_pro': default_pro,
        'temp_pro': user_defaults.get("temp_pro", TEMP_PRO_DEFAULT),
        'persona_pro': user_defaults.get("persona_pro", "You are an optimistic, data-driven, and visionary technologist."),
        'pro_tone': user_defaults.get("pro_tone", "Assertive"),
        'pro_style': user_defaults.get("pro_style", "Logical"),
        'pro_formality': user_defaults.get("pro_formality", "Professional"),
        'pro_complexity': user_defaults.get("pro_complexity", "Standard"),
        
        'model_con': default_con,
        'temp_con': user_defaults.get("temp_con", TEMP_CON_DEFAULT),
        'persona_con': user_defaults.get("persona_con", "You are a cautious, pragmatic, and humanist philosopher."),
        'con_tone': user_defaults.get("con_tone", "Assertive"),
        'con_style': user_defaults.get("con_style", "Logical"),
        'con_formality': user_defaults.get("con_formality", "Professional"),
        'con_complexity': user_defaults.get("con_complexity", "Standard"),
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Callbacks ---
def cb_run_baselines():
    if not st.session_state.topic:
        st.toast("🚨 Please enter a topic first!", icon="error")
        return
    st.session_state.running = True
    st.session_state.debate_history = []
    st.session_state.final_outputs = None
    st.session_state.critic_report = None
    
    with st.status("Running...", expanded=True) as status:
        if not st.session_state.warmup_complete:
            status.update(label="Warming up models (one-time)...")
            warmup_results = coordinator.warm_up_models(
                st.session_state.model_pro, st.session_state.model_con
            )
            st.session_state.warmup_complete = True
            st.toast("Models are warmed up!", icon="🔥")
            for key, res in warmup_results.items():
                if "FAIL" in res:
                    status.update(label="Warmup Failed!", state="error")
                    st.error(f"Failed to warm up {key}: {res}")
                    st.session_state.running = False
                    return

        status.update(label="Generating baselines...")
        
        style_pro = {
            "tone": st.session_state.pro_tone, "style": st.session_state.pro_style,
            "formality": st.session_state.pro_formality, "complexity": st.session_state.pro_complexity
        }
        style_con = {
            "tone": st.session_state.con_tone, "style": st.session_state.con_style,
            "formality": st.session_state.con_formality, "complexity": st.session_state.con_complexity
        }
        
        mike_base, metrics_mike, jimmy_base, metrics_jimmy = coordinator.generate_baselines(
            st.session_state.topic,
            st.session_state.force_adversarial,
            st.session_state.model_pro, st.session_state.temp_pro, st.session_state.persona_pro, style_pro,
            st.session_state.model_con, st.session_state.temp_con, st.session_state.persona_con, style_con
        )
        st.session_state.debate_history = [{
            "round": 0,
            "mike_capsule": {"topic": st.session_state.topic, "my_side": "PRO"},
            "mike_output": mike_base, "mike_metrics": metrics_mike, 
            "jimmy_capsule": {"topic": st.session_state.topic, "my_side": "CON"},
            "jimmy_output": jimmy_base, "jimmy_metrics": metrics_jimmy
        }]
        status.update(label="Baselines generated!", state="complete")
    
    st.session_state.running = False

def cb_run_exchange():
    st.session_state.running = True
    last_round = st.session_state.debate_history[-1]
    
    with st.status(f"Running exchange round {len(st.session_state.debate_history)}...", expanded=True) as status:
        
        style_pro = {
            "tone": st.session_state.pro_tone, "style": st.session_state.pro_style,
            "formality": st.session_state.pro_formality, "complexity": st.session_state.pro_complexity
        }
        style_con = {
            "tone": st.session_state.con_tone, "style": st.session_state.con_style,
            "formality": st.session_state.con_formality, "complexity": st.session_state.con_complexity
        }
        
        capsule_mike, mike_output, metrics_mike, capsule_jimmy, jimmy_output, metrics_jimmy = coordinator.exchange_step(
            st.session_state.topic, 
            last_round["mike_output"], 
            last_round["jimmy_output"],
            st.session_state.force_adversarial,
            st.session_state.model_pro, st.session_state.temp_pro, st.session_state.persona_pro, style_pro,
            st.session_state.model_con, st.session_state.temp_con, st.session_state.persona_con, style_con
        )
        st.session_state.debate_history.append({
            "round": len(st.session_state.debate_history),
            "mike_capsule": capsule_mike,
            "mike_output": mike_output, "mike_metrics": metrics_mike,
            "jimmy_capsule": capsule_jimmy,
            "jimmy_output": jimmy_output, "jimmy_metrics": metrics_jimmy
        })
        status.update(label=f"Round {len(st.session_state.debate_history)-1} complete!", state="complete")
        
    st.session_state.running = False

def cb_run_finalize():
    st.session_state.running = True
    st.session_state.final_outputs = None
    st.session_state.critic_report = None
    
    with st.status("Finalizing debate...", expanded=True) as status:
        status.update(label="Generating final statements...")
        
        style_pro = {
            "tone": st.session_state.pro_tone, "style": st.session_state.pro_style,
            "formality": st.session_state.pro_formality, "complexity": st.session_state.pro_complexity
        }
        style_con = {
            "tone": st.session_state.con_tone, "style": st.session_state.con_style,
            "formality": st.session_state.con_formality, "complexity": st.session_state.con_complexity
        }
        
        mike_final, metrics_mike, jimmy_final, metrics_jimmy = coordinator.finalize_debate(
            st.session_state.topic, 
            st.session_state.debate_history,
            st.session_state.persona_pro,
            st.session_state.model_pro,
            st.session_state.temp_pro,
            style_pro,
            st.session_state.persona_con,
            st.session_state.model_con,
            st.session_state.temp_con,
            style_con
        )
        st.session_state.final_outputs = {
            "mike": mike_final, "mike_metrics": metrics_mike,
            "jimmy": jimmy_final, "jimmy_metrics": metrics_jimmy
        }
    
        status.update(label="Running critic audits...")
        transcript = json.loads(get_transcript_json()) 
        report = coordinator.run_critic(transcript) 
        st.session_state.critic_report = report
        
        status.update(label="Debate finalized and scored!", state="complete")
        
    st.session_state.running = False


# --- UI Layout (Sidebar UPDATED) ---
with st.sidebar:
    st.header("1. Configuration")
    
    st.text_area("Debate Topic", key="topic", height=100, on_change=save_user_defaults)
    
    st.checkbox("Force Adversarial Stance (Permission to Lie)", key="force_adversarial",
                help="If checked, models are given a strong instruction to "
                     "defend their side, even if it's factually wrong. ",
                on_change=save_user_defaults)
    
    st.divider()
    
    st.header("2. Debate Controls")
    st.button("Generate Baselines", on_click=cb_run_baselines, disabled=st.session_state.running, use_container_width=True)
    if st.session_state.debate_history:
        st.button("Continue Exchange", on_click=cb_run_exchange, disabled=st.session_state.running, use_container_width=True)
        st.button("Finalize & Score", on_click=cb_run_finalize, disabled=st.session_state.running, use_container_width=True)
    
    st.divider()
    
    st.header("3. Debater Personas")

    AVAILABLE_MODELS = get_local_models()
    if not AVAILABLE_MODELS:
        st.error("No local Ollama models found. Pull models in the 'Model Explorer'.")
        st.stop()

    with st.expander("PRO Debater Persona & Style", expanded=True):
        
        # --- THIS IS THE FIX ---
        pro_index = AVAILABLE_MODELS.index(st.session_state.model_pro) if st.session_state.model_pro in AVAILABLE_MODELS else 0
        st.selectbox("Select PRO Model", AVAILABLE_MODELS, key="model_pro", 
                     index=pro_index, on_change=save_user_defaults)
        # --- END OF FIX ---
        
        st.slider("PRO Temperature", 0.0, 2.0, step=0.1, key="temp_pro",
                  help="Controls creativity & randomness. 0.0 is deterministic, 2.0 is very random.",
                  on_change=save_user_defaults)
        st.text_area("PRO Persona Text", key="persona_pro", height=75, on_change=save_user_defaults,
                     help="A general description of the persona (e.g., 'You are a cautious philosopher...'). This is used for all rounds.")
        st.select_slider("Tone", 
                         options=["Deferential", "Polite", "Assertive", "Aggressive", "Sarcastic"], 
                         key="pro_tone", help="Controls the attitude and emotional style.",
                         on_change=save_user_defaults)
        st.select_slider("Argument Style", 
                         options=["Emotional", "Logical", "Data-driven"], 
                         key="pro_style", help="Controls the substance of the argument.",
                         on_change=save_user_defaults)
        st.select_slider("Formality", 
                         options=["Casual", "Professional", "Academic"], 
                         key="pro_formality", help="Controls the vocabulary and writing style.",
                         on_change=save_user_defaults)
        st.select_slider("Reasoning Complexity", 
                         options=["Superficial", "Standard", "Complex"], 
                         key="pro_complexity", help="Controls the depth of the argument.",
                         on_change=save_user_defaults)

    with st.expander("CON Debater Persona & Style", expanded=True):
        
        # --- THIS IS THE FIX ---
        con_index = AVAILABLE_MODELS.index(st.session_state.model_con) if st.session_state.model_con in AVAILABLE_MODELS else 0
        st.selectbox("Select CON Model", AVAILABLE_MODELS, key="model_con", 
                     index=con_index, on_change=save_user_defaults)
        # --- END OF FIX ---
        
        st.slider("CON Temperature", 0.0, 2.0, step=0.1, key="temp_con",
                  help="Controls creativity & randomness. 0.0 is deterministic, 2.0 is very random.",
                  on_change=save_user_defaults)
        st.text_area("CON Persona Text", key="persona_con", height=75, on_change=save_user_defaults,
                     help="A general description of the persona (e.g., 'You are a cautious philosopher...'). This is used for all rounds.")
        st.select_slider("Tone", 
                         options=["Deferential", "Polite", "Assertive", "Aggressive", "Sarcastic"], 
                         key="con_tone", help="Controls the attitude and emotional style.",
                         on_change=save_user_defaults)
        st.select_slider("Argument Style", 
                         options=["Emotional", "Logical", "Data-driven"], 
                         key="con_style", help="Controls the substance of the argument.",
                         on_change=save_user_defaults)
        st.select_slider("Formality", 
                         options=["Casual", "Professional", "Academic"], 
                         key="con_formality", help="Controls the vocabulary and writing style.",
                         on_change=save_user_defaults)
        st.select_slider("Reasoning Complexity", 
                         options=["Superficial", "Standard", "Complex"], 
                         key="con_complexity", help="Controls the depth of the argument.",
                         on_change=save_user_defaults)

# --- Main Panel: Debate Display ---
if st.session_state.final_outputs:
    st.header("🏆 Final Arguments & Report")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"PRO ({st.session_state.model_pro})")
        st.info(st.session_state.final_outputs["mike"].get("final", "*Missing*"))
        if st.session_state.final_outputs["mike"].get("side_mismatch"): st.warning("⚠️ Side Mismatch!")
        if st.session_state.final_outputs["mike"].get("error"): st.error(st.session_state.final_outputs["mike"]["error"])
        with st.expander("Show Final Metrics"):
            render_metrics_dashboard(st.session_state.final_outputs.get("mike_metrics", BLANK_METRICS))

    with col2:
        st.subheader(f"CON ({st.session_state.model_con})")
        st.info(st.session_state.final_outputs["jimmy"].get("final", "*Missing*"))
        if st.session_state.final_outputs["jimmy"].get("side_mismatch"): st.warning("⚠️ Side Mismatch!")
        if st.session_state.final_outputs["jimmy"].get("error"): st.error(st.session_state.final_outputs["jimmy"]["error"])
        with st.expander("Show Final Metrics"):
            render_metrics_dashboard(st.session_state.final_outputs.get("jimmy_metrics", BLANK_METRICS))
            
    st.divider()

    st.header("👨‍⚖️ Critic's Report")
    if st.session_state.critic_report:
        report = st.session_state.critic_report
        st.subheader("Verdict")
        st.info(report.get("verdict", "Critic failed to return a verdict."))
        
        st.subheader("Drift Audit")
        drift_report = report.get("drift_audit", {})
        col1, col2 = st.columns(2)
        col1.metric("PRO Side Mismatches", drift_report.get("total_pro_mismatches", 0))
        col2.metric("CON Side Mismatches", drift_report.get("total_con_mismatches", 0))

        st.subheader("Hallucination Scan")
        hallucination_report = report.get("hallucination_audit", {})
        if "error" in hallucination_report:
            st.error(f"Hallucination scan failed: {hallucination_report['error']}")
        else:
            fabrications = hallucination_report.get("potential_fabrications", [])
            if not fabrications:
                st.success("No potential fabrications detected.")
            else:
                st.warning(f"Detected {len(fabrications)} potential fabrications:")
                for fab in fabrications: st.markdown(f"- `{fab}`")
    else:
        st.error("Critic report was not generated.")
    
    st.divider()
    st.header("Export")
    st.download_button("Download Full Transcript (JSON)", get_transcript_json(), f"battle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "application/json")

st.divider()

if st.session_state.debate_history:
    st.header("Debate History")
    
    for round_data in st.session_state.debate_history:
        round_num = round_data["round"]
        st.subheader(f"Round {round_num}: {'Baselines' if round_num == 0 else 'Exchange'}")

        with st.chat_message(f"PRO ({st.session_state.model_pro})"):
            mike_output = round_data["mike_output"]
            if mike_output.get("error"): st.error(mike_output.get("error"))
            elif mike_output.get("side_mismatch"):
                protest_text = mike_output.get("side_confirm", "")
                if protest_text and protest_text.upper() not in ["PRO", "MISSING", ""]:
                    st.warning(f"⚠️ **Model Protest Detected!** (Side: PRO)", icon="🗣️")
                    st.markdown(f"> **Model's 'Side':** *{protest_text}*")
                else:
                    st.warning("⚠️ Side Mismatch! (Tag was missing or wrong)")
            
            st.markdown(mike_output.get("reasoning", "*No reasoning provided.*"))
            
            with st.expander("Show PRO's Debug Info"):
                render_metrics_dashboard(round_data.get("mike_metrics", BLANK_METRICS))
                st.markdown("---")
                st.markdown("##### Capsule (Input)")
                st.json(round_data["mike_capsule"])
                st.markdown("##### Raw Output")
                st.code(mike_output.get("raw_output", ""), language="xml")

        with st.chat_message(f"CON ({st.session_state.model_con})"):
            jimmy_output = round_data["jimmy_output"]
            if jimmy_output.get("error"): st.error(jimmy_output.get("error"))
            elif jimmy_output.get("side_mismatch"):
                protest_text = jimmy_output.get("side_confirm", "")
                if protest_text and protest_text.upper() not in ["CON", "MISSING", ""]:
                    st.warning(f"⚠️ **Model Protest Detected!** (Side: CON)", icon="🗣️")
                    st.markdown(f"> **Model's 'Side':** *{protest_text}*")
                else:
                    st.warning("⚠️ Side Mismatch! (Tag was missing or wrong)")
            
            st.markdown(jimmy_output.get("reasoning", "*No reasoning provided.*"))
            
            with st.expander("Show CON's Debug Info"):
                render_metrics_dashboard(round_data.get("jimmy_metrics", BLANK_METRICS))
                st.markdown("---")
                st.markdown("##### Capsule (Input)")
                st.json(round_data["jimmy_capsule"])
                st.markdown("##### Raw Output")
                st.code(jimmy_output.get("raw_output", ""), language="xml")
        
        st.divider()
else:
    st.info("Enter a topic and click 'Generate Baselines' to start.")
