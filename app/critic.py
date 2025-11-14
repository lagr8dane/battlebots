# app/critic.py
import json
import logging
from app.runner import run_ollama
from app.config import MODEL_CRITIC, TEMP_CRITIC, CAPS_REPAIR, CAPS_FINALIZE
from app.parsing import robust_extract_tag 

log = logging.getLogger(__name__)

# --- Critic Prompts ---
PROMPT_HALLUCINATION_AUDIT = """
You are an audit critic. Analyze the following debate transcript for fabricated information.
Scan all <REASONING> and <FINAL> blocks.

[TRANSCRIPT]
{transcript_json}
[/TRANSCRIPT]

Identify any specific, "hard" facts, statistics, percentages, or direct quotes that seem unlikely or fabricated (e..g., "a 2025 study proved", "87% of all...", "As the CEO said...").

List the *exact* fabricated phrases. If none are found, return an empty list.
Respond *only* in this strict JSON format:
{{
  "potential_fabrications": [
    "<string>",
    "<string>"
  ]
}}
"""

# --- THIS PROMPT IS NOW DYNAMIC ---
PROMPT_VERDICT = """
You are a human debate judge. You must render a final verdict.
The topic of the debate was: "{topic}"

Here is the final argument from {model_pro_name} (PRO):
<ARGUMENT_PRO>
{mike_final}
</ARGUMENT_PRO>

Here is the final argument from {model_con_name} (CON):
<ARGUMENT_CON>
{jimmy_final}
</ARGUMENT_CON>

Based *only* on these two final arguments, who was more persuasive and made a stronger case?
Write a one-paragraph summary explaining your decision and declaring a winner. 
Do not use XML tags or JSON. Respond in a single, human-readable block of text.
"""

# --- Critic Execution Functions ---

def _run_critic_json_audit(prompt: str) -> dict:
    """Helper function to run a critic prompt that MUST return JSON."""
    success, raw_output, metrics, error = run_ollama(
        model_name=MODEL_CRITIC,
        prompt=prompt,
        temperature=TEMP_CRITIC,
        **CAPS_REPAIR 
    )
    
    if not success:
        return {"error": "Failed to run critic model", "details": error}

    try:
        if "```json" in raw_output:
            raw_output = robust_extract_tag(raw_output, "```json")
        if "```" in raw_output:
            raw_output = raw_output.replace("```", "")
            
        report = json.loads(raw_output)
        return report
    except json.JSONDecodeError:
        log.warning(f"Critic failed to produce valid JSON. Raw: {raw_output}")
        return {"error": "Critic returned non-JSON output", "raw": raw_output}

# --- THIS FUNCTION IS UPDATED ---
def _run_critic_verdict_audit(transcript: dict, model_pro_name: str, model_con_name: str) -> dict:
    """Helper function to run the free-text 'verdict' prompt."""
    prompt = PROMPT_VERDICT.format(
        topic=transcript.get("topic", "No Topic"),
        mike_final=transcript.get("finals", {}).get("mike", {}).get("final", "No argument"),
        jimmy_final=transcript.get("finals", {}).get("jimmy", {}).get("final", "No argument"),
        model_pro_name=model_pro_name,
        model_con_name=model_con_name
    )
    
    success, raw_output, metrics, err = run_ollama(
        model_name=MODEL_CRITIC,
        prompt=prompt,
        temperature=TEMP_CRITIC,
        **CAPS_FINALIZE 
    )
    
    if not success:
        return {"verdict": f"Critic failed to render a verdict: {err}", "metrics": metrics}
    
    # Clean up any XML tags the critic might have added by mistake
    raw_output = re.sub(r'<[^>]+>', '', raw_output).strip()
    
    return {"verdict": raw_output, "metrics": metrics}

# --- THIS FUNCTION IS UPDATED ---
def run_all_critic_audits(transcript: dict, pro_mismatches: int, con_mismatches: int, 
                            model_pro_name: str, model_con_name: str) -> dict:
    """
    Runs the full suite of critic audits on a completed debate transcript.
    """
    transcript_json = json.dumps(transcript, indent=2)
    
    log.info("Running critic: Verdict...")
    verdict_report = _run_critic_verdict_audit(transcript, model_pro_name, model_con_name)

    log.info("Running critic: Hallucination Audit...")
    hallucination_prompt = PROMPT_HALLUCINATION_AUDIT.format(transcript_json=transcript_json)
    hallucination_report = _run_critic_json_audit(hallucination_prompt)
    
    final_report = {
        "verdict": verdict_report.get("verdict", "Critic failed."),
        "verdict_metrics": verdict_report.get("metrics", {}), 
        "drift_audit": {
            "total_pro_mismatches": pro_mismatches,
            "total_con_mismatches": con_mismatches
        },
        "hallucination_audit": hallucination_report
    }
    
    return final_report
