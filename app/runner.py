# app/runner.py
import subprocess
import json
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

if "OLLAMA_NUM_PARALLEL" not in os.environ:
    os.environ["OLLAMA_NUM_PARALLEL"] = "1"
    log.warning("OLLAMA_NUM_PARALLEL not set, defaulting to 1.")

def run_ollama(model_name: str, 
               prompt: str, 
               temperature: float = 0.5, 
               num_predict: int = 300, 
               timeout: int = 60) -> tuple[bool, str, dict, str]:
    """
    Runs an Ollama model generation call via the REST API (curl)
    for robust timeout and parameter control.

    Returns:
        A tuple (success: bool, output: str, metrics: dict, error: str)
    """
    api_url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict
        }
    }
    
    curl_cmd = [
        "curl", "-s", api_url, "-d", json.dumps(payload)
    ]

    try:
        log.info(f"Running model {model_name} with num_predict={num_predict}, timeout={timeout}s")
        
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
            encoding='utf-8'
        )
        
        raw_output = result.stdout
        
        try:
            response_json = json.loads(raw_output)
            
            if "response" in response_json:
                log.info(f"Successfully ran {model_name}.")
                
                # --- NEW METRICS PARSING ---
                metrics = parse_ollama_metrics(response_json)
                response_text = response_json["response"].strip()
                # --- END METRICS PARSING ---
                
                return True, response_text, metrics, ""
                
            elif "error" in response_json:
                log.error(f"Ollama API error for {model_name}: {response_json['error']}")
                return False, "", {}, f"Ollama API Error: {response_json['error']}"
            else:
                log.error(f"Unknown JSON response from Ollama: {raw_output}")
                return False, "", {}, "Unknown JSON response from Ollama."
                
        except json.JSONDecodeError:
            log.error(f"Failed to decode JSON from Ollama: {raw_output}")
            return False, "", {}, f"Ollama JSON Decode Error: {raw_output}"

    except subprocess.TimeoutExpired:
        log.warning(f"TimeoutExpired: Model {model_name} exceeded {timeout}s.")
        return False, "", {}, f"Timeout: Model call exceeded {timeout} seconds."
    
    except Exception as e:
        log.error(f"Generic exception in run_ollama: {e}")
        return False, "", {}, f"Python Exception: {str(e)}"

def parse_ollama_metrics(response_json: dict) -> dict:
    """Helper to extract and calculate key performance metrics from Ollama response."""
    try:
        # Times are in nanoseconds, convert to seconds
        total_s = response_json.get("total_duration", 0) / 1e9
        load_s = response_json.get("load_duration", 0) / 1e9
        gen_s = response_json.get("eval_duration", 0) / 1e9
        
        tokens_in = response_json.get("prompt_eval_count", 0)
        tokens_out = response_json.get("eval_count", 0)
        
        # Calculate tokens per second
        tok_per_s = 0
        if gen_s > 0:
            tok_per_s = tokens_out / gen_s

        return {
            "time_total_s": round(total_s, 2),
            "time_load_s": round(load_s, 2),
            "time_gen_s": round(gen_s, 2),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_per_s": round(tok_per_s, 2)
        }
    except Exception as e:
        log.error(f"Failed to parse metrics: {e}")
        return {"error": str(e)}
