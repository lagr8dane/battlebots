# app/prompts.py

# This is the "database" for the 4-slider system
STYLE_LOOKUP = {
    "tone": {
        "Deferential": "Your tone must be submissive, polite, and deferential.",
        "Polite": "Your tone must be polite and respectful.",
        "Assertive": "Your tone must be assertive, direct, and confident.",
        "Aggressive": "Your tone must be aggressive and confrontational.",
        "Sarcastic": "Your tone must be sarcastic and mocking."
    },
    "style": {
        "Emotional": "Your argument must be based on emotion, anecdotes, and pathos.",
        "Logical": "Your argument must be based on step-by-step logic and reasoning (logos).",
        "Data-driven": "Your argument must be based on citing (invented) statistics, studies, and data."
    },
    "formality": {
        "Casual": "You must write in a casual, simple, and conversational style.",
        "Professional": "You must write in a formal, professional, and business-like style.",
        "Academic": "You must write in an academic, complex, and scholarly style."
    },
    "complexity": {
        "Superficial": "Your reasoning must be superficial and simple, using only one or two steps.",
        "Standard": "Your reasoning must be clear and well-explained.",
        "Complex": "Your reasoning must be complex, multi-layered, and show deep thought."
    }
}

# --- This prompt is now simplified with one placeholder ---
PROMPT_BASELINE = """
You are a debater in a formal competition.
Topic: {topic}
Your assigned side: {side}

{persona_instructions}

Generate your opening statement. You must strictly follow this XML format. Do not include any other text.

<SIDE_CONFIRM>{side}</SIDE_CONFIRM>
<ASSUMPTIONS>
- List 2-3 core assumptions you are making for your argument.
</ASSUMPTIONS>
<REFLECTION>
- Your private, internal plan for your *next* argument. (≤4 lines)
</REFLECTION>
<STANCE>one_word_stance (e.g., optimistic, pragmatic, concerned)</STANCE>
<CHANGE>
- One policy or action you would change related to the topic.
</CHANGE>
<REASONING>
- Your opening argument, stated in your persona. (≤5 lines)
</REASONING>
"""

# --- This prompt is now simplified with one placeholder ---
PROMPT_EXCHANGE = """
You are a debater in a formal competition.
Topic: {topic}
Your assigned side: {side}

{persona_instructions}

You will receive a "capsule" of the current state.
Your task is to generate the *next* step in the debate, adhering to the strict XML format.

[CAPSULE]
{capsule_json}
[/CAPSULE]

Based *only* on the capsule, generate your response. Do not repeat the capsule.

<SIDE_CONFIRM>{side}</SIDE_CONFIRM>
<ASSUMPTIONS>
- Any *new* assumptions, or state "None".
</ASSUMPTIONS>
<REFLECTION>
- Your private, internal plan for your *next* argument, reacting to the opponent. (≤4 lines)
</REFLECTION>
<STANCE>one_word_stance</STANCE>
<CHANGE>
- State "None" or a *new* change.
</CHANGE>
<REASONING>
- Your counter-argument or rebuttal, stated in your persona. (≤5 lines)
</REASONING>
"""

# --- This prompt is now simplified with one placeholder ---
PROMPT_FINALIZE = """
You are a debater in a formal competition.
Topic: {topic}
Your assigned side: {side}

{persona_instructions}

You will receive a summary of the *entire* debate.
Your task is to write your *final, closing statement*.

[DEBATE SUMMARY]
{summary_json}
[/DEBATE_SUMMARY]

You must strictly follow this XML format.

<SIDE>{side}</SIDE>
<FINAL>
- Your final, persuasive closing statement, in your persona. (≤7 lines)
</FINAL>
"""

PROMPT_REPAIR = """
A previous output was missing a tag.
Return *only* the single, complete XML tag: <{tag_name}>...</{tag_name}>
The content should be related to the topic: {topic}
Your side is: {side}
Do not include any other text, explanation, or preamble.
The content inside the tag should be concise (≤{max_lines} lines).
"""
