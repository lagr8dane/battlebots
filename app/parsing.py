# app/parsing.py
import re
import pandas as pd

def _clip_text(text: str, max_lines: int = 5) -> str:
    """Clips text to a max number of lines to enforce brevity."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return "\n".join(lines[:max_lines])

def robust_extract_tag(raw_text: str, tag: str) -> str:
    """
    A more robust, non-greedy parser that finds the *first*
    complete tag and ignores duplicates or malformed XML.
    """
    # The '?' makes the '.*' non-greedy, so it stops at the *first* closing tag
    match = re.search(f'<{tag}>(.*?)</{tag}>', raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

def parse_neutral_output(raw_text: str, assigned_side: str) -> dict:
    """
    Parses the standard exchange output.
    We only *really* care about reasoning and side_confirm.
    """
    
    data = {
        "side_confirm": robust_extract_tag(raw_text, "SIDE_CONFIRM"),
        "reasoning": _clip_text(robust_extract_tag(raw_text, "REASONING"), 5),
        # We can still extract the others for the JSON export, even if we don't show them
        "assumptions": _clip_text(robust_extract_tag(raw_text, "ASSUMPTIONS"), 3),
        "reflection": _clip_text(robust_extract_tag(raw_text, "REFLECTION"), 4),
        "stance": robust_extract_tag(raw_text, "STANCE"),
        "change": _clip_text(robust_extract_tag(raw_text, "CHANGE"), 2),
    }
    
    side_mismatch = False
    side_confirm_val = data.get("side_confirm", "")
    
    # Check for protest (wrote text instead of side)
    if side_confirm_val and side_confirm_val.upper() not in [assigned_side.upper(), "MISSING", ""]:
        side_mismatch = True 
    # Check for simple mismatch or missing
    elif not side_confirm_val or side_confirm_val.upper() != assigned_side.upper():
        side_mismatch = True

    data["side_mismatch"] = side_mismatch
    data["raw_output"] = raw_text
    return data

def parse_final_output(raw_text: str, assigned_side: str) -> dict:
    """Parses the final persona output and checks for side mismatch."""
    
    data = {
        "final": _clip_text(robust_extract_tag(raw_text, "FINAL"), 7),
        "side": robust_extract_tag(raw_text, "SIDE"),
    }
    
    side_mismatch = False
    if not data["side"]:
        side_mismatch = True
    elif data["side"].upper() != assigned_side.upper():
        side_mismatch = True
        
    data["side_mismatch"] = side_mismatch
    data["raw_output"] = raw_text
    return data
