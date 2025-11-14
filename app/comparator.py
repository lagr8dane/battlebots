# app/comparator.py
import json
import logging
import re  # <-- NEW IMPORT
from app.runner import run_ollama
from app.comparator_prompts import PROMPT_COMPARISON_CRITIC
from app.config import (
    MODEL_COMPARATOR,
    CAPS_COMPARISON, CAPS_CRITIQUE
)

log = logging.getLogger(__name__)

# --- NEW HELPER FUNCTION (copied from app/parsing.py) ---
def _extract_tag(text: str, tag: str) -> str:
    """Strictly extracts content from a single XML-style tag."""
    match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""
# --- END HELPER FUNCTION ---

class ComparatorCoordinator:
    def __init__(self):
        log.info("ComparatorCoordinator initialized.")
    
    def run_comparison(self, user_prompt: str, 
                       model_a_name: str, persona_a_text: str, 
                       model_b_name: str, persona_b_text: str) -> tuple[dict, dict]:
        
        prompt_a = f"{persona_a_text}\n\n{user_prompt}" if persona_a_text else user_prompt
        prompt_b = f"{persona_b_text}\n\n{user_prompt}" if persona_b_text else user_prompt
        
        log.info(f"Running comparison for models: {model_a_name} vs {model_b_name}")

        success_a, raw_a, metrics_a, err_a = run_ollama(
            model_name=model_a_name, prompt=prompt_a, temperature=0.6, **CAPS_COMPARISON
        )
        
        success_b, raw_b, metrics_b, err_b = run_ollama(
            model_name=model_b_name, prompt=prompt_b, temperature=0.6, **CAPS_COMPARISON
        )

        response_a = {"response": raw_a, "metrics": metrics_a, "error": err_a}
        response_b = {"response": raw_b, "metrics": metrics_b, "error": err_b}

        return response_a, response_b

    # --- THIS FUNCTION IS UPDATED ---
    def run_critique(self, user_prompt: str, 
                     model_a_name: str, response_a: str, metrics_a: dict,
                     model_b_name: str, response_b: str, metrics_b: dict) -> dict:
        
        log.info(f"Running critic to judge {model_a_name} vs {model_b_name}")

        critic_prompt = PROMPT_COMPARISON_CRITIC.format(
            user_prompt=user_prompt,
            model_a=model_a_name, response_a=response_a,
            model_b=model_b_name, response_b=response_b,
            metrics_a_tok_s=metrics_a.get("tokens_per_s", "N/A"),
            metrics_a_gen_s=metrics_a.get("time_gen_s", "N/A"),
            metrics_a_tokens_out=metrics_a.get("tokens_out", "N/A"),
            metrics_b_tok_s=metrics_b.get("tokens_per_s", "N/A"),
            metrics_b_gen_s=metrics_b.get("time_gen_s", "N/A"),
            metrics_b_tokens_out=metrics_b.get("tokens_out", "N/A")
        )
        
        success, raw_critique, metrics, err = run_ollama(
            model_name=MODEL_COMPARATOR,
            prompt=critic_prompt,
            temperature=0.4,
            **CAPS_CRITIQUE
        )
        
        if not success:
            return {
                "critique_report": {"verdict": f"Critic model failed to run: {err}"}, 
                "raw_critique": "",
                "metrics": metrics
            }
        
        # --- NEW PARSING LOGIC ---
        # We now parse the critic's output instead of just returning it
        parsed_report = {
            "verdict": _extract_tag(raw_critique, "VERDICT"),
            "reasons": _extract_tag(raw_critique, "REASONS"),
            "scores": _extract_tag(raw_critique, "SCORES"),
            "advice": _extract_tag(raw_critique, "ADVICE"),
        }
        
        # If parsing fails (e.g., model just wrote text), use the raw text as the verdict
        if not parsed_report["verdict"]:
            parsed_report["verdict"] = raw_critique
        
        return {
            "critique_report": parsed_report, 
            "raw_critique": raw_critique, 
            "metrics": metrics
        }
