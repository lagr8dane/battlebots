# app/coordinator.py
import json
import logging
import re # <-- Import re for the critic fix
from app.runner import run_ollama, parse_ollama_metrics
from app.parsing import parse_neutral_output, parse_final_output, robust_extract_tag
from app.prompts import (
    PROMPT_BASELINE, PROMPT_EXCHANGE, PROMPT_FINALIZE, PROMPT_REPAIR,
    STYLE_LOOKUP 
)
from app.config import (
    MODEL_CRITIC, TEMP_CRITIC,
    CAPS_WARMUP, CAPS_BASELINE, CAPS_EXCHANGE, CAPS_FINALIZE, CAPS_REPAIR
)
from app.critic import run_all_critic_audits

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

BLANK_METRICS = {
    "time_total_s": 0, "time_load_s": 0, "time_gen_s": 0,
    "tokens_in": 0, "tokens_out": 0, "tokens_per_s": 0
}

class DebateCoordinator:
    def __init__(self):
        self.critic_model = {
            "name": MODEL_CRITIC, 
            "temp": TEMP_CRITIC
        }
        log.info("DebateCoordinator initialized for dynamic models.")

    # --- THIS IS THE MISSING FUNCTION THAT CAUSED THE CRASH ---
    def _build_persona_instructions(self, persona_text: str, style_dict: dict, 
                                    force_adversarial: bool, side: str) -> str:
        """Builds the single, consolidated instruction block."""
        prompts = []
        
        # 1. Add the main persona text first
        if persona_text:
            prompts.append(persona_text)

        # 2. Add the adversarial instruction if checked
        if force_adversarial:
            if side == "PRO":
                prompts.append("You *must* agree with and argue in favor of the topic statement.")
            else:
                prompts.append("You *must* disagree with and argue against the topic statement.")

        # 3. Add the 4 slider instructions
        prompts.append(STYLE_LOOKUP["tone"].get(style_dict.get("tone"), ""))
        prompts.append(STYLE_LOOKUP["style"].get(style_dict.get("style"), ""))
        prompts.append(STYLE_LOOKUP["formality"].get(style_dict.get("formality"), ""))
        prompts.append(STYLE_LOOKUP["complexity"].get(style_dict.get("complexity"), ""))
        
        prompts = [p for p in prompts if p] 
        if not prompts:
            return "You are a neutral debater." # Fallback
        
        return "**YOUR PERSONA AND INSTRUCTIONS:**\n" + "\n".join(f"- {p}" for p in prompts)
    # --- END OF MISSING FUNCTION ---

    def _run_model_with_repair(self, model_name: str, temperature: float, side: str,
                               prompt: str, caps: dict, 
                               required_tag: str,
                               repair_context: dict) -> tuple[bool, str, dict, str]:
        
        success, raw_output, metrics, error = run_ollama(
            model_name=model_name,
            prompt=prompt,
            temperature=temperature,
            **caps
        )
        
        if not success:
            return False, "", metrics, error 

        required_tags_to_check = []
        if required_tag == "REASONING":
            required_tags_to_check = ["REASONING", "SIDE_CONFIRM"]
        elif required_tag == "FINAL":
            required_tags_to_check = ["FINAL", "SIDE"]
            
        for tag in required_tags_to_check:
            if not robust_extract_tag(raw_output, tag): 
                log.warning(f"Missing required tag <{tag}> for {model_name}. Attempting repair.")
                
                repair_prompt = PROMPT_REPAIR.format(
                    tag_name=tag,
                    topic=repair_context.get("topic", "the debate topic"),
                    side=side,
                    max_lines=7 if tag == "FINAL" else 5
                )
                
                repair_success, repair_output, repair_metrics, repair_error = run_ollama(
                    model_name=model_name,
                    prompt=repair_prompt,
                    temperature=temperature,
                    **CAPS_REPAIR
                )
                
                if repair_success:
                    log.info(f"Repair successful for <{tag}>.")
                    raw_output += f"\n\n\n{repair_output}"
                    repair_metrics["time_load_s"] += metrics.get("time_load_s", 0)
                    metrics = repair_metrics
                else:
                    log.error(f"Repair failed for {model_name}: {repair_error}")
                    return True, raw_output, metrics, f"Original run OK, but repair for <{tag}> failed."

        return True, raw_output, metrics, ""

    def warm_up_models(self, model_pro: str, model_con: str) -> dict:
        log.info(f"Warming up models: {model_pro}, {model_con}, {self.critic_model['name']}")
        results = {}
        models_to_warm = [
            (model_pro, "PRO"),
            (model_con, "CON"),
            (self.critic_model['name'], "CRITIC")
        ]
        
        for model_name, role in models_to_warm:
            success, _, metrics, err = run_ollama(
                model_name=model_name, prompt="ok", temperature=0.1, **CAPS_WARMUP
            )
            load_time = metrics.get('time_load_s', 0)
            results[role] = f"OK ({model_name} loaded in {load_time}s)" if success else f"FAIL: {err}"
            if not success:
                log.error(f"Failed to warm up {model_name}: {err}")
        
        log.info(f"Warm-up complete: {results}")
        return results

    def generate_baselines(self, topic: str, force_adversarial: bool,
                             model_pro: str, temp_pro: float, persona_pro: str, style_pro: dict,
                             model_con: str, temp_con: float, persona_con: str, style_con: dict
                             ) -> tuple[dict, dict, dict, dict]:
        
        log.info(f"Generating baselines for PRO: {model_pro} and CON: {model_con}")
        
        inst_pro = self._build_persona_instructions(persona_pro, style_pro, force_adversarial, "PRO")
        inst_con = self._build_persona_instructions(persona_con, style_con, force_adversarial, "CON")
        
        prompt_mike = PROMPT_BASELINE.format(
            topic=topic, side="PRO", 
            persona_instructions=inst_pro
        )
        success_mike, raw_mike, metrics_mike, err_mike = self._run_model_with_repair(
            model_pro, temp_pro, "PRO", prompt_mike, 
            CAPS_BASELINE, "REASONING", {"topic": topic}
        )
        
        prompt_jimmy = PROMPT_BASELINE.format(
            topic=topic, side="CON", 
            persona_instructions=inst_con
        )
        success_jimmy, raw_jimmy, metrics_jimmy, err_jimmy = self._run_model_with_repair(
            model_con, temp_con, "CON", prompt_jimmy, 
            CAPS_BASELINE, "REASONING", {"topic": topic}
        )

        mike_output = parse_neutral_output(raw_mike, "PRO")
        jimmy_output = parse_neutral_output(raw_jimmy, "CON")

        if not success_mike: mike_output["error"] = err_mike
        if not success_jimmy: jimmy_output["error"] = err_jimmy

        return mike_output, metrics_mike, jimmy_output, metrics_jimmy

    def exchange_step(self, topic: str, last_mike_output: dict, last_jimmy_output: dict, 
                        force_adversarial: bool,
                        model_pro: str, temp_pro: float, persona_pro: str, style_pro: dict,
                        model_con: str, temp_con: float, persona_con: str, style_con: dict
                        ) -> tuple[dict, dict, dict, dict, dict, dict]:
        
        log.info("Generating exchange step...")
        
        inst_pro = self._build_persona_instructions(persona_pro, style_pro, force_adversarial, "PRO")
        inst_con = self._build_persona_instructions(persona_con, style_con, force_adversarial, "CON")

        capsule_mike = {"topic": topic, "my_side": "PRO", "my_last_reflection": last_mike_output.get("reflection", "N/A"), "opponent_last_reasoning": last_jimmy_output.get("reasoning", "N/A")}
        prompt_mike = PROMPT_EXCHANGE.format(
            topic=topic, side="PRO", 
            capsule_json=json.dumps(capsule_mike, indent=2), 
            persona_instructions=inst_pro
        )
        
        capsule_jimmy = {"topic": topic, "my_side": "CON", "my_last_reflection": last_jimmy_output.get("reflection", "N/A"), "opponent_last_reasoning": last_mike_output.get("reasoning", "N/A")}
        prompt_jimmy = PROMPT_EXCHANGE.format(
            topic=topic, side="CON", 
            capsule_json=json.dumps(capsule_jimmy, indent=2), 
            persona_instructions=inst_con
        )

        success_mike, raw_mike, metrics_mike, err_mike = self._run_model_with_repair(
            model_pro, temp_pro, "PRO", prompt_mike, 
            CAPS_EXCHANGE, "REASONING", {"topic": topic}
        )
        
        success_jimmy, raw_jimmy, metrics_jimmy, err_jimmy = self._run_model_with_repair(
            model_con, temp_con, "CON", prompt_jimmy, 
            CAPS_EXCHANGE, "REASONING", {"topic": topic}
        )

        mike_output = parse_neutral_output(raw_mike, "PRO")
        jimmy_output = parse_neutral_output(raw_jimmy, "CON")
        
        if not success_mike: mike_output["error"] = err_mike
        if not success_jimmy: jimmy_output["error"] = err_jimmy

        return capsule_mike, mike_output, metrics_mike, capsule_jimmy, jimmy_output, metrics_jimmy

    def finalize_debate(self, topic: str, debate_history: list, 
                          persona_pro: str, model_pro: str, temp_pro: float, style_pro: dict,
                          persona_con: str, model_con: str, temp_con: float, style_con: dict
                          ) -> tuple[dict, dict, dict, dict]:
        
        log.info("Generating final statements...")
        
        inst_pro = self._build_persona_instructions(persona_pro, style_pro, force_adversarial=True, side="PRO")
        inst_con = self._build_persona_instructions(persona_con, style_con, force_adversarial=True, side="CON")
        
        summary = [f"PRO (Baseline): {debate_history[0]['mike_output']['reasoning']}", f"CON (Baseline): {debate_history[0]['jimmy_output']['reasoning']}"]
        for i, round_data in enumerate(debate_history[1:], start=1):
            summary.append(f"PRO (Round {i}): {round_data['mike_output']['reasoning']}")
            summary.append(f"CON (Round {i}): {round_data['jimmy_output']['reasoning']}")
        summary_json = json.dumps(summary, indent=2)

        prompt_mike = PROMPT_FINALIZE.format(
            topic=topic, side="PRO", 
            summary_json=summary_json, 
            persona_instructions=inst_pro
        )
        success_mike, raw_mike, metrics_mike, err_mike = self._run_model_with_repair(
            model_pro, temp_pro, "PRO", prompt_mike, 
            CAPS_FINALIZE, "FINAL", {"topic": topic}
        )

        prompt_jimmy = PROMPT_FINALIZE.format(
            topic=topic, side="CON", 
            summary_json=summary_json, 
            persona_instructions=inst_con
        )
        
        success_jimmy, raw_jimmy, metrics_jimmy, err_jimmy = self._run_model_with_repair(
            model_con, temp_con, "CON", prompt_jimmy, 
            CAPS_FINALIZE, "FINAL", {"topic": topic}
        )
        
        mike_final = parse_final_output(raw_mike, "PRO")
        jimmy_final = parse_final_output(raw_jimmy, "CON")

        if not success_mike: mike_final["error"] = err_mike
        if not success_jimmy: jimmy_final["error"] = err_jimmy
        
        return mike_final, metrics_mike, jimmy_final, metrics_jimmy

    def run_critic(self, transcript: dict) -> dict:
        log.info("Calculating drift scores and running critic audits...")
        pro_mismatches, con_mismatches = 0, 0
        
        for round_data in transcript.get("history", []):
            if round_data.get("mike_output", {}).get("side_mismatch", False): pro_mismatches += 1
            if round_data.get("jimmy_output", {}).get("side_mismatch", False): con_mismatches += 1
        if transcript.get("finals", {}).get("mike", {}).get("side_mismatch", False): pro_mismatches += 1
        if transcript.get("finals", {}).get("jimmy", {}).get("side_mismatch", False): con_mismatches += 1
            
        log.info(f"Pre-calculated drift: PRO={pro_mismatches}, CON={con_mismatches}")

        config = transcript.get("debate_config", {})
        model_pro_name = config.get("model_pro", "PRO")
        model_con_name = config.get("model_con", "CON")

        try:
            report = run_all_critic_audits(
                transcript=transcript, 
                pro_mismatches=pro_mismatches, 
                con_mismatches=con_mismatches,
                model_pro_name=model_pro_name,
                model_con_name=model_con_name
            )
            log.info("Critic audit complete.")
            return report
        except Exception as e:
            log.error(f"Critic run failed: {e}")
            return {"error": str(e), "details": "Critic execution failed."}
